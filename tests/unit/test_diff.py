"""Тесты движка семантического дифференцирования c2pax.diff."""

from datetime import datetime, timezone

from c2pax.core.models import (
    AIProvenance,
    AssetInfo,
    AssetMetadata,
    IdentityInfo,
    PermissionsInfo,
)
from c2pax.core.provenance import Action, ProvenanceGraph, ProvenanceNode
from c2pax.diff.semantic import compute_semantic_diff


def test_compute_semantic_diff_no_changes() -> None:
    asset = AssetInfo(
        has_c2pa=True,
        metadata=AssetMetadata(title="Same Title", format="image/jpeg"),
        identity=IdentityInfo(signer_name="Same Signer"),
    )
    diff = compute_semantic_diff(asset, asset)
    assert diff.signer_changed is False
    assert len(diff.added_actions) == 0
    assert len(diff.added_ingredients) == 0
    assert diff.ai_provenance_changed is False
    assert diff.permissions_changed is False
    assert len(diff.metadata_diff) == 0


def test_compute_semantic_diff_with_changes() -> None:
    dt1 = datetime(2026, 8, 17, 10, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 8, 17, 11, 0, tzinfo=timezone.utc)

    act1 = Action(name="c2pa.created", software="c2pax", timestamp=dt1)
    act2 = Action(name="c2pa.edited", software="Photoshop", timestamp=dt2)

    root1 = ProvenanceNode(id="root", title="Version 1", actions=[act1])
    graph1 = ProvenanceGraph(root_id="root", _nodes={"root": root1})

    root2 = ProvenanceNode(id="root", title="Version 2", actions=[act1, act2])
    ing_node = ProvenanceNode(id="ing_1", title="Watermark.png", format="image/png")
    graph2 = ProvenanceGraph(root_id="root", _nodes={"root": root2, "ing_1": ing_node})

    asset1 = AssetInfo(
        has_c2pa=True,
        metadata=AssetMetadata(title="Version 1", file_size_bytes=1000),
        identity=IdentityInfo(signer_name="Author A"),
        provenance=graph1,
        ai=AIProvenance(generated=False),
        permissions=PermissionsInfo(data_mining_allowed=True),
    )

    asset2 = AssetInfo(
        has_c2pa=True,
        metadata=AssetMetadata(title="Version 2", file_size_bytes=1500),
        identity=IdentityInfo(signer_name="Author B"),
        provenance=graph2,
        ai=AIProvenance(generated=True, tools=["Midjourney"]),
        permissions=PermissionsInfo(data_mining_allowed=False),
    )

    diff = compute_semantic_diff(asset1, asset2)
    assert diff.signer_changed is True
    assert diff.previous_signer is not None
    assert diff.previous_signer.signer_name == "Author A"
    assert diff.current_signer is not None
    assert diff.current_signer.signer_name == "Author B"

    assert len(diff.added_actions) == 1
    assert diff.added_actions[0].name == "c2pa.edited"

    assert len(diff.added_ingredients) == 1
    assert diff.added_ingredients[0].title == "Watermark.png"

    assert diff.ai_provenance_changed is True
    assert diff.permissions_changed is True
    assert "title" in diff.metadata_diff
    assert "file_size_bytes" in diff.metadata_diff
