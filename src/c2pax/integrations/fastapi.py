"""Асинхронные потоковые хэндлеры для FastAPI (UploadFile)."""

from __future__ import annotations

from typing import Any

from c2pax.api import inspect, verify
from c2pax.backend.base import BaseC2paBackend
from c2pax.core.models import AssetInfo
from c2pax.verification.policy import VerificationPolicy
from c2pax.verification.result import VerificationResult
from c2pax.verification.trust import TrustStore

try:
    from fastapi import UploadFile

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    UploadFile = object  # type: ignore[assignment, misc]


async def inspect_upload(
    file: Any,
    backend: BaseC2paBackend | None = None,
) -> AssetInfo:
    """Асинхронно инспектирует загруженный через FastAPI файл без избыточной буферизации в память."""
    filename = getattr(file, "filename", None)
    content_type = getattr(file, "content_type", None)

    if hasattr(file, "file"):
        if hasattr(file, "seek"):
            await file.seek(0)
        res = inspect(file.file, filename=filename, mime_type=content_type, backend=backend)
        if hasattr(file, "seek"):
            await file.seek(0)
        return res

    return inspect(file, filename=filename, mime_type=content_type, backend=backend)


async def verify_upload(
    file: Any,
    policy: VerificationPolicy | None = None,
    trust_store: TrustStore | None = None,
    backend: BaseC2paBackend | None = None,
) -> VerificationResult:
    """Асинхронно верифицирует цифровой манифест загруженного файла FastAPI."""
    filename = getattr(file, "filename", None)
    content_type = getattr(file, "content_type", None)

    if hasattr(file, "file"):
        if hasattr(file, "seek"):
            await file.seek(0)
        res = verify(
            file.file,
            policy=policy,
            trust_store=trust_store,
            filename=filename,
            mime_type=content_type,
            backend=backend,
        )
        if hasattr(file, "seek"):
            await file.seek(0)
        return res

    return verify(
        file,
        policy=policy,
        trust_store=trust_store,
        filename=filename,
        mime_type=content_type,
        backend=backend,
    )
