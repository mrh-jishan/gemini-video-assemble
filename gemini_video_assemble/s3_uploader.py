from pathlib import Path
from typing import Optional

try:
    import boto3
except ImportError:
    boto3 = None

class S3Uploader:
    def __init__(self, access_key: str, secret_key: str, region: str, bucket: str):
        if not boto3:
            raise RuntimeError("boto3 not installed")
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def upload(self, file_path: Path, key_prefix: str = "") -> str:
        key = f"{key_prefix}/{file_path.name}" if key_prefix else file_path.name
        # Remove leading slash if present
        if key.startswith("/"):
            key = key[1:]
            
        print(f"Uploading {file_path} to s3://{self.bucket}/{key}")
        self.client.upload_file(str(file_path), self.bucket, key)
        return f"s3://{self.bucket}/{key}"
