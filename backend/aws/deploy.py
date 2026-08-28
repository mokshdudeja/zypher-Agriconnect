"""
AgriConnect — Full AWS Deployment Automation

Provisions the complete production stack:
    1. S3 buckets for training data and models
    2. DynamoDB tables (crop_prices, call_logs, user_sessions)
    3. SageMaker training jobs and real-time endpoints with auto-scaling
    4. Lambda functions (daily_update, weekly_retrain, api_handler)
    5. API Gateway REST API with routes and API key
    6. EventBridge rules (daily 6 AM IST, weekly Sunday 2 AM IST)
    7. IAM roles and policies

Usage:
    python -m backend.aws.deploy --stage dev       # Deploy dev environment
    python -m backend.aws.deploy --stage prod      # Deploy production
    python -m backend.aws.deploy --stage dev teardown  # Destroy dev environment
    python -m backend.aws.deploy --stage dev status    # Check stack status
    python -m backend.aws.deploy --stage dev deploy-sagemaker  # Deploy SageMaker only

Requires: boto3, AWS credentials configured
"""

import os
import sys
import json
import time
import zipfile
import hashlib
import logging
import argparse
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


# ─── Configuration ───────────────────────────────────────────────

PROJECT = "zypher-agriconnect"
REGION = os.getenv("AWS_REGION", "ap-south-1")

# S3
S3_DATA_BUCKET = f"{PROJECT}-data"
S3_MODELS_BUCKET = f"{PROJECT}-models"

# SageMaker
SAGEMAKER_ROLE_NAME = f"{PROJECT}-sagemaker-role"
SAGEMAKER_ENDPOINT = f"{PROJECT}-price-predictor"
SAGEMAKER_INSTANCE_TYPE_TRAIN = "ml.m5.large"
SAGEMAKER_INSTANCE_TYPE_INFERENCE = "ml.t2.medium"
SAGEMAKER_MAX_RUNTIME = 3600  # 1 hour
SAGEMAKER_AUTO_MIN = 1
SAGEMAKER_AUTO_MAX = 4

# DynamoDB
DYNAMODB_TABLES = {
    "crop_prices": {"pk": "crop", "sk": "state_date", "ttl_days": 30},
    "call_logs": {"pk": "call_id", "sk": None, "ttl_days": 90},
    "user_sessions": {"pk": "user_id", "sk": None, "ttl_days": 7},
}

# Lambda
LAMBDA_FUNCTIONS = {
    "daily_update": {
        "description": "Fetch new mandi data, update DynamoDB cache",
        "timeout": 300,
        "memory": 512,
    },
    "weekly_retrain": {
        "description": "Trigger SageMaker training job",
        "timeout": 600,
        "memory": 256,
    },
    "api_handler": {
        "description": "Main API Gateway Lambda (all endpoints)",
        "timeout": 30,
        "memory": 1024,
    },
}

# API Gateway
API_NAME = f"{PROJECT}-api"
API_THROTTLE_RATE = 1000
API_THROTTLE_BURST = 2000

# EventBridge
EVENTBRIDGE_RULES = [
    {
        "name": f"{PROJECT}-daily-update",
        "description": "Trigger daily data collection at 6 AM IST",
        "schedule": "cron(0 0 * * ? *)",  # 00:00 UTC = 05:30 IST
        "target": "daily_update",
        "input": {"action": "daily_update"},
    },
    {
        "name": f"{PROJECT}-weekly-retrain",
        "description": "Trigger weekly model retraining on Sunday 2 AM IST",
        "schedule": "cron(0 20 ? * SUN *)",  # 20:00 UTC = 01:30 IST
        "target": "weekly_retrain",
        "input": {"action": "weekly_retrain"},
    },
]

# API Gateway routes
API_ROUTES = {
    "GET /api/predict/{crop}/{state}": "api_handler",
    "GET /api/weather": "api_handler",
    "GET /api/weather/v2": "api_handler",
    "GET /api/weather/alerts": "api_handler",
    "POST /api/crop-recommend": "api_handler",
    "GET /api/health": "api_handler",
    "GET /api/supported": "api_handler",
    "POST /api/sarvam/tts": "api_handler",
    "POST /api/sarvam/stt": "api_handler",
    "POST /api/sarvam/translate": "api_handler",
    "POST /api/ivr/incoming": "api_handler",
    "POST /api/ivr/gather": "api_handler",
    "GET /api/ivr/audio/{proxy+}": "api_handler",
    "POST /api/ivr/tts": "api_handler",
    "POST /api/ivr/test-crop": "api_handler",
}


# ─── Helpers ─────────────────────────────────────────────────────

def _iam_client():
    return boto3.client("iam", region_name=REGION)


def _s3_client():
    return boto3.client("s3", region_name=REGION)


def _dynamodb_client():
    return boto3.client("dynamodb", region_name=REGION)


def _sagemaker_client():
    return boto3.client("sagemaker", region_name=REGION)


def _lambda_client():
    return boto3.client("lambda", region_name=REGION)


def _apigw_client():
    return boto3.client("apigateway", region_name=REGION)


def _events_client():
    return boto3.client("events", region_name=REGION)


def _account_id() -> str:
    sts = boto3.client("sts", region_name=REGION)
    return sts.get_caller_identity()["Account"]


def _lambda_zip_path() -> Path:
    """Create deployment ZIP for Lambda functions."""
    zip_path = Path(tempfile.mkdtemp()) / "lambda.zip"
    project_root = Path(__file__).resolve().parent.parent.parent

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add the entire backend package
        for root, dirs, files in os.walk(project_root / "backend"):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if f.endswith((".py", ".txt")):
                    full = Path(root) / f
                    arcname = str(full.relative_to(project_root))
                    zf.write(full, arcname)

        # Add requirements
        req_files = list(project_root.glob("backend/*/requirements.txt"))
        for req in req_files:
            zf.write(req, str(req.relative_to(project_root)))

    logger.info(f"Lambda ZIP created: {zip_path} ({zip_path.stat().st_size} bytes)")
    return zip_path


# ─── IAM ─────────────────────────────────────────────────────────

def create_iam_role(role_name: str, trust_policy: dict, policies: list[dict]) -> str:
    """Create IAM role with trust policy and inline policies. Returns ARN."""
    iam = _iam_client()

    # Check if exists
    try:
        resp = iam.get_role(RoleName=role_name)
        logger.info(f"IAM role {role_name} already exists")
        return resp["Role"]["Arn"]
    except ClientError:
        pass

    # Create role
    resp = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description=f"AgriConnect {role_name}",
        Tags=[{"Key": "Project", "Value": PROJECT}],
    )
    arn = resp["Role"]["Arn"]
    logger.info(f"Created IAM role: {role_name}")

    # Attach policies
    for policy in policies:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy["name"],
            PolicyDocument=json.dumps(policy["document"]),
        )
        logger.info(f"  Attached policy: {policy['name']}")

    return arn


def setup_sagemaker_role() -> str:
    """Create SageMaker execution role with S3 and DynamoDB access."""
    trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "sagemaker.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    policies = [
        {
            "name": "s3-access",
            "document": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                        "Resource": [
                            f"arn:aws:s3:::{S3_DATA_BUCKET}",
                            f"arn:aws:s3:::{S3_DATA_BUCKET}/*",
                            f"arn:aws:s3:::{S3_MODELS_BUCKET}",
                            f"arn:aws:s3:::{S3_MODELS_BUCKET}/*",
                        ],
                    }
                ],
            },
        },
        {
            "name": "dynamodb-access",
            "document": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "dynamodb:PutItem", "dynamodb:GetItem",
                            "dynamodb:Query", "dynamodb:Scan",
                            "dynamodb:UpdateItem",
                        ],
                        "Resource": "arn:aws:dynamodb:*:*:table/zypher-agriconnect-*",
                    }
                ],
            },
        },
        {
            "name": "cloudwatch-logs",
            "document": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                        "Resource": "arn:aws:logs:*:*:*",
                    }
                ],
            },
        },
    ]
    return create_iam_role(SAGEMAKER_ROLE_NAME, trust, policies)


def setup_lambda_role() -> str:
    """Create Lambda execution role with all necessary permissions."""
    trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    policies = [
        {
            "name": "lambda-basic",
            "document": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
                        ],
                        "Resource": "arn:aws:logs:*:*:*",
                    }
                ],
            },
        },
        {
            "name": "dynamodb-access",
            "document": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:DeleteItem",
                            "dynamodb:Query", "dynamodb:Scan", "dynamodb:UpdateItem",
                            "dynamodb:BatchWriteItem", "dynamodb:BatchGetItem",
                        ],
                        "Resource": "arn:aws:dynamodb:*:*:table/zypher-agriconnect-*",
                    }
                ],
            },
        },
        {
            "name": "s3-access",
            "document": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                        "Resource": [
                            f"arn:aws:s3:::{S3_DATA_BUCKET}",
                            f"arn:aws:s3:::{S3_DATA_BUCKET}/*",
                            f"arn:aws:s3:::{S3_MODELS_BUCKET}",
                            f"arn:aws:s3:::{S3_MODELS_BUCKET}/*",
                        ],
                    }
                ],
            },
        },
        {
            "name": "sagemaker-invoke",
            "document": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "sagemaker:InvokeEndpoint",
                            "sagemaker:DescribeEndpoint",
                            "sagemaker:InvokeEndpointAsync",
                        ],
                        "Resource": f"arn:aws:sagemaker:*:*:endpoint/{SAGEMAKER_ENDPOINT}",
                    }
                ],
            },
        },
        {
            "name": "sagemaker-start-job",
            "document": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "sagemaker:CreateTrainingJob",
                            "sagemaker:DescribeTrainingJob",
                            "sagemaker:StopTrainingJob",
                            "sagemaker:CreateModel",
                            "sagemaker:CreateEndpointConfig",
                            "sagemaker:CreateEndpoint",
                            "sagemaker:UpdateEndpointWeightsAndCapacities",
                            "sagemaker:DescribeEndpoint",
                            "sagemaker:DeleteEndpoint",
                        ],
                        "Resource": "*",
                    }
                ],
            },
        },
        {
            "name": "secrets-manager",
            "document": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["secretsmanager:GetSecretValue"],
                        "Resource": f"arn:aws:secretsmanager:*:*:secret:agriconnect/*",
                    }
                ],
            },
        },
        {
            "name": "apigateway-invoke",
            "document": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["execute-api:Invoke"],
                        "Resource": "*",
                    }
                ],
            },
        },
    ]
    return create_iam_role(f"{PROJECT}-lambda-role", trust, policies)


# ─── S3 ──────────────────────────────────────────────────────────

def setup_s3_buckets():
    """Create S3 buckets for training data and models."""
    s3 = _s3_client()

    for bucket_name in [S3_DATA_BUCKET, S3_MODELS_BUCKET]:
        try:
            s3.head_bucket(Bucket=bucket_name)
            logger.info(f"S3 bucket exists: {bucket_name}")
        except ClientError:
            try:
                create_kwargs = {"Bucket": bucket_name}
                # ap-south-1 doesn't need LocationConstraint
                if REGION != "us-east-1":
                    create_kwargs["CreateBucketConfiguration"] = {
                        "LocationConstraint": REGION
                    }
                s3.create_bucket(**create_kwargs)

                # Enable versioning
                s3.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={"Status": "Enabled"},
                )

                # Enable server-side encryption
                s3.put_bucket_encryption(
                    Bucket=bucket_name,
                    ServerSideEncryptionConfiguration={
                        "Rules": [
                            {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                        ]
                    },
                )

                logger.info(f"Created S3 bucket: {bucket_name}")
            except ClientError as e:
                logger.error(f"Failed to create bucket {bucket_name}: {e}")

    # Create training data prefix
    s3.put_object(Bucket=S3_DATA_BUCKET, Key="training/", Body=b"")
    s3.put_object(Bucket=S3_MODELS_BUCKET, Key="checkpoints/", Body=b"")


# ─── DynamoDB ────────────────────────────────────────────────────

def setup_dynamodb_tables():
    """Create all DynamoDB tables with TTL."""
    dynamodb = _dynamodb_client()

    for table_name, config in DYNAMODB_TABLES.items():
        full_name = f"{PROJECT}-{table_name}"

        try:
            dynamodb.describe_table(TableName=full_name)
            logger.info(f"DynamoDB table exists: {full_name}")
            continue
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                raise

        key_schema = [{"AttributeName": config["pk"], "KeyType": "HASH"}]
        attr_defs = [{"AttributeName": config["pk"], "AttributeType": "S"}]

        if config["sk"]:
            key_schema.append({"AttributeName": config["sk"], "KeyType": "RANGE"})
            attr_defs.append({"AttributeName": config["sk"], "AttributeType": "S"})

        dynamodb.create_table(
            TableName=full_name,
            KeySchema=key_schema,
            AttributeDefinitions=attr_defs,
            BillingMode="PAY_PER_REQUEST",
            Tags=[{"Key": "Project", "Value": PROJECT}],
        )

        # Wait for table
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=full_name)

        # Enable TTL
        dynamodb.update_time_to_live(
            TableName=full_name,
            TimeToLiveSpecification={
                "Enabled": True,
                "AttributeName": "ttl",
            },
        )

        logger.info(f"Created DynamoDB table: {full_name} (TTL: {config['ttl_days']} days)")


# ─── SageMaker ───────────────────────────────────────────────────

def create_sagemaker_training_job(role_arn: str) -> str:
    """Create a SageMaker training job. Returns job name."""
    sm = _sagemaker_client()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    job_name = f"{PROJECT}-train-{timestamp}"

    # XGBoost container (AWS managed)
    xgboost_image = "811284226046.dkr.ecr.ap-south-1.amazonaws.com/xgboost:latest"

    try:
        sm.create_training_job(
            TrainingJobName=job_name,
            AlgorithmSpecification={
                "TrainingImage": xgboost_image,
                "TrainingInputMode": "File",
            },
            RoleArn=role_arn,
            InputDataConfig=[
                {
                    "ChannelName": "training",
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            "S3Uri": f"s3://{S3_DATA_BUCKET}/training/",
                            "S3DataDistributionType": "FullyReplicated",
                        }
                    },
                },
            ],
            OutputDataConfig={
                "S3OutputPath": f"s3://{S3_MODELS_BUCKET}/output/",
            },
            ResourceConfig={
                "InstanceCount": 1,
                "InstanceType": SAGEMAKER_INSTANCE_TYPE_TRAIN,
                "VolumeSizeInGB": 50,
            },
            StoppingCondition={
                "MaxRuntimeInSeconds": SAGEMAKER_MAX_RUNTIME,
            },
            HyperParameters={
                "objective": "reg:squarederror",
                "eval_metric": "rmse",
                "num_round": "500",
                "max_depth": "8",
                "eta": "0.05",
                "subsample": "0.8",
                "colsample_bytree": "0.8",
            },
            Tags=[
                {"Key": "Project", "Value": PROJECT},
                {"Key": "Stage", "Value": os.getenv("STAGE", "dev")},
            ],
        )
        logger.info(f"Started SageMaker training job: {job_name}")
        return job_name

    except ClientError as e:
        logger.error(f"Failed to start training job: {e}")
        raise


def deploy_sagemaker_endpoint(role_arn: str, model_data_url: Optional[str] = None):
    """Deploy or update SageMaker real-time endpoint with auto-scaling."""
    sm = _sagemaker_client()

    # If no model data URL, use the latest from S3
    if not model_data_url:
        s3 = _s3_client()
        try:
            resp = s3.list_objects_v2(
                Bucket=S3_MODELS_BUCKET, Prefix="output/", MaxKeys=1,
            )
            contents = resp.get("Contents", [])
            if contents:
                latest = sorted(contents, key=lambda x: x["LastModified"])[-1]
                model_data_url = f"s3://{S3_MODELS_BUCKET}/{latest['Key']}"
            else:
                # Use a placeholder — in production this would error
                logger.warning("No model found in S3. Creating endpoint with placeholder.")
                model_data_url = f"s3://{S3_MODELS_BUCKET}/placeholder/model.tar.gz"
        except ClientError:
            model_data_url = f"s3://{S3_MODELS_BUCKET}/placeholder/model.tar.gz"

    # Create model
    model_name = f"{PROJECT}-model"
    try:
        sm.create_model(
            ModelName=model_name,
            PrimaryContainer={
                "Image": "811284226046.dkr.ecr.ap-south-1.amazonaws.com/xgboost:latest",
                "ModelDataUrl": model_data_url,
            },
            ExecutionRoleArn=role_arn,
            Tags=[{"Key": "Project", "Value": PROJECT}],
        )
        logger.info(f"Created SageMaker model: {model_name}")
    except ClientError as e:
        if "AlreadyExists" in str(e):
            logger.info(f"Model {model_name} exists, updating...")
            # Delete and recreate
            try:
                sm.delete_model(ModelName=model_name)
                time.sleep(5)
                sm.create_model(
                    ModelName=model_name,
                    PrimaryContainer={
                        "Image": "811284226046.dkr.ecr.ap-south-1.amazonaws.com/xgboost:latest",
                        "ModelDataUrl": model_data_url,
                    },
                    ExecutionRoleArn=role_arn,
                    Tags=[{"Key": "Project", "Value": PROJECT}],
                )
            except ClientError as e2:
                logger.error(f"Failed to update model: {e2}")
                raise
        else:
            raise

    # Create endpoint config
    config_name = f"{SAGEMAKER_ENDPOINT}-config"
    try:
        sm.create_endpoint_config(
            EndpointConfigName=config_name,
            ProductionVariants=[
                {
                    "VariantName": "primary",
                    "ModelName": model_name,
                    "InstanceType": SAGEMAKER_INSTANCE_TYPE_INFERENCE,
                    "InitialInstanceCount": 1,
                    "InitialVariantWeight": 1.0,
                },
            ],
            Tags=[{"Key": "Project", "Value": PROJECT}],
        )
        logger.info(f"Created endpoint config: {config_name}")
    except ClientError as e:
        if "AlreadyExists" in str(e):
            logger.info(f"Endpoint config {config_name} exists")
        else:
            raise

    # Create or update endpoint
    try:
        sm.describe_endpoint(EndpointName=SAGEMAKER_ENDPOINT)
        # Endpoint exists — update it
        sm.update_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            EndpointConfigName=config_name,
        )
        logger.info(f"Updating endpoint: {SAGEMAKER_ENDPOINT}")
    except ClientError:
        # Create new endpoint
        sm.create_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            EndpointConfigName=config_name,
            Tags=[{"Key": "Project", "Value": PROJECT}],
        )
        logger.info(f"Creating endpoint: {SAGEMAKER_ENDPOINT}")

    # Wait for endpoint to be in service
    logger.info("Waiting for endpoint to be in service (this may take 5-10 minutes)...")
    try:
        waiter = sm.get_waiter("endpoint_in_service")
        waiter.wait(EndpointName=SAGEMAKER_ENDPOINT, WaiterConfig={"Delay": 30, "MaxAttempts": 20})
        logger.info(f"Endpoint {SAGEMAKER_ENDPOINT} is in service!")
    except Exception as e:
        logger.warning(f"Endpoint waiter timed out: {e}")

    # Setup auto-scaling
    _setup_autoscaling(model_name)


def _setup_autoscaling(model_name: str):
    """Configure auto-scaling for the SageMaker endpoint."""
    aas = boto3.client("application-autoscaling", region_name=REGION)

    resource_id = f"endpoint/{SAGEMAKER_ENDPOINT}/variant/primary"

    try:
        aas.register_scalable_target(
            ServiceNamespace="sagemaker",
            ResourceId=resource_id,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            MinCapacity=SAGEMAKER_AUTO_MIN,
            MaxCapacity=SAGEMAKER_AUTO_MAX,
        )

        # Target tracking on invocations per instance
        aas.put_scaling_policy(
            PolicyName=f"{PROJECT}-auto-scaling",
            ServiceNamespace="sagemaker",
            ResourceId=resource_id,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            PolicyType="TargetTrackingScaling",
            TargetTrackingScalingPolicyConfiguration={
                "TargetValue": 750.0,  # Invocations per instance per minute
                "PredefinedMetricSpecification": {
                    "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance",
                },
                "ScaleInCooldown": 300,
                "ScaleOutCooldown": 60,
            },
        )
        logger.info(f"Auto-scaling configured: {SAGEMAKER_AUTO_MIN}-{SAGEMAKER_AUTO_MAX} instances")
    except ClientError as e:
        logger.warning(f"Auto-scaling setup failed: {e}")


# ─── Lambda ──────────────────────────────────────────────────────

def deploy_lambda_functions(role_arn: str):
    """Package and deploy all Lambda functions."""
    lam = _lambda_client()
    account_id = _account_id()
    zip_path = _lambda_zip_path()

    for func_name, config in LAMBDA_FUNCTIONS.items():
        full_name = f"{PROJECT}-{func_name}"

        # Read zip bytes
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        env_vars = {
            "STAGE": os.getenv("STAGE", "dev"),
            "AWS_REGION": REGION,
            "S3_BUCKET": S3_DATA_BUCKET,
            "S3_MODELS_BUCKET": S3_MODELS_BUCKET,
            "SAGEMAKER_ENDPOINT": SAGEMAKER_ENDPOINT,
            "PREDICTIONS_TABLE": f"{PROJECT}-crop_prices",
            "CALL_LOG_TABLE": f"{PROJECT}-call_logs",
            "SESSIONS_TABLE": f"{PROJECT}-user_sessions",
            "SARVAM_API_KEY": os.getenv("SARVAM_API_KEY", ""),
            "EXOTEL_SID": os.getenv("EXOTEL_SID", ""),
            "EXOTEL_API_KEY": os.getenv("EXOTEL_API_KEY", ""),
            "PUBLIC_API_BASE": os.getenv("PUBLIC_API_BASE", ""),
        }

        try:
            # Check if exists
            lam.get_function(FunctionName=full_name)
            # Update code
            lam.update_function_code(
                FunctionName=full_name,
                ZipFile=zip_bytes,
            )
            lam.update_function_configuration(
                FunctionName=full_name,
                Timeout=config["timeout"],
                MemorySize=config["memory"],
                Environment={"Variables": env_vars},
            )
            logger.info(f"Updated Lambda: {full_name}")
        except ClientError:
            # Create new
            lam.create_function(
                FunctionName=full_name,
                Runtime="python3.11",
                Role=role_arn,
                Handler="backend.ivr.handler.handler" if "ivr" in func_name else "backend.prediction.aws.lambda_handler.handler_daily_update",
                Code={"ZipFile": zip_bytes},
                Timeout=config["timeout"],
                MemorySize=config["memory"],
                Description=config["description"],
                Environment={"Variables": env_vars},
                Tags={"Project": PROJECT},
            )
            logger.info(f"Created Lambda: {full_name}")

    # Cleanup temp zip
    zip_path.unlink(missing_ok=True)


# ─── API Gateway ─────────────────────────────────────────────────

def deploy_api_gateway() -> str:
    """Create REST API Gateway with routes. Returns API ID."""
    apigw = _apigw_client()

    # Check for existing API
    apis = apigw.get_rest_apis()
    existing = [a for a in apis.get("items", []) if a["name"] == API_NAME]

    if existing:
        api_id = existing[0]["id"]
        logger.info(f"API Gateway exists: {api_id}")
        return api_id

    # Create new API
    api = apigw.create_rest_api(
        name=API_NAME,
        description="AgriConnect Crop Price Prediction API",
        apiKeySource="HEADER",
        endpointConfiguration={"types": ["REGIONAL"]},
        tags={"Project": PROJECT},
    )
    api_id = api["id"]
    logger.info(f"Created API Gateway: {api_id}")

    # Get root resource
    resources = apigw.get_resources(restApiId=api_id)
    root_id = resources["items"][0]["id"]

    # Create /api resource
    api_resource = apigw.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart="api",
    )

    # Create /api/{proxy+} catch-all
    proxy_resource = apigw.create_resource(
        restApiId=api_id,
        parentId=api_resource["id"],
        pathPart="{proxy+}",
    )

    # Add ANY method to proxy
    account_id = _account_id()
    lambda_arn = f"arn:aws:lambda:{REGION}:{account_id}:function:{PROJECT}-api_handler"

    apigw.put_method(
        restApiId=api_id,
        resourceId=proxy_resource["id"],
        httpMethod="ANY",
        authorizationType="NONE",
        apiKeyRequired=True,
    )

    apigw.put_integration(
        restApiId=api_id,
        resourceId=proxy_resource["id"],
        httpMethod="ANY",
        type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations",
    )

    # Also add root /api ANY method
    apigw.put_method(
        restApiId=api_id,
        resourceId=api_resource["id"],
        httpMethod="ANY",
        authorizationType="NONE",
        apiKeyRequired=True,
    )

    apigw.put_integration(
        restApiId=api_id,
        resourceId=api_resource["id"],
        httpMethod="ANY",
        type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations",
    )

    # Grant Lambda permission to be invoked by API Gateway
    lam = _lambda_client()
    try:
        lam.add_permission(
            FunctionName=f"{PROJECT}-api_handler",
            StatementId=f"{PROJECT}-apigw-{int(time.time())}",
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=f"arn:aws:execute-api:{REGION}:{account_id}:{api_id}/*/*",
        )
    except ClientError as e:
        if "ResourceConflictException" not in str(e):
            logger.warning(f"Lambda permission warning: {e}")

    # Create API key
    try:
        api_key = apigw.create_api_key(
            name=f"{PROJECT}-api-key",
            enabled=True,
            generateDistinctId=False,
        )
        key_id = api_key["id"]

        # Create usage plan
        usage_plan = apigw.create_usage_plan(
            name=f"{PROJECT}-usage-plan",
            throttle={"rateLimit": API_THROTTLE_RATE, "burstLimit": API_THROTTLE_BURST},
            quota={"limit": 10000, "period": "DAY"},
            apiStages=[{"apiId": api_id, "stage": "prod"}],
        )

        apigw.create_usage_plan_key(
            usagePlanId=usage_plan["id"],
            keyId=key_id,
            keyType="API_KEY",
        )
        logger.info(f"Created API key: {api_key['name']} (save this: {api_key.get('value', 'check console')})")
    except ClientError as e:
        logger.warning(f"API key creation: {e}")

    # Deploy to prod stage
    apigw.create_deployment(
        restApiId=api_id,
        stageName="prod",
        description=f"AgriConnect API deployment {datetime.now().isoformat()}",
    )

    logger.info(f"API Gateway deployed: https://{api_id}.execute-api.{REGION}.amazonaws.com/prod/")

    return api_id


# ─── EventBridge ─────────────────────────────────────────────────

def setup_eventbridge_rules():
    """Create EventBridge rules for scheduled triggers."""
    events = _events_client()
    account_id = _account_id()

    for rule_config in EVENTBRIDGE_RULES:
        # Create or update rule
        events.put_rule(
            Name=rule_config["name"],
            ScheduleExpression=rule_config["schedule"],
            State="ENABLED",
            Description=rule_config["description"],
        )
        logger.info(f"EventBridge rule: {rule_config['name']} ({rule_config['schedule']})")

        # Add Lambda target
        lambda_arn = f"arn:aws:lambda:{REGION}:{account_id}:function:{PROJECT}-{rule_config['target']}"

        events.put_targets(
            Rule=rule_config["name"],
            Targets=[
                {
                    "Id": f"{rule_config['target']}-target",
                    "Arn": lambda_arn,
                    "Input": json.dumps(rule_config["input"]),
                }
            ],
        )

        # Grant permission
        lam = _lambda_client()
        try:
            lam.add_permission(
                FunctionName=f"{PROJECT}-{rule_config['target']}",
                StatementId=f"{rule_config['name']}-perm-{int(time.time())}",
                Action="lambda:InvokeFunction",
                Principal="events.amazonaws.com",
                SourceArn=f"arn:aws:events:{REGION}:{account_id}:rule/{rule_config['name']}",
            )
        except ClientError as e:
            if "ResourceConflictException" not in str(e):
                logger.warning(f"EventBridge permission: {e}")


# ─── Teardown ────────────────────────────────────────────────────

def teardown(stage: str):
    """Destroy all resources for a stage."""
    logger.warning(f"⚠️  Tearing down {stage} environment...")

    # Delete API Gateway
    try:
        apigw = _apigw_client()
        apis = apigw.get_rest_apis()
        for api in apis.get("items", []):
            if api["name"] == API_NAME:
                apigw.delete_rest_api(restApiId=api["id"])
                logger.info(f"Deleted API Gateway: {api['id']}")
    except Exception as e:
        logger.warning(f"API Gateway cleanup: {e}")

    # Delete Lambda functions
    try:
        lam = _lambda_client()
        for func_name in LAMBDA_FUNCTIONS:
            full_name = f"{PROJECT}-{func_name}"
            try:
                lam.delete_function(FunctionName=full_name)
                logger.info(f"Deleted Lambda: {full_name}")
            except ClientError:
                pass
    except Exception as e:
        logger.warning(f"Lambda cleanup: {e}")

    # Delete EventBridge rules
    try:
        events = _events_client()
        for rule_config in EVENTBRIDGE_RULES:
            try:
                events.remove_targets(Rule=rule_config["name"], Ids=[f"{rule_config['target']}-target"])
                events.delete_rule(Name=rule_config["name"])
                logger.info(f"Deleted EventBridge rule: {rule_config['name']}")
            except ClientError:
                pass
    except Exception as e:
        logger.warning(f"EventBridge cleanup: {e}")

    # Delete SageMaker endpoint
    try:
        sm = _sagemaker_client()
        try:
            sm.delete_endpoint(EndpointName=SAGEMAKER_ENDPOINT)
            logger.info(f"Deleted SageMaker endpoint: {SAGEMAKER_ENDPOINT}")
        except ClientError:
            pass
        try:
            sm.delete_endpoint_config(EndpointConfigName=f"{SAGEMAKER_ENDPOINT}-config")
        except ClientError:
            pass
        try:
            sm.delete_model(ModelName=f"{PROJECT}-model")
        except ClientError:
            pass
    except Exception as e:
        logger.warning(f"SageMaker cleanup: {e}")

    # Delete DynamoDB tables
    try:
        dynamodb = _dynamodb_client()
        for table_name in DYNAMODB_TABLES:
            full_name = f"{PROJECT}-{table_name}"
            try:
                dynamodb.delete_table(TableName=full_name)
                logger.info(f"Deleted DynamoDB table: {full_name}")
            except ClientError:
                pass
    except Exception as e:
        logger.warning(f"DynamoDB cleanup: {e}")

    # Delete S3 buckets (empty them first)
    try:
        s3 = _s3_client()
        for bucket_name in [S3_DATA_BUCKET, S3_MODELS_BUCKET]:
            try:
                # Delete all objects
                resp = s3.list_objects_v2(Bucket=bucket_name)
                objects = resp.get("Contents", [])
                if objects:
                    s3.delete_objects(
                        Bucket=bucket_name,
                        Delete={"Objects": [{"Key": o["Key"]} for o in objects]},
                    )
                s3.delete_bucket(Bucket=bucket_name)
                logger.info(f"Deleted S3 bucket: {bucket_name}")
            except ClientError:
                pass
    except Exception as e:
        logger.warning(f"S3 cleanup: {e}")

    logger.info(f"✅ Teardown complete for {stage}")


# ─── Status ──────────────────────────────────────────────────────

def show_status():
    """Print status of all AWS resources."""
    print(f"\n{'='*60}")
    print(f"  AgriConnect AWS Stack Status — {REGION}")
    print(f"{'='*60}\n")

    # S3
    s3 = _s3_client()
    for bucket in [S3_DATA_BUCKET, S3_MODELS_BUCKET]:
        try:
            s3.head_bucket(Bucket=bucket)
            print(f"  ✅ S3: {bucket}")
        except ClientError:
            print(f"  ❌ S3: {bucket} (not found)")

    # DynamoDB
    dynamodb = _dynamodb_client()
    for table_name in DYNAMODB_TABLES:
        full_name = f"{PROJECT}-{table_name}"
        try:
            resp = dynamodb.describe_table(TableName=full_name)
            count = resp["Table"].get("ItemCount", 0)
            print(f"  ✅ DynamoDB: {full_name} ({count} items)")
        except ClientError:
            print(f"  ❌ DynamoDB: {full_name} (not found)")

    # Lambda
    lam = _lambda_client()
    for func_name in LAMBDA_FUNCTIONS:
        full_name = f"{PROJECT}-{func_name}"
        try:
            resp = lam.get_function(FunctionName=full_name)
            last_modified = resp["Configuration"]["LastModified"]
            print(f"  ✅ Lambda: {full_name} (modified: {last_modified})")
        except ClientError:
            print(f"  ❌ Lambda: {full_name} (not found)")

    # SageMaker
    sm = _sagemaker_client()
    try:
        resp = sm.describe_endpoint(EndpointName=SAGEMAKER_ENDPOINT)
        status = resp["EndpointStatus"]
        emoji = "✅" if status == "InService" else "⏳"
        print(f"  {emoji} SageMaker Endpoint: {SAGEMAKER_ENDPOINT} ({status})")
    except ClientError:
        print(f"  ❌ SageMaker Endpoint: {SAGEMAKER_ENDPOINT} (not found)")

    # API Gateway
    apigw = _apigw_client()
    try:
        apis = apigw.get_rest_apis()
        found = [a for a in apis.get("items", []) if a["name"] == API_NAME]
        if found:
            url = f"https://{found[0]['id']}.execute-api.{REGION}.amazonaws.com/prod/"
            print(f"  ✅ API Gateway: {url}")
        else:
            print(f"  ❌ API Gateway: {API_NAME} (not found)")
    except ClientError:
        print(f"  ❌ API Gateway: (error)")

    # EventBridge
    events = _events_client()
    for rule_config in EVENTBRIDGE_RULES:
        try:
            resp = events.describe_rule(Name=rule_config["name"])
            state = resp["State"]
            emoji = "✅" if state == "ENABLED" else "⏸️"
            print(f"  {emoji} EventBridge: {rule_config['name']} ({state})")
        except ClientError:
            print(f"  ❌ EventBridge: {rule_config['name']} (not found)")

    print()


# ─── Main Deploy ─────────────────────────────────────────────────

def deploy_all(stage: str = "dev"):
    """Deploy the complete AWS stack."""
    print(f"\n🚀 Deploying AgriConnect to AWS ({stage}) in {REGION}\n")

    start = time.time()

    # 1. IAM
    print("━━━ 1/7 IAM Roles ━━━")
    sagemaker_role_arn = setup_sagemaker_role()
    lambda_role_arn = setup_lambda_role()

    # 2. S3
    print("\n━━━ 2/7 S3 Buckets ━━━")
    setup_s3_buckets()

    # 3. DynamoDB
    print("\n━━━ 3/7 DynamoDB Tables ━━━")
    setup_dynamodb_tables()

    # 4. Lambda
    print("\n━━━ 4/7 Lambda Functions ━━━")
    deploy_lambda_functions(lambda_role_arn)

    # 5. API Gateway
    print("\n━━━ 5/7 API Gateway ━━━")
    api_id = deploy_api_gateway()

    # 6. EventBridge
    print("\n━━━ 6/7 EventBridge Rules ━━━")
    setup_eventbridge_rules()

    # 7. SageMaker
    print("\n━━━ 7/7 SageMaker ━━━")
    try:
        job_name = create_sagemaker_training_job(sagemaker_role_arn)
        print(f"  Training job started: {job_name}")
        print("  (Run --deploy-sagemaker separately after training completes)")
    except Exception as e:
        print(f"  ⚠️  SageMaker training skipped: {e}")
        print("  Deploy endpoint manually after training: --deploy-sagemaker")

    elapsed = time.time() - start
    print(f"\n✅ Deployment complete in {elapsed:.0f}s")
    print(f"\n📋 Next steps:")
    print(f"  1. Upload training data: aws s3 cp data/ s3://{S3_DATA_BUCKET}/training/ --recursive")
    print(f"  2. Wait for training job to complete")
    print(f"  3. Deploy endpoint: python -m backend.aws.deploy --stage {stage} deploy-sagemaker")
    print(f"  4. Test API: curl https://{api_id}.execute-api.{REGION}.amazonaws.com/prod/api/health")


def deploy_sagemaker_only():
    """Deploy just the SageMaker endpoint (after training is complete)."""
    print("\n🚀 Deploying SageMaker Endpoint\n")
    role_arn = setup_sagemaker_role()
    deploy_sagemaker_endpoint(role_arn)
    print("\n✅ SageMaker endpoint deployed!")


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AgriConnect AWS Deployment")
    parser.add_argument("--stage", default="dev", choices=["dev", "staging", "prod"])
    parser.add_argument("action", nargs="?", default="deploy",
                        choices=["deploy", "teardown", "status", "deploy-sagemaker"])
    args = parser.parse_args()

    os.environ["STAGE"] = args.stage

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.action == "deploy":
        deploy_all(args.stage)
    elif args.action == "teardown":
        teardown(args.stage)
    elif args.action == "status":
        show_status()
    elif args.action == "deploy-sagemaker":
        deploy_sagemaker_only()


if __name__ == "__main__":
    main()
