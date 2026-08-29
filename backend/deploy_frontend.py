"""Deploy dist/ to S3."""
import boto3, os

s3 = boto3.client('s3', region_name='ap-south-1')
bucket = 'agriconnect-frontend-dev'
dist = 'dist'

# Clear old assets
resp = s3.list_objects_v2(Bucket=bucket, Prefix='assets/')
if 'Contents' in resp:
    for obj in resp['Contents']:
        s3.delete_object(Bucket=bucket, Key=obj['Key'])
    print(f'Cleared {len(resp["Contents"])} old assets')

# Upload
count = 0
for root, dirs, files in os.walk(dist):
    for f in files:
        fp = os.path.join(root, f)
        key = os.path.relpath(fp, dist).replace("\\", "/")
        ct = "text/html" if f.endswith(".html") else "application/javascript" if f.endswith(".js") else "text/css" if f.endswith(".css") else "application/octet-stream"
        s3.upload_file(fp, bucket, key, ExtraArgs={"ContentType": ct, "CacheControl": "no-cache"})
        count += 1
print(f"Uploaded {count} files to s3://{bucket}")
