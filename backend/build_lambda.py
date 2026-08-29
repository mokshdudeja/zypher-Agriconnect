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
for d in ["ivr", "prediction/api", "sarvam"]:
    os.makedirs(os.path.join(BUILD, d), exist_ok=True)

# Copy source files
shutil.copy(os.path.join(ROOT, "backend/ivr/handler.py"), os.path.join(BUILD, "ivr/"))
shutil.copy(os.path.join(ROOT, "backend/ivr/farmer_phone.py"), os.path.join(BUILD, "ivr/"))
shutil.copy(os.path.join(ROOT, "backend/prediction/api/app.py"), os.path.join(BUILD, "prediction/api/"))
shutil.copy(os.path.join(ROOT, "backend/voice_agents.py"), os.path.join(BUILD, "voice_agents.py"))
shutil.copy(os.path.join(ROOT, "backend/sarvam/api.py"), os.path.join(BUILD, "sarvam/api.py"))

# Create __init__.py files
for init in ["prediction/__init__.py", "prediction/api/__init__.py", "ivr/__init__.py", "sarvam/__init__.py"]:
    open(os.path.join(BUILD, init), "w").close()

# Install dependencies
print("Installing dependencies...")
subprocess.run(
    ["pip", "install", "fastapi", "mangum", "requests", "pydantic", "boto3", "python-multipart", "-t", BUILD, "-q"],
    check=True,
)

# Re-extract Linux pydantic_core .so (pip install overwrites with Windows version)
print("Fixing pydantic_core for Linux...")
subprocess.run(
    ["pip", "download", "pydantic_core==2.46.5", "--platform", "manylinux2014_x86_64",
     "--python-version", "3.11", "--only-binary=:all:", "-d", "C:/tmp/wheels"],
    check=True, capture_output=True,
)
import zipfile as _zf
for f in os.listdir("C:/tmp/wheels"):
    if "pydantic_core" in f and "manylinux" in f:
        with _zf.ZipFile(os.path.join("C:/tmp/wheels", f)) as whl:
            for name in whl.namelist():
                if name.startswith("pydantic_core/") and not name.endswith(".dist-info/"):
                    whl.extract(name, BUILD)
        print("  Extracted Linux pydantic_core .so")
        break

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
