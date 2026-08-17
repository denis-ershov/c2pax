"""Парсер сырых структур манифестов C2PA в доменные модели c2pax."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from c2pax.core.models import (
    AIProvenance,
    AssetInfo,
    AssetMetadata,
    IdentityInfo,
    ManifestStatus,
    PermissionsInfo,
)
from c2pax.core.provenance import (
    Action,
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    Relationship,
)
from c2pax.core.source import AssetSourceAdapter
from c2pax.verification.cert_utils import (
    extract_identity_from_cert,
    parse_pem_certificates,
)


def _parse_iso_datetime(val: Any) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            # Обработка Z и смещений
            clean_str = val.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_str)
        except Exception:
            return None
    return None


def parse_raw_manifest_to_asset_info(
    raw_store: dict[str, Any] | None,
    source: AssetSourceAdapter,
) -> AssetInfo:
    """Трансформирует сырой словарь манифест-стора в строго типизированный AssetInfo."""
    # Базовые метаданные ассета
    metadata = AssetMetadata(
        title=source.path.stem if source.path else "Asset",
        format=source.get_mime_type(),
        file_size_bytes=source.get_size(),
    )

    if not raw_store or not raw_store.get("manifests"):
        return AssetInfo(
            has_c2pa=False,
            metadata=metadata,
            identity=IdentityInfo(),
            provenance=None,
            ai=AIProvenance(),
            permissions=PermissionsInfo(),
            manifest_status=ManifestStatus(present=False),
            raw=raw_store or {},
        )

    active_id = raw_store.get("active_manifest")
    manifests: dict[str, Any] = raw_store.get("manifests", {})

    active_manifest: dict[str, Any] = manifests.get(active_id) if active_id else {}
    if not active_manifest and manifests:
        # Fallback к первому попавшемуся
        active_id = next(iter(manifests.keys()))
        active_manifest = manifests[active_id]

    # 1. Manifest Status
    claim_generator = active_manifest.get("claim_generator")
    format_version = active_manifest.get("format") or active_manifest.get("version")
    signature_info = active_manifest.get("signature_info", {})
    has_sig = bool(signature_info)

    manifest_status = ManifestStatus(
        present=True,
        format_version=str(format_version) if format_version else None,
        claim_generator=str(claim_generator) if claim_generator else None,
        has_signature=has_sig,
        label=active_id,
    )

    # 2. Metadata (уточнение по манифесту)
    if active_manifest.get("title"):
        metadata.title = active_manifest.get("title")
    if active_manifest.get("format"):
        metadata.format = active_manifest.get("format")

    # 3. Identity Info
    identity = IdentityInfo()
    if signature_info:
        cert_pem = signature_info.get("cert")
        if cert_pem:
            try:
                certs = parse_pem_certificates(cert_pem)
                if certs:
                    identity = extract_identity_from_cert(certs[0])
            except Exception:
                pass

        if not identity.signer_name and signature_info.get("issuer"):
            identity.signer_name = signature_info.get("issuer")
            identity.cert_issuer = signature_info.get("issuer")

        if not identity.cert_serial and signature_info.get("cert_serial_number"):
            identity.cert_serial = str(signature_info.get("cert_serial_number"))

    # 4. Actions & AI & Permissions
    actions_list: list[Action] = []
    ai_info = AIProvenance()
    permissions = PermissionsInfo()
    raw_assertions = active_manifest.get("assertions", [])

    for assertion in raw_assertions:
        label = assertion.get("label", "")
        data = assertion.get("data", {})

        # Actions assertion
        if "c2pa.actions" in label or label == "actions":
            raw_actions = data.get("actions", [])
            for act in raw_actions:
                act_name = act.get("action", "unknown")
                act_soft = act.get("softwareAgent")
                act_time = _parse_iso_datetime(act.get("when"))
                act_params = act.get("parameters", {})
                action_obj = Action(
                    name=act_name,
                    software=act_soft,
                    timestamp=act_time,
                    parameters=act_params,
                )
                actions_list.append(action_obj)

                # Проверка AI признаков в действиях
                name_and_soft = f"{act_name} {act_soft} {act_params!s}".lower()
                ai_keywords = (
                    "ai",
                    "generative",
                    "midjourney",
                    "dall-e",
                    "stable diffusion",
                    "firefly",
                    "chatgpt",
                    "generator",
                )
                if any(kw in name_and_soft for kw in ai_keywords):
                    if act_name in ("c2pa.created", "c2pa.placed"):
                        ai_info.generated = True
                    else:
                        ai_info.assisted = True
                    if act_soft and act_soft not in ai_info.tools:
                        ai_info.tools.append(act_soft)

        # AI assertions
        elif (
            "c2pa.ai_generative" in label
            or "c2pa.ai_assisted" in label
            or "c2pa.ai" in label
            or "firefly" in label
        ):
            if "generative" in label or data.get("prompt"):
                ai_info.generated = True
            elif "assisted" in label:
                ai_info.assisted = True

            tool_val = data.get("tool") or data.get("software")
            if tool_val and tool_val not in ai_info.tools:
                ai_info.tools.append(tool_val)

            model_val = data.get("model")
            if model_val:
                if isinstance(model_val, dict):
                    ai_info.models.append(model_val)
                else:
                    ai_info.models.append({"name": str(model_val)})

            prompt_val = data.get("prompt")
            if prompt_val and prompt_val not in ai_info.prompts:
                ai_info.prompts.append(str(prompt_val))

            ai_info.raw_assertions.append(assertion)

        # Permissions & Data mining assertion
        elif "c2pa.data_mining" in label or "training" in label:
            entries = data.get("entries", {})
            if "c2pa.data_mining" in entries:
                use_val = entries["c2pa.data_mining"].get("use", "")
                permissions.data_mining_allowed = use_val == "allowed"
            if "c2pa.ai_generative_training" in entries or "c2pa.ai_training" in entries:
                use_val = entries.get("c2pa.ai_generative_training", {}).get("use") or entries.get(
                    "c2pa.ai_training", {}
                ).get("use", "")
                permissions.ai_training_allowed = use_val == "allowed"

            permissions.raw_assertions.append(assertion)

    # 5. Provenance Graph DAG
    root_node_id = active_id or "root"
    root_node = ProvenanceNode(
        id=root_node_id,
        title=metadata.title or "Root Asset",
        format=metadata.format,
        hash=active_manifest.get("signature_info", {}).get("hash"),
        actions=actions_list,
    )

    provenance_graph = ProvenanceGraph(
        root_id=root_node_id,
        _nodes={root_node_id: root_node},
        _edges=[],
    )

    # Рекурсивный парсинг ингредиентов и связанных манифестов
    ingredients = active_manifest.get("ingredients", [])
    for idx, ing in enumerate(ingredients):
        ing_id = ing.get("instance_id") or ing.get("manifest_data") or f"ingredient_{idx}"
        ing_title = ing.get("title", f"Ingredient {idx + 1}")
        ing_format = ing.get("format")
        ing_rel_str = ing.get("relationship", "parentOf")
        try:
            ing_rel = Relationship(ing_rel_str)
        except ValueError:
            ing_rel = Relationship.PARENT_OF

        ing_node = ProvenanceNode(
            id=ing_id,
            title=ing_title,
            format=ing_format,
            hash=ing.get("hash"),
        )
        provenance_graph.add_node(ing_node)
        provenance_graph.add_edge(
            ProvenanceEdge(
                source_id=root_node_id,
                target_id=ing_id,
                relationship=ing_rel,
            )
        )

        # Если в манифест-сторе есть отдельный манифест для этого ингредиента
        if ing_id in manifests:
            sub_manifest = manifests[ing_id]
            for sub_assertion in sub_manifest.get("assertions", []):
                if "c2pa.actions" in sub_assertion.get("label", ""):
                    for sub_act in sub_assertion.get("data", {}).get("actions", []):
                        ing_node.actions.append(
                            Action(
                                name=sub_act.get("action", "unknown"),
                                software=sub_act.get("softwareAgent"),
                                timestamp=_parse_iso_datetime(sub_act.get("when")),
                                parameters=sub_act.get("parameters", {}),
                            )
                        )

    return AssetInfo(
        has_c2pa=True,
        metadata=metadata,
        identity=identity,
        provenance=provenance_graph,
        ai=ai_info,
        permissions=permissions,
        manifest_status=manifest_status,
        raw=raw_store,
    )
