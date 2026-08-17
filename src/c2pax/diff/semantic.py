"""Движок семантического дифференцирования (c2pax.diff)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from c2pax.core.models import AssetInfo, IdentityInfo
from c2pax.core.provenance import Action, ProvenanceNode


@dataclass(slots=True)
class SemanticDiff:
    """Результат семантического сравнения двух цифровых ассетов C2PA."""

    added_actions: list[Action] = field(default_factory=list)
    added_ingredients: list[ProvenanceNode] = field(default_factory=list)
    signer_changed: bool = False
    previous_signer: IdentityInfo | None = None
    current_signer: IdentityInfo | None = None
    ai_provenance_changed: bool = False
    permissions_changed: bool = False
    metadata_diff: dict[str, tuple[Any, Any]] = field(default_factory=dict)

    def explain(self) -> str:
        """Формирует текстовую сводку семантических различий."""
        lines: list[str] = ["🔍 СЕМАНТИЧЕСКИЕ РАЗЛИЧИЯ АССЕТОВ:", "-" * 50]

        # 1. Изменение подписанта
        if self.signer_changed:
            prev_name = self.previous_signer.signer_name if self.previous_signer else "Не подписан"
            curr_name = self.current_signer.signer_name if self.current_signer else "Не подписан"
            lines.append(f"• Подписант изменён: {prev_name} ➔ {curr_name}")
        else:
            lines.append("• Подписант: Без изменений")

        # 2. Новые действия
        if self.added_actions:
            lines.append(f"• Добавлено новых действий ({len(self.added_actions)}):")
            for act in self.added_actions:
                soft = f" ({act.software})" if act.software else ""
                lines.append(f"    + {act.name}{soft}")
        else:
            lines.append("• Действия: Новых действий не обнаружено")

        # 3. Новые ингредиенты
        if self.added_ingredients:
            lines.append(f"• Добавлено новых ингредиентов ({len(self.added_ingredients)}):")
            for ing in self.added_ingredients:
                lines.append(f"    + {ing.title} [формат: {ing.format or 'не указан'}]")
        else:
            lines.append("• Ингредиенты: Без изменений")

        # 4. Изменения AI
        if self.ai_provenance_changed:
            lines.append("• ИИ-происхождение: Обнаружены изменения в декларациях ИИ")
        else:
            lines.append("• ИИ-происхождение: Без изменений")

        # 5. Разрешения
        if self.permissions_changed:
            lines.append("• Политика данных (Data Mining/AI Training): Изменена")
        else:
            lines.append("• Политика данных: Без изменений")

        # 6. Метаданные
        if self.metadata_diff:
            lines.append("• Изменения метаданных:")
            for k, (v1, v2) in self.metadata_diff.items():
                lines.append(f"    {k}: {v1} ➔ {v2}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_actions": [a.to_dict() for a in self.added_actions],
            "added_ingredients": [i.to_dict() for i in self.added_ingredients],
            "signer_changed": self.signer_changed,
            "previous_signer": self.previous_signer.to_dict() if self.previous_signer else None,
            "current_signer": self.current_signer.to_dict() if self.current_signer else None,
            "ai_provenance_changed": self.ai_provenance_changed,
            "permissions_changed": self.permissions_changed,
            "metadata_diff": {k: list(v) for k, v in self.metadata_diff.items()},
        }


def compute_semantic_diff(asset1: AssetInfo, asset2: AssetInfo) -> SemanticDiff:
    """Вычисляет семантические различия между двумя объектами AssetInfo."""
    diff = SemanticDiff()

    # 1. Сравнение действий (Actions)
    actions1 = asset1.provenance.actions if asset1.provenance else []
    actions2 = asset2.provenance.actions if asset2.provenance else []

    actions1_keys = {(a.name, a.software, a.timestamp) for a in actions1}
    for act in actions2:
        if (act.name, act.software, act.timestamp) not in actions1_keys:
            diff.added_actions.append(act)

    # 2. Сравнение ингредиентов
    nodes1_titles = {n.title: n for n in (asset1.provenance.nodes() if asset1.provenance else [])}
    if asset2.provenance:
        for node in asset2.provenance.nodes():
            if node.id != asset2.provenance.root_id and node.title not in nodes1_titles:
                diff.added_ingredients.append(node)

    # 3. Сравнение подписантов
    sig1 = asset1.identity
    sig2 = asset2.identity
    if (
        sig1.signer_name != sig2.signer_name
        or sig1.organization != sig2.organization
        or sig1.cert_serial != sig2.cert_serial
    ):
        diff.signer_changed = True
        diff.previous_signer = sig1
        diff.current_signer = sig2

    # 4. Сравнение AI Provenance
    ai1 = asset1.ai
    ai2 = asset2.ai
    if (
        ai1.generated != ai2.generated
        or ai1.assisted != ai2.assisted
        or set(ai1.tools) != set(ai2.tools)
        or len(ai1.prompts) != len(ai2.prompts)
    ):
        diff.ai_provenance_changed = True

    # 5. Сравнение Permissions
    perm1 = asset1.permissions
    perm2 = asset2.permissions
    if (
        perm1.data_mining_allowed != perm2.data_mining_allowed
        or perm1.ai_training_allowed != perm2.ai_training_allowed
    ):
        diff.permissions_changed = True

    # 6. Сравнение метаданных
    meta1 = asset1.metadata
    meta2 = asset2.metadata
    if meta1.title != meta2.title:
        diff.metadata_diff["title"] = (meta1.title, meta2.title)
    if meta1.format != meta2.format:
        diff.metadata_diff["format"] = (meta1.format, meta2.format)
    if meta1.file_size_bytes != meta2.file_size_bytes:
        diff.metadata_diff["file_size_bytes"] = (meta1.file_size_bytes, meta2.file_size_bytes)

    return diff
