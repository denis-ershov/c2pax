"""Тесты интеграции с FastAPI UploadFile."""

import asyncio
import io
from typing import Any

from c2pax.backend.mock import MockC2paBackend
from c2pax.integrations.fastapi import inspect_upload, verify_upload
from c2pax.verification.policy import VerificationPolicy
from c2pax.verification.status import VerificationStatus


class DummyUploadFile:
    """Mock-объект UploadFile для асинхронного тестирования."""

    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self.file = io.BytesIO(content)

    async def seek(self, offset: int) -> None:
        self.file.seek(offset)

    async def read(self, size: int = -1) -> bytes:
        return self.file.read(size)


def test_fastapi_inspect_and_verify_upload(
    sample_jpeg_bytes: bytes,
    sample_c2pa_manifest_data: dict[str, Any],
) -> None:
    async def _run() -> None:
        upload = DummyUploadFile("sample.jpg", sample_jpeg_bytes)

        backend = MockC2paBackend()
        backend.set_mock_manifest("sample.jpg", sample_c2pa_manifest_data)

        # 1. Async Inspect
        info = await inspect_upload(upload, backend=backend)
        assert info.has_c2pa is True
        assert info.metadata.title == "Sunset Landscape"

        # 2. Async Verify
        res = await verify_upload(upload, policy=VerificationPolicy.permissive(), backend=backend)
        assert res.status == VerificationStatus.VALID
        assert res.valid is True

    asyncio.run(_run())
