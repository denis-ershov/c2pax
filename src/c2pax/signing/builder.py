"""Fluent Builder API для создания и подписания C2PA манифестов."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

from c2pax.backend import get_default_backend
from c2pax.backend.base import BaseC2paBackend
from c2pax.core.provenance import Relationship
from c2pax.core.source import AssetSource, AssetSourceAdapter
from c2pax.signing.signer import Signer


class Builder:
    """Построитель деклараций манифеста C2PA с удобным fluent-интерфейсом."""

    def __init__(self) -> None:
        self._title: str | None = None
        self._format: str | None = None
        self._claim_generator: str = "c2pax Python SDK 0.1.0"
        self._actions: list[dict[str, Any]] = []
        self._custom_assertions: list[dict[str, Any]] = []
        self._ingredients: list[tuple[dict[str, Any], AssetSource]] = []

    def set_title(self, title: str) -> Builder:
        """Устанавливает название создаваемого ассета."""
        self._title = title
        return self

    def set_format(self, mime_format: str) -> Builder:
        """Устанавливает MIME-тип выходного медиа-контейнера."""
        self._format = mime_format
        return self

    def set_claim_generator(self, generator: str) -> Builder:
        """Устанавливает идентификатор программного генератора."""
        self._claim_generator = generator
        return self

    def add_action(
        self,
        name: str,
        software: str | None = None,
        timestamp: datetime | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Builder:
        """Добавляет действие (c2pa.action) в историю манифеста."""
        time_val = timestamp or datetime.now(timezone.utc)
        action_dict: dict[str, Any] = {
            "action": name,
            "when": time_val.isoformat(),
        }
        if software:
            action_dict["softwareAgent"] = software
        if parameters:
            action_dict["parameters"] = parameters

        self._actions.append(action_dict)
        return self

    def add_ai_generation_assertion(
        self,
        tool: str,
        model_name: str | None = None,
        prompt: str | None = None,
    ) -> Builder:
        """Добавляет утверждение о генерации контента с помощью искусственного интеллекта."""
        data: dict[str, Any] = {"tool": tool}
        if model_name:
            data["model"] = model_name
        if prompt:
            data["prompt"] = prompt

        self._custom_assertions.append(
            {
                "label": "c2pa.ai_generative",
                "data": data,
            }
        )
        return self

    def add_ai_assisted_assertion(
        self,
        tool: str,
        model_name: str | None = None,
    ) -> Builder:
        """Добавляет утверждение об использовании ИИ при редактировании/содействии."""
        data: dict[str, Any] = {"tool": tool}
        if model_name:
            data["model"] = model_name

        self._custom_assertions.append(
            {
                "label": "c2pa.ai_assisted",
                "data": data,
            }
        )
        return self

    def add_ai_training_permission(
        self,
        data_mining_allowed: bool = True,
        ai_training_allowed: bool = True,
    ) -> Builder:
        """Настраивает политику сбора данных и обучения нейросетей (c2pa.data_mining)."""
        entries: dict[str, Any] = {
            "c2pa.data_mining": {
                "use": "allowed" if data_mining_allowed else "notAllowed",
            },
            "c2pa.ai_generative_training": {
                "use": "allowed" if ai_training_allowed else "notAllowed",
            },
        }
        self._custom_assertions.append(
            {
                "label": "c2pa.data_mining",
                "data": {"entries": entries},
            }
        )
        return self

    def add_assertion(self, label: str, data: dict[str, Any]) -> Builder:
        """Добавляет произвольное пользовательское утверждение (custom assertion)."""
        self._custom_assertions.append(
            {
                "label": label,
                "data": data,
            }
        )
        return self

    def add_ingredient(
        self,
        path_or_source: AssetSource,
        relationship: Relationship | str = Relationship.PARENT_OF,
        title: str | None = None,
    ) -> Builder:
        """Добавляет связанный исходный ассет или компонент (Ingredient)."""
        rel_str = relationship.value if isinstance(relationship, Relationship) else relationship
        ing_title = title
        if not ing_title and isinstance(path_or_source, (str, Path)):
            ing_title = Path(path_or_source).name
        elif not ing_title:
            ing_title = f"Ingredient {len(self._ingredients) + 1}"

        ing_def = {
            "title": ing_title,
            "relationship": rel_str,
        }
        self._ingredients.append((ing_def, path_or_source))
        return self

    def build_manifest_definition(self) -> dict[str, Any]:
        """Формирует полную структуру манифеста для передачи в backend."""
        assertions: list[dict[str, Any]] = []

        if self._actions:
            assertions.append(
                {
                    "label": "c2pa.actions",
                    "data": {"actions": self._actions},
                }
            )

        assertions.extend(self._custom_assertions)

        definition: dict[str, Any] = {
            "claim_generator": self._claim_generator,
            "title": self._title or "Untitled Asset",
            "assertions": assertions,
        }
        if self._format:
            definition["format"] = self._format

        return definition

    def sign(
        self,
        input_file: AssetSource,
        output_file: str | Path | BinaryIO,
        signer: Signer,
        backend: BaseC2paBackend | None = None,
    ) -> bytes:
        """Подписывает исходный медиа-файл и сохраняет результат."""
        active_backend = backend or get_default_backend()
        manifest_def = self.build_manifest_definition()

        with AssetSourceAdapter(input_file) as input_adapter:
            # Подготовка ингредиентов
            prepared_ingredients: list[tuple[dict[str, Any], AssetSourceAdapter]] = []
            for ing_def, ing_src in self._ingredients:
                ing_adapter = AssetSourceAdapter(ing_src)
                ing_adapter.open()
                prepared_ingredients.append((ing_def, ing_adapter))

            try:
                if isinstance(output_file, (str, Path)):
                    out_path = Path(output_file)
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(out_path, "wb") as out_stream:
                        return active_backend.sign_asset(
                            input_source=input_adapter,
                            output_stream=out_stream,
                            manifest_definition=manifest_def,
                            signer_cert_pem=signer.certificate_pem,
                            signer_private_key_pem=signer.private_key_pem,
                            alg=signer.alg,
                            tsa_url=signer.tsa_url,
                            ingredients=prepared_ingredients if prepared_ingredients else None,
                        )
                else:
                    return active_backend.sign_asset(
                        input_source=input_adapter,
                        output_stream=output_file,
                        manifest_definition=manifest_def,
                        signer_cert_pem=signer.certificate_pem,
                        signer_private_key_pem=signer.private_key_pem,
                        alg=signer.alg,
                        tsa_url=signer.tsa_url,
                        ingredients=prepared_ingredients if prepared_ingredients else None,
                    )
            finally:
                for _, ing_adapter in prepared_ingredients:
                    ing_adapter.close()


def sign(
    input_file: AssetSource,
    output_file: str | Path | BinaryIO,
    signer: Signer,
    title: str | None = None,
    creator: str | None = None,
    ai_tool: str | None = None,
    backend: BaseC2paBackend | None = None,
) -> bytes:
    """Функция быстрого наложения цифровой подписи C2PA на медиа-файл."""
    builder = Builder()
    if title:
        builder.set_title(title)
    if creator:
        builder.add_action("c2pa.created", software=creator)
    else:
        builder.add_action("c2pa.created")

    if ai_tool:
        builder.add_ai_generation_assertion(tool=ai_tool)

    return builder.sign(
        input_file=input_file,
        output_file=output_file,
        signer=signer,
        backend=backend,
    )
