"""Адаптер к официальному движку c2pa-python (c2pa-rs)."""

from __future__ import annotations

import json
from typing import Any, BinaryIO, cast

from c2pax.backend.base import BaseC2paBackend
from c2pax.core.exceptions import (
    CorruptedManifestError,
    SigningError,
    UnsupportedFormatError,
)
from c2pax.core.source import AssetSourceAdapter
from c2pax.verification.trust import TrustStore

try:
    import c2pa

    _C2PA_AVAILABLE = True
except ImportError:
    c2pa = None  # type: ignore[assignment]
    _C2PA_AVAILABLE = False


class C2paRsBackend(BaseC2paBackend):
    """Адаптер к официальной библиотеке c2pa-python."""

    def __init__(self) -> None:
        if not _C2PA_AVAILABLE:
            pass  # При реальном вызове проверяется доступность

    def _get_c2pa_module(self) -> Any:
        """Возвращает инициализированный модуль c2pa или вызывает исключение."""
        if not _C2PA_AVAILABLE or c2pa is None:
            raise RuntimeError(
                "Пакет 'c2pa-python' не установлен. Установите его с помощью 'pip install c2pa-python'."
            )
        return c2pa

    def read_manifest_raw(self, source: AssetSourceAdapter) -> dict[str, Any] | None:
        """Считывает сырой JSON манифеста с помощью c2pa.Reader."""
        c2pa_mod = self._get_c2pa_module()
        mime_type = source.get_mime_type()
        stream = source.get_stream()

        try:
            with c2pa_mod.Reader(mime_type, stream) as reader:
                raw_json = reader.json()
                if not raw_json:
                    return None
                data = json.loads(raw_json)
                if not isinstance(data, dict) or not data.get("manifests"):
                    return None
                return cast(dict[str, Any], data)
        except Exception as e:
            err_msg = str(e).lower()
            if "not found" in err_msg or "no jumbf" in err_msg or "manifest not found" in err_msg:
                return None
            if "unsupported" in err_msg or "format" in err_msg:
                raise UnsupportedFormatError(
                    f"Формат {mime_type} не поддерживается c2pa-rs: {e}"
                ) from e
            if "corrupted" in err_msg or "parse" in err_msg or "invalid" in err_msg:
                raise CorruptedManifestError(f"Манифест C2PA поврежден: {e}") from e
            # Если манифест просто отсутствует в файле
            return None

    def verify_raw(
        self,
        source: AssetSourceAdapter,
        trust_store: TrustStore | None = None,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """Выполняет низкоуровневую верификацию через c2pa-rs."""
        c2pa_mod = self._get_c2pa_module()
        mime_type = source.get_mime_type()
        stream = source.get_stream()

        try:
            # Настройка контекста и настроек TrustStore
            settings_dict: dict[str, Any] = {}
            if trust_store is not None:
                # Настройки верификации c2pa-rs
                settings_dict["verify"] = {
                    "verify_cert_anchors": True,
                }

            ctx = None
            if hasattr(c2pa_mod, "Context") and settings_dict:
                try:
                    settings = getattr(c2pa_mod, "Settings", None)
                    if settings and hasattr(settings, "from_dict"):
                        ctx = c2pa_mod.Context(settings.from_dict(settings_dict))
                    else:
                        ctx = c2pa_mod.Context()
                except Exception:
                    ctx = c2pa_mod.Context()
            elif hasattr(c2pa_mod, "Context"):
                ctx = c2pa_mod.Context()

            reader_kwargs: dict[str, Any] = {}
            if ctx is not None:
                reader_kwargs["context"] = ctx

            with c2pa_mod.Reader(mime_type, stream, **reader_kwargs) as reader:
                raw_json = reader.json()
                if not raw_json:
                    return None, []

                manifest_data = json.loads(raw_json)
                if not isinstance(manifest_data, dict):
                    return None, []
                validation_status = manifest_data.get("validation_status", [])
                return cast(dict[str, Any], manifest_data), cast(
                    list[dict[str, Any]], validation_status
                )
        except Exception as e:
            err_msg = str(e).lower()
            if "not found" in err_msg or "no jumbf" in err_msg:
                return None, []
            if "unsupported" in err_msg:
                raise UnsupportedFormatError(f"Формат {mime_type} не поддерживается: {e}") from e
            return None, [{"code": "general_error", "message": str(e)}]

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
        """Создает и подписывает C2PA манифест."""
        c2pa_mod = self._get_c2pa_module()

        cert_bytes = (
            signer_cert_pem.encode("utf-8") if isinstance(signer_cert_pem, str) else signer_cert_pem
        )
        key_bytes = (
            signer_private_key_pem.encode("utf-8")
            if isinstance(signer_private_key_pem, str)
            else signer_private_key_pem
        )

        alg_enum = alg.upper()
        if hasattr(c2pa_mod, "C2paSigningAlg"):
            alg_enum = getattr(c2pa_mod.C2paSigningAlg, alg.upper(), alg)

        signer_info_kwargs: dict[str, Any] = {
            "alg": alg_enum,
            "sign_cert": cert_bytes,
            "private_key": key_bytes,
        }
        if tsa_url:
            signer_info_kwargs["ta_url"] = (
                tsa_url.encode("utf-8") if isinstance(tsa_url, str) else tsa_url
            )

        try:
            signer_info = c2pa_mod.C2paSignerInfo(**signer_info_kwargs)
            manifest_json_str = json.dumps(manifest_definition)

            with c2pa_mod.Context() as ctx:
                with c2pa_mod.Signer.from_info(signer_info) as signer:
                    with c2pa_mod.Builder(manifest_json_str, ctx) as builder:
                        if ingredients:
                            for ing_def, ing_source in ingredients:
                                ing_json = json.dumps(ing_def)
                                ing_mime = ing_source.get_mime_type()
                                ing_stream = ing_source.get_stream()
                                builder.add_ingredient(ing_json, ing_mime, ing_stream)

                        src_stream = input_source.get_stream()
                        mime_type = input_source.get_mime_type()
                        manifest_bytes = builder.sign(
                            signer,
                            mime_type,
                            src_stream,
                            output_stream,
                        )
                        return cast(bytes, manifest_bytes)
        except Exception as e:
            raise SigningError(f"Ошибка при создании цифровой подписи C2PA: {e}") from e
