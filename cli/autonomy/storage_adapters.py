import boto3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("zana.sync.storage")

class S3StorageAdapter:
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket_name: str):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self.bucket = bucket_name

    def upload(self, local_path: Path, remote_name: str = "zana.vault"):
        logger.info(f"☁️ Uploading to S3: {remote_name}...")
        self.s3.upload_file(str(local_path), self.bucket, remote_name)
        logger.info("✅ Upload successful.")

    def download(self, local_path: Path, remote_name: str = "zana.vault"):
        logger.info(f"☁️ Downloading from S3: {remote_name}...")
        self.s3.download_file(self.bucket, remote_name, str(local_path))
        logger.info("✅ Download successful.")
