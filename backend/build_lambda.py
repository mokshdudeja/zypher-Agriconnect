"""Build Lambda ZIP deployment package."""
import zipfile
import os
import shutil
import subprocess

BUILD = "C:/tmp/lambda-build"
ZIP_PATH = "C:/tmp/lambda.zip"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if os.path.exists(BUILD):
    shutil.rmtree(BUILD)

# Create dirs
for d in ["ivr", "prediction/api"]:
    os.makedirs(os.path.join(BUILD, d), exist_ok=True)

# Copy source files
shutil.copy(os.path.join(ROOT, "backend/ivr/handler.py"), os.path.join(BUILD, "ivr/"))
shutil.copy(os.path.join(ROOT, "backend/ivr/farmer_phone.py"), os.path.join(BUILD, "ivr/"))
shutil.copy(os.path.join(ROOT, "backend/prediction/api/app.py"), os.path.join(BUILD, "prediction/api/"))

# Create __init__.py files
for init in ["prediction/__init__.py", "prediction/api/__init__.py", "ivr/__init__.py"]:
    open(os.path.join(BUILD, init), "w").close()

# Install dependencies
print("Installing dependencies...")
subprocess.run(
    ["pip", "install", "fastapi", "mangum", "requests", "pydantic", "boto3", "-t", BUILD, "-q"],
    check=True,
)

# Create ZIP
print("Creating ZIP...")
with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(BUILD):
        for f in files:
            fp = os.path.join(root, f)
            arc = os.path.relpath(fp, BUILD).replace("\\", "/")
            zf.write(fp, arc)

size = os.path.getsize(ZIP_PATH)
print(f"DONE: {ZIP_PATH} ({size:,} bytes)")
