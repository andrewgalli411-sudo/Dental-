"""S3-backed ObjectStore. Activated at Phase 0 with AWS creds + a BAA.

Buckets must be private with SSE-KMS enforced by bucket policy. boto3 is imported
lazily so local/test environments don't need it installed or configured.
"""

from __future__ import annotations


class S3ObjectStore:
    def __init__(self, bucket: str, region: str, kms_key_id: str | None = None) -> None:
        import boto3  # lazy: only needed when S3 is actually used

        self._bucket = bucket
        self._kms_key_id = kms_key_id
        self._client = boto3.client("s3", region_name=region)

    def _extra_args(self, content_type: str) -> dict:
        args: dict = {"ContentType": content_type}
        if self._kms_key_id:
            args["ServerSideEncryption"] = "aws:kms"
            args["SSEKMSKeyId"] = self._kms_key_id
        else:
            args["ServerSideEncryption"] = "aws:kms"  # bucket default key
        return args

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=data, **self._extra_args(content_type)
        )

    def get(self, key: str) -> bytes:
        resp = self._client.get_object(Bucket=self._bucket, Key=key)
        return resp["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def presigned_url(self, key: str, expires_seconds: int) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
