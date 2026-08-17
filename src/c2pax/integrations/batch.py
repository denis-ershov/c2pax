"""Пакетная обработка и параллельная верификация файлов."""

from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from c2pax.api import verify
from c2pax.backend.base import BaseC2paBackend
from c2pax.core.source import AssetSource
from c2pax.verification.policy import VerificationPolicy
from c2pax.verification.result import VerificationResult
from c2pax.verification.trust import TrustStore


def verify_many(
    sources: Sequence[AssetSource],
    policy: VerificationPolicy | None = None,
    trust_store: TrustStore | None = None,
    max_workers: int = 4,
    backend: BaseC2paBackend | None = None,
) -> list[VerificationResult]:
    """Параллельно выполняет верификацию списка ассетов с использованием ThreadPoolExecutor."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                verify,
                src,
                policy=policy,
                trust_store=trust_store,
                backend=backend,
            )
            for src in sources
        ]
        return [f.result() for f in futures]


def verify_directory(
    dir_path: str | Path,
    recursive: bool = True,
    pattern: str = "*",
    policy: VerificationPolicy | None = None,
    trust_store: TrustStore | None = None,
    max_workers: int = 4,
    backend: BaseC2paBackend | None = None,
) -> dict[Path, VerificationResult]:
    """Сканирует каталог и верифицирует все найденные медиа-файлы."""
    p = Path(dir_path)
    if not p.exists() or not p.is_dir():
        raise NotADirectoryError(f"Каталог не найден: {dir_path}")

    files: list[Path] = []
    if recursive:
        files = [f for f in p.rglob(pattern) if f.is_file()]
    else:
        files = [f for f in p.glob(pattern) if f.is_file()]

    results_list = verify_many(
        files,
        policy=policy,
        trust_store=trust_store,
        max_workers=max_workers,
        backend=backend,
    )
    return dict(zip(files, results_list, strict=True))
