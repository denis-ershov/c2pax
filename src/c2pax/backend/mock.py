"""Mock-бэкенд для детерминированного и автономного тестирования c2pax."""

from __future__ import annotations

import copy
import json
from typing import Any, BinaryIO

from c2pax.backend.base import BaseC2paBackend
from c2pax.core.source import AssetSourceAdapter
from c2pax.verification.trust import TrustStore


class MockC2paBackend(BaseC2paBackend):
    """Изолированный тестовый бэкенд C2PA."""

    def __init__(self) -> None:
        self._mock_stores: dict[str, dict[str, Any]] = {}
        self._mock_validation_statuses: dict[str, list[dict[str, Any]]] = {}
        self._signed_history: list[dict[str, Any]] = []

    def set_mock_manifest(
        self,
        identifier: str,
        manifest_data: dict[str, Any],
        validation_status: list[dict[str, Any]] | None = None,
    ) -> None:
        """Регистрирует тестовый манифест для файла или байтов."""
        self._mock_stores[identifier] = manifest_data
        if validation_status is not None:
            self._mock_validation_statuses[identifier] = validation_status

    def _get_identifier(self, source: AssetSourceAdapter) -> str:
        if source.path:
            return str(source.path)
        explicit_fn = getattr(source, "_explicit_filename", None)
        if explicit_fn is not None:
            return explicit_fn
        return str(hash(source.get_bytes()[:256]))

    def read_manifest_raw(self, source: AssetSourceAdapter) -> dict[str, Any] | None:
        ident = self._get_identifier(source)
        if ident in self._mock_stores:
            return copy.deepcopy(self._mock_stores[ident])

        filename = source.path.name if source.path else getattr(source, "_explicit_filename", None)
        if filename and filename in self._mock_stores:
            return copy.deepcopy(self._mock_stores[filename])

        return None

    def verify_raw(
        self,
        source: AssetSourceAdapter,
        trust_store: TrustStore | None = None,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        ident = self._get_identifier(source)
        manifest_data = self.read_manifest_raw(source)
        if manifest_data is None:
            return None, []

        statuses = self._mock_validation_statuses.get(ident, [])
        filename = source.path.name if source.path else getattr(source, "_explicit_filename", None)
        if not statuses and filename and filename in self._mock_validation_statuses:
            statuses = self._mock_validation_statuses[filename]

        return manifest_data, copy.deepcopy(statuses)

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
        raw_input = input_source.get_bytes()
        # В тестовом режиме просто копируем исходный файл в выходной поток и формируем фиктивный заголовок
        output_stream.write(raw_input)

        manifest_label = manifest_definition.get("title", "mock_manifest")
        active_manifest = {
            "title": manifest_definition.get("title", "Mock Title"),
            "format": input_source.get_mime_type(),
            "claim_generator": "c2pax Mock Backend 0.1",
            "assertions": manifest_definition.get("assertions", []),
            "signature_info": {
                "alg": alg,
                "issuer": "Mock Signer CA",
                "time": "2026-08-17T12:00:00Z",
            },
        }

        mock_store = {
            "active_manifest": manifest_label,
            "manifests": {
                manifest_label: active_manifest,
            },
        }

        # Сохраняем в истории
        self._signed_history.append(
            {
                "manifest_definition": manifest_definition,
                "alg": alg,
                "tsa_url": tsa_url,
                "ingredients_count": len(ingredients) if ingredients else 0,
            }
        )

        return json.dumps(mock_store).encode("utf-8")
