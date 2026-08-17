"""Базовый абстрактный интерфейс для низкоуровневых C2PA движков."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, BinaryIO

from c2pax.core.source import AssetSourceAdapter
from c2pax.verification.trust import TrustStore


class BaseC2paBackend(ABC):
    """Абстрактный интерфейс к C2PA движку (c2pa-rs / c2pa-python / Mock)."""

    @abstractmethod
    def read_manifest_raw(self, source: AssetSourceAdapter) -> dict[str, Any] | None:
        """Считывает сырой JSON манифеста C2PA из ассета.

        Возвращает None, если манифест C2PA отсутствует.
        """
        ...

    @abstractmethod
    def verify_raw(
        self,
        source: AssetSourceAdapter,
        trust_store: TrustStore | None = None,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """Выполняет низкоуровневую верификацию.

        Возвращает кортеж (manifest_store_dict | None, validation_status_list).
        """
        ...

    @abstractmethod
    def sign_asset(
        self,
        input_source: AssetSourceAdapter,
        output_stream: BinaryIO,
        manifest_definition: dict[str, Any],
        signer_cert_pem: bytes | str,
        signer_private_key_pem: bytes | str,
        alg: str = "es256",
        tsa_url: str | None = None,
        ingredients: list[tuple[dict[str, Any], AssetSourceAdapter]] | None = None,
    ) -> bytes:
        """Создает и подписывает C2PA манифест, встраивая его в выходной поток."""
        ...
