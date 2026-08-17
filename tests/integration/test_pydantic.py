"""Тесты интеграции с Pydantic v2."""

import pytest

from c2pax.core.models import (
    AIProvenance,
    AssetInfo,
    AssetMetadata,
    IdentityInfo,
    ManifestStatus,
    PermissionsInfo,
)
from c2pax.integrations.pydantic import _PYDANTIC_AVAILABLE, to_pydantic


@pytest.mark.skipif(not _PYDANTIC_AVAILABLE, reason="Pydantic v2 is not installed")
def test_to_pydantic_asset_info() -> None:
    info = AssetInfo(
        has_c2pa=True,
        metadata=AssetMetadata(title="Pydantic Test", format="image/jpeg", file_size_bytes=2048),
        identity=IdentityInfo(signer_name="Test Author"),
        ai=AIProvenance(generated=True, tools=["SDXL"]),
        permissions=PermissionsInfo(data_mining_allowed=False),
        manifest_status=ManifestStatus(present=True),
    )

    schema_obj = to_pydantic(info)
    assert schema_obj.has_c2pa is True
    assert schema_obj.metadata.title == "Pydantic Test"
    assert schema_obj.identity.signer_name == "Test Author"
    assert schema_obj.ai.generated is True
    assert schema_obj.permissions.data_mining_allowed is False

    # Проверка сериализации в JSON
    json_str = schema_obj.model_dump_json()
    assert "Pydantic Test" in json_str
