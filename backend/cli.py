"""
AgriConnect CLI — Development, Testing & Deployment

Usage:
    python -m backend.cli test --coverage
    python -m backend.cli deploy --stage dev
    python -m backend.cli status --stage dev
    python -m backend.cli predict --crop wheat --state uttar_pradesh
    python -m backend.cli ivr-test --crop wheat --state uttar_pradesh
    python -m backend.cli local
    python -m backend.cli logs --lambda api_handler
    python -m backend.cli train --crops wheat rice --states uttar_pradesh maharashtra
    python -m backend.cli daily-update
    python -m backend.cli weekly-retrain
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

try:
    import typer
    from typer import Exit
except ImportError:
    print("Typer not installed. Run: pip install typer[all]")
    sys.exit(1)

app = typer.Typer(
    name="agriconnect",
    help="AgriConnect — Development, Testing & Deployment CLI",
    add_completion=False,
)


# ─── Test ───────────────────────────────────────────────────────

@app.command()
def test(
    coverage: bool = typer.Option(False, "--coverage", "-c", help="Run with coverage report"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    marker: Optional[str] = typer.Option(None, "-m", "--marker", help="Run specific pytest marker"),
    module: Optional[str] = typer.Option(None, "-k", "--module", help="Run specific test module (e.g. test_ivr)"),
    parallel: bool = typer.Option(False, "-p", "--parallel", help="Run tests in parallel"),
):
    """Run pytest with optional coverage."""
    cmd = ["python", "-m", "pytest"]

    if verbose:
        cmd.append("-v")

    if marker:
        cmd.extend(["-m", marker])

    if module:
        cmd.extend(["-k", module])

    if parallel:
        cmd.extend(["-n", "auto"])

    if coverage:
        cmd = ["python", "-m", "pytest", "--cov=backend", "--cov-report=term-missing", "--cov-report=html:htmlcov"]
        if verbose:
            cmd.insert(2, "-v")
        if marker:
            cmd.extend(["-m", marker])
        if module:
            cmd.extend(["-k", module])

    cmd.append("backend/tests/")

    typer.echo(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parent.parent)
    raise Exit(result.returncode)


# ─── Deploy ─────────────────────────────────────────────────────

@app.command()
def deploy(
    stage: str = typer.Option("dev", "--stage", help="Deployment stage (dev/staging/prod)"),
    component: Optional[str] = typer.Option(None, "--component", help="Deploy specific: sagemaker, lambda, infrastructure"),
):
    """Deploy to AWS."""
    project_root = Path(__file__).resolve().parent.parent

    if component == "sagemaker":
        cmd = ["python", "-m", "backend.aws.deploy", "--stage", stage, "deploy-sagemaker"]
    elif component == "lambda":
        cmd = ["python", "-m", "backend.aws.deploy", "--stage", stage, "deploy"]
    elif component == "infrastructure":
        cmd = ["aws", "cloudformation", "deploy",
               "--template-file", str(project_root / "backend" / "aws" / "cloudformation.yaml"),
               "--stack-name", f"agriconnect-{stage}",
               "--parameter-overrides", f"Stage={stage}",
               "--capabilities", "CAPABILITY_IAM"]
    else:
        cmd = ["python", "-m", "backend.aws.deploy", "--stage", stage, "deploy"]

    typer.echo(f"Deploying to {stage}...")
    typer.echo(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=project_root)
    raise Exit(result.returncode)


# ─── Status ─────────────────────────────────────────────────────

@app.command()
def status(
    stage: str = typer.Option("dev", "--stage", help="Stage to check"),
):
    """Show status of all AWS resources."""
    project_root = Path(__file__).resolve().parent.parent
    cmd = ["python", "-m", "backend.aws.deploy", "--stage", stage, "status"]
    result = subprocess.run(cmd, cwd=project_root)
    raise Exit(result.returncode)


# ─── Logs ───────────────────────────────────────────────────────

@app.command()
def logs(
    lambda_name: str = typer.Option("api_handler", "--lambda", "-l", help="Lambda function name"),
    tail: bool = typer.Option(False, "--tail", "-t", help="Stream logs continuously"),
    since: Optional[str] = typer.Option(None, "--since", "-s", help="Show logs since (e.g. '1h', '2025-01-01')"),
    stage: str = typer.Option("dev", "--stage", help="Deployment stage"),
):
    """Stream CloudWatch logs for Lambda functions."""
    full_name = f"zypher-agriconnect-{lambda_name}-{stage}"

    if tail:
        cmd = ["aws", "logs", "tail", f"/aws/lambda/{full_name}", "--follow"]
    elif since:
        cmd = ["aws", "logs", "filter-log-events",
               "--log-group-name", f"/aws/lambda/{full_name}",
               "--start-time", since]
    else:
        cmd = ["aws", "logs", "filter-log-events",
               "--log-group-name", f"/aws/lambda/{full_name}",
               "--start-time", "1h"]

    typer.echo(f"Fetching logs for: {full_name}")
    result = subprocess.run(cmd)
    raise Exit(result.returncode)


# ─── IVR Test ───────────────────────────────────────────────────

@app.command("ivr-test")
def ivr_test_cmd(
    crop: str = typer.Option(..., "--crop", "-c", help="Crop name (english or hindi)"),
    state: str = typer.Option("uttar_pradesh", "--state", "-s", help="State name"),
    language: str = typer.Option("hi", "--language", "-l", help="Language (hi/en)"),
    phone: str = typer.Option("+919876543210", "--phone", help="Test phone number"),
):
    """Test IVR flow locally without a real call."""
    import requests

    base_url = os.getenv("IVR_BASE_URL", "http://localhost:8002")

    typer.echo(f"\n{'='*50}")
    typer.echo(f"  IVR Test — {crop} in {state}")
    typer.echo(f"{'='*50}\n")

    # 1. Simulate incoming call
    typer.echo("1. Simulating incoming call...")
    try:
        resp = requests.post(f"{base_url}/api/ivr/incoming", data={
            "CallSid": "test-cli-001",
            "From": phone,
            "To": "+911234567890",
            "Direction": "inbound",
        }, timeout=5)
        typer.echo(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            typer.echo(f"   ✅ Welcome message generated")
            if "<Gather" in resp.text:
                typer.echo(f"   ✅ Gather prompt ready")
        else:
            typer.echo(f"   ❌ Failed: {resp.text[:200]}")
    except requests.ConnectionError:
        typer.echo(f"   ⚠️  Server not running at {base_url}")
        typer.echo(f"   Run: uvicorn backend.ivr.handler:app --port 8002")

    # 2. Test crop lookup
    typer.echo(f"\n2. Testing crop lookup: {crop}...")
    try:
        resp = requests.post(f"{base_url}/api/ivr/test-crop", json={
            "crop": crop,
            "state": state,
        }, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            typer.echo(f"   ✅ Crop: {data.get('crop', 'N/A')}")
            typer.echo(f"   Price: ₹{data.get('prediction', {}).get('current_price', 'N/A')}/quintal")
            typer.echo(f"   Response: {data.get('response_text_hindi', 'N/A')[:80]}...")
        else:
            typer.echo(f"   ❌ Failed: {resp.text[:200]}")
    except requests.ConnectionError:
        typer.echo(f"   ⚠️  Server not running")

    # 3. Test TTS
    typer.echo(f"\n3. Testing TTS preview...")
    try:
        resp = requests.post(f"{base_url}/api/ivr/tts", json={
            "text": f"{crop} की कीमत जानने के लिए धन्यवाद",
            "language": "hi-IN",
        }, timeout=10)
        if resp.status_code == 200:
            typer.echo(f"   ✅ TTS audio generated ({len(resp.content)} bytes)")
        else:
            typer.echo(f"   ⚠️  TTS returned {resp.status_code}")
    except requests.ConnectionError:
        typer.echo(f"   ⚠️  Server not running")

    # 4. Show supported crops
    typer.echo(f"\n4. Supported crops:")
    try:
        resp = requests.get(f"{base_url}/api/ivr/crops", timeout=5)
        if resp.status_code == 200:
            for c in resp.json()["crops"]:
                typer.echo(f"   {c['name']:12s} {c['hindi']:6s}  keywords: {', '.join(c['voice_keywords'][:3])}")
    except requests.ConnectionError:
        pass

    typer.echo(f"\n{'='*50}")
    typer.echo(f"  Test complete!")
    typer.echo(f"{'='*50}\n")


# ─── Predict ────────────────────────────────────────────────────

@app.command()
def predict(
    crop: str = typer.Option(..., "--crop", "-c", help="Crop name"),
    state: str = typer.Option("uttar_pradesh", "--state", "-s", help="State name"),
    days: int = typer.Option(7, "--days", "-d", help="Forecast horizon"),
):
    """Get price prediction for a crop-state pair."""
    import requests

    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    typer.echo(f"\n  Price Prediction — {crop} in {state}\n")

    try:
        resp = requests.get(f"{base_url}/api/predict/{crop}/{state}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            typer.echo(f"  Crop:           {data['crop']}")
            typer.echo(f"  State:          {data['state']}")
            typer.echo(f"  Current Price:  ₹{data['current_price']:.0f}/quintal")
            typer.echo(f"  Predicted 7d:   ₹{data['predicted_price_7d']:.0f}/quintal")
            typer.echo(f"  Predicted 15d:  ₹{data['predicted_price_15d']:.0f}/quintal")
            typer.echo(f"  Predicted 30d:  ₹{data['predicted_price_30d']:.0f}/quintal")
            typer.echo(f"  Trend:          {data['trend']}")
            typer.echo(f"  Confidence:     {data['confidence']:.0%}")
            typer.echo(f"  Factors:        {', '.join(data['factors'][:5])}")
            if data.get("model_confidence"):
                typer.echo(f"  Model:          XGBoost (confidence: {data['model_confidence']:.0%})")
        else:
            typer.echo(f"  ❌ Error {resp.status_code}: {resp.text[:200]}")
    except requests.ConnectionError:
        typer.echo(f"  ⚠️  API not running at {base_url}")
        typer.echo(f"  Run: uvicorn backend.prediction.api.app:app --port 8000")

    typer.echo()


# ─── Local Dev Server ───────────────────────────────────────────

@app.command()
def local(
    port: int = typer.Option(8000, "--port", "-p", help="Port number"),
    app_type: str = typer.Option("prediction", "--app", "-a", help="App: prediction, ivr, sarvam, all"),
):
    """Start local development server with hot reload."""
    typer.echo(f"\n  Starting AgriConnect dev server ({app_type})...\n")

    apps = {
        "prediction": ("backend.prediction.api.app:app", 8000),
        "ivr": ("backend.ivr.handler:app", 8002),
        "sarvam": ("backend.sarvam.api:app", 8001),
    }

    if app_type == "all":
        typer.echo("  Starting all services:")
        for name, (module, p) in apps.items():
            typer.echo(f"    - {name}: http://localhost:{p}")
        typer.echo(f"\n  Run each in a separate terminal:")
        for name, (module, p) in apps.items():
            typer.echo(f"    uvicorn {module} --reload --port {p}")
        return

    if app_type not in apps:
        typer.echo(f"  Unknown app: {app_type}. Use: prediction, ivr, sarvam, all")
        raise Exit(1)

    module, default_port = apps[app_type]
    actual_port = port or default_port

    typer.echo(f"  URL: http://localhost:{actual_port}")
    typer.echo(f"  Docs: http://localhost:{actual_port}/docs")
    typer.echo()

    cmd = [
        sys.executable, "-m", "uvicorn", module,
        "--reload", "--host", "0.0.0.0", "--port", str(actual_port),
    ]
    subprocess.run(cmd)


# ─── Train ──────────────────────────────────────────────────────

@app.command()
def train(
    crops: Optional[str] = typer.Option(None, "--crops", help="Comma-separated crops (default: all)"),
    states: Optional[str] = typer.Option(None, "--states", help="Comma-separated states (default: all)"),
):
    """Train XGBoost models for crop-state pairs."""
    project_root = Path(__file__).resolve().parent.parent

    cmd = [sys.executable, "-m", "backend.prediction.data_pipeline", "full-train"]

    if crops:
        cmd.extend(["--crops"] + crops.split(","))
    if states:
        cmd.extend(["--states"] + states.split(","))

    typer.echo(f"Training models...")
    result = subprocess.run(cmd, cwd=project_root)
    raise Exit(result.returncode)


# ─── Daily Update ───────────────────────────────────────────────

@app.command("daily-update")
def daily_update_cmd():
    """Run daily data update pipeline."""
    project_root = Path(__file__).resolve().parent.parent
    cmd = [sys.executable, "-m", "backend.prediction.data_pipeline", "daily-update"]
    typer.echo("Running daily update...")
    result = subprocess.run(cmd, cwd=project_root)
    raise Exit(result.returncode)


# ─── Weekly Retrain ─────────────────────────────────────────────

@app.command("weekly-retrain")
def weekly_retrain_cmd():
    """Run weekly model retraining."""
    project_root = Path(__file__).resolve().parent.parent
    cmd = [sys.executable, "-m", "backend.prediction.data_pipeline", "weekly-retrain"]
    typer.echo("Running weekly retrain...")
    result = subprocess.run(cmd, cwd=project_root)
    raise Exit(result.returncode)


# ─── Collect Data ───────────────────────────────────────────────

@app.command()
def collect(
    crops: Optional[str] = typer.Option(None, "--crops", help="Comma-separated crops"),
    states: Optional[str] = typer.Option(None, "--states", help="Comma-separated states"),
):
    """Collect mandi + weather data from external APIs."""
    project_root = Path(__file__).resolve().parent.parent
    cmd = [sys.executable, "-m", "backend.prediction.data_pipeline", "collect-data"]
    if crops:
        cmd.extend(["--crops"] + crops.split(","))
    if states:
        cmd.extend(["--states"] + states.split(","))
    typer.echo("Collecting data...")
    result = subprocess.run(cmd, cwd=project_root)
    raise Exit(result.returncode)


if __name__ == "__main__":
    app()
