import io
import asyncio
import logging
from typing import Any
import aioboto3
from contextlib import asynccontextmanager
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

class R2StorageGateway:
    def __init__(self) -> None:
        self.endpoint_url = getattr(settings, "R2_ENDPOINT_URL", None)
        self.access_key = getattr(settings, "R2_ACCESS_KEY_ID", None)
        self.secret_key = getattr(settings, "R2_SECRET_ACCESS_KEY", None)
        self.bucket_name = getattr(settings, "R2_BUCKET_NAME", None)
        self.region_name = getattr(settings, "R2_REGION_NAME", "auto")
        self.session = aioboto3.Session()

    @asynccontextmanager
    async def _get_client(self):
        if not self.endpoint_url or not self.access_key or not self.secret_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cloudflare R2 storage is not configured.",
            )
        async with self.session.client(
            service_name="s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region_name,
        ) as client:
            yield client

    async def upload_bytes(self, *, object_name: str, data: bytes, content_type: str | None) -> None:
        stream = io.BytesIO(data)
        extra_args: dict[str, str] = {}
        if content_type: extra_args["ContentType"] = content_type
        try:
            async with self._get_client() as client:
                await client.upload_fileobj(
                    stream,
                    self.bucket_name,
                    object_name,
                    ExtraArgs=extra_args if extra_args else None,
                )
        except ClientError as exc:
            raise HTTPException(status_code=503, detail="Failed to upload file to Cloudflare R2.") from exc

    async def delete_object(self, object_name: str) -> None:
        if not self.endpoint_url or not self.access_key or not self.secret_key: return
        max_retries = 5
        for attempt in range(max_retries):
            try:
                async with self._get_client() as client:
                    await client.delete_object(Bucket=self.bucket_name, Key=object_name)
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to delete object {object_name}: {e}")
                    raise HTTPException(status_code=500, detail="Failed to delete file from storage.")
                await asyncio.sleep(1)

    async def generate_presigned_put_url(self, *, object_name: str, expires_in: int = 3600, content_type: str | None = None, metadata: dict[str, str] | None = None) -> str:
        params: dict[str, object] = {"Bucket": self.bucket_name, "Key": object_name}
        if content_type: params["ContentType"] = content_type
        if metadata: params["Metadata"] = metadata
        try:
            async with self._get_client() as client:
                return await client.generate_presigned_url(ClientMethod="put_object", Params=params, ExpiresIn=expires_in)
        except ClientError as exc:
            raise HTTPException(status_code=503, detail="Failed to generate presigned upload URL.") from exc

    async def generate_presigned_get_url(self, *, object_name: str, expires_in: int = 3600) -> str:
        params = {"Bucket": self.bucket_name, "Key": object_name}
        try:
            async with self._get_client() as client:
                return await client.generate_presigned_url(ClientMethod="get_object", Params=params, ExpiresIn=expires_in)
        except ClientError as exc:
            raise HTTPException(status_code=503, detail="Failed to generate presigned download URL.") from exc

    async def generate_presigned_post(self, *, object_name: str, expires_in: int = 3600, content_type: str | None = None, max_file_size: int | None = None) -> dict[str, object]:
        fields: dict[str, str] = {"key": object_name}
        conditions: list[object] = []
        if content_type:
            conditions.append(["eq", "$Content-Type", content_type])
            fields["Content-Type"] = content_type
        if max_file_size is not None:
            conditions.append(["content-length-range", 0, max_file_size])
        try:
            async with self._get_client() as client:
                return await client.generate_presigned_post(Bucket=self.bucket_name, Key=object_name, Fields=fields if fields else None, Conditions=conditions if conditions else None, ExpiresIn=expires_in)
        except ClientError as exc:
            raise HTTPException(status_code=503, detail="Failed to generate presigned POST.") from exc

    async def head_object(self, object_name: str) -> dict[str, Any] | None:
        try:
            async with self._get_client() as client:
                return await client.head_object(Bucket=self.bucket_name, Key=object_name)
        except ClientError as exc:
            if str(exc.response.get("Error", {}).get("Code", "")) in ("404", "NoSuchKey", "NotFound"):
                return None
            raise HTTPException(status_code=503, detail="Failed to verify storage object.") from exc

    async def create_multipart_upload(self, *, object_name: str, content_type: str | None = None) -> str:
        kwargs: dict[str, Any] = {"Bucket": self.bucket_name, "Key": object_name}
        if content_type: kwargs["ContentType"] = content_type
        try:
            async with self._get_client() as client:
                res = await client.create_multipart_upload(**kwargs)
                return res["UploadId"]
        except ClientError as exc:
            raise HTTPException(status_code=503, detail="Failed to initiate multipart upload.") from exc

    async def generate_presigned_part_url(self, *, object_name: str, upload_id: str, part_number: int, expires_in: int = 600) -> str:
        params = {"Bucket": self.bucket_name, "Key": object_name, "UploadId": upload_id, "PartNumber": part_number}
        try:
            async with self._get_client() as client:
                return await client.generate_presigned_url(ClientMethod="upload_part", Params=params, ExpiresIn=expires_in)
        except ClientError as exc:
            raise HTTPException(status_code=503, detail="Failed to generate URL for upload part.") from exc

    async def complete_multipart_upload(self, *, object_name: str, upload_id: str, parts: list[dict[str, Any]]) -> None:
        try:
            async with self._get_client() as client:
                await client.complete_multipart_upload(Bucket=self.bucket_name, Key=object_name, UploadId=upload_id, MultipartUpload={"Parts": parts})
        except ClientError as exc:
            raise HTTPException(status_code=503, detail="Failed to complete multipart upload.") from exc

    async def abort_multipart_upload(self, *, object_name: str, upload_id: str) -> None:
        try:
            async with self._get_client() as client:
                await client.abort_multipart_upload(Bucket=self.bucket_name, Key=object_name, UploadId=upload_id)
        except ClientError:
            pass
