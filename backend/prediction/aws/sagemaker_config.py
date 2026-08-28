"""
SageMaker Configuration for Crop Price Prediction Training
Handles model training jobs, endpoints, and hyperparameter tuning
"""
import os

# SageMaker settings
SAGEMAKER_ROLE = os.getenv("SAGEMAKER_ROLE", "arn:aws:iam::role/SageMakerExecutionRole")
S3_BUCKET = os.getenv("S3_BUCKET", "agriconnect-prediction-data")
S3_TRAINING_PREFIX = "training-data"
S3_MODEL_PREFIX = "models"
S3_OUTPUT_PREFIX = "output"

# Training instance
TRAINING_INSTANCE = "ml.m5.xlarge"      # 4 vCPU, 16 GB RAM
INFERENCE_INSTANCE = "ml.t2.medium"      # 2 vCPU, 4 GB RAM (for inference)

# Hyperparameter ranges for tuning
HYPERPARAMETER_RANGES = {
    "xgboost": {
        "max_depth": {"MinValue": 3, "MaxValue": 10},
        "learning_rate": {"MinValue": 0.01, "MaxValue": 0.3},
        "n_estimators": {"MinValue": 100, "MaxValue": 2000},
        "subsample": {"MinValue": 0.6, "MaxValue": 1.0},
        "colsample_bytree": {"MinValue": 0.6, "MaxValue": 1.0},
    },
    "lstm": {
        "lstm_units_1": {"MinValue": 32, "MaxValue": 256},
        "lstm_units_2": {"MinValue": 16, "MaxValue": 128},
        "dropout": {"MinValue": 0.1, "MaxValue": 0.4},
        "learning_rate": {"MinValue": 0.0001, "MaxValue": 0.01},
    },
}

# Docker image for custom training container
ECR_REPO = os.getenv("ECR_REPO", "agriconnect-prediction")
DOCKER_BASE_IMAGE = "763104351884.dkr.ecr.ap-south-1.amazonaws.com/pytorch-training:2.0.0-gpu-py310-cu117-ubuntu20.04-sagemaker"


def get_training_job_config(crop, state, model_type="xgboost"):
    """Generate SageMaker training job configuration."""
    return {
        "TrainingJobName": f"agriconnect-{crop}-{state}-{model_type}-{__import__('datetime').datetime.now().strftime('%Y%m%d%H%M%S')}",
        "AlgorithmSpecification": {
            "TrainingImage": DOCKER_BASE_IMAGE,
            "TrainingInputMode": "File",
        },
        "RoleArn": SAGEMAKER_ROLE,
        "InputDataConfig": [
            {
                "ChannelName": "training",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": f"s3://{S3_BUCKET}/{S3_TRAINING_PREFIX}/{crop}/{state}/",
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
            },
        ],
        "OutputDataConfig": {
            "S3OutputPath": f"s3://{S3_BUCKET}/{S3_OUTPUT_PREFIX}/{crop}/{state}/",
        },
        "ResourceConfig": {
            "InstanceCount": 1,
            "InstanceType": TRAINING_INSTANCE,
            "VolumeSizeInGB": 50,
        },
        "StoppingCondition": {
            "MaxRuntimeInSeconds": 3600,
        },
        "HyperParameters": {
            "crop": crop,
            "state": state,
            "model_type": model_type,
        },
        "Tags": [
            {"Key": "Project", "Value": "AgriConnect"},
            {"Key": "Crop", "Value": crop},
            {"Key": "State", "Value": state},
        ],
    }


def get_endpoint_config(model_data_url, model_name):
    """Generate SageMaker endpoint configuration for deployment."""
    return {
        "EndpointConfigName": f"{model_name}-config",
        "ProductionVariants": [
            {
                "VariantName": "primary",
                "ModelName": model_name,
                "InstanceType": INFERENCE_INSTANCE,
                "InitialInstanceCount": 1,
                "InitialVariantWeight": 1.0,
            },
        ],
        "Tags": [
            {"Key": "Project", "Value": "AgriConnect"},
        ],
    }
