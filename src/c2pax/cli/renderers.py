"""Визуализаторы вывода CLI на базе библиотеки Rich."""

from __future__ import annotations

import json
from typing import Any

from c2pax.core.models import AssetInfo
from c2pax.diff.semantic import SemanticDiff
from c2pax.verification.result import VerificationResult
from c2pax.verification.status import VerificationStatus

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree

    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False
    Console = None  # type: ignore[assignment, misc]


def get_console() -> Any:
    """Возвращает экземпляр Rich Console или None."""
    if _RICH_AVAILABLE:
        return Console(highlight=False)
    return None


def render_json(data: dict[str, Any] | list[Any]) -> None:
    """Выводит форматированный JSON в stdout."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def render_asset_info(info: AssetInfo, console: Any = None) -> None:
    """Рендерит декларативную информацию об ассете в красивом терминальном виде."""
    con = console or get_console()
    if not con or not _RICH_AVAILABLE:
        # Fallback без Rich
        print(f"=== Asset Info: {info.metadata.title or 'Unknown'} ===")
        print(f"C2PA Present: {info.has_c2pa}")
        print(f"Format: {info.metadata.format}")
        print(f"Signer: {info.identity.signer_name or 'None'}")
        print(f"AI Generated: {info.ai.generated}")
        return

    # Заголовок
    status_icon = "🟢" if info.has_c2pa else "⚪"
    header_text = f"{status_icon} [bold cyan]{info.metadata.title or 'Медиа-ассет'}[/bold cyan]"
    if info.metadata.format:
        header_text += f" [dim]({info.metadata.format})[/dim]"

    con.print(header_text)
    con.print()

    # 1. Панель метаданных и манифеста
    meta_table = Table(show_header=False, box=None, padding=(0, 2))
    meta_table.add_column("Key", style="bold yellow")
    meta_table.add_column("Value")

    meta_table.add_row(
        "Размер файла:", f"{info.metadata.file_size_bytes or 0:,} байт".replace(",", " ")
    )
    meta_table.add_row(
        "Манифест C2PA:",
        "[green]Присутствует[/green]" if info.has_c2pa else "[dim]Отсутствует[/dim]",
    )
    if info.manifest_status.claim_generator:
        meta_table.add_row("Генератор:", f"[blue]{info.manifest_status.claim_generator}[/blue]")
    if info.manifest_status.label:
        meta_table.add_row("ID Манифеста:", f"[dim]{info.manifest_status.label}[/dim]")

    con.print(Panel(meta_table, title="[bold]📦 Метаданные контейнера[/bold]", border_style="blue"))

    # 2. Панель Identity
    if info.identity.signer_name or info.identity.cert_issuer:
        id_table = Table(show_header=False, box=None, padding=(0, 2))
        id_table.add_column("Key", style="bold magenta")
        id_table.add_column("Value")

        id_table.add_row("Подписант:", f"[bold]{info.identity.signer_name or 'Не указан'}[/bold]")
        if info.identity.organization:
            id_table.add_row("Организация:", info.identity.organization)
        if info.identity.cert_issuer:
            id_table.add_row("Издатель CA:", info.identity.cert_issuer)
        if info.identity.cert_serial:
            id_table.add_row("Серийный №:", f"[dim]{info.identity.cert_serial}[/dim]")

        con.print(
            Panel(
                id_table,
                title="[bold]🪪 Задекларированный автор / Подписант[/bold]",
                border_style="magenta",
            )
        )

    # 3. Панель AI и Разрешений
    ai_table = Table(show_header=False, box=None, padding=(0, 2))
    ai_table.add_column("Key", style="bold green")
    ai_table.add_column("Value")

    ai_status = "Нет утверждений"
    if info.ai.generated is True:
        ai_status = "🤖 Полностью сгенерировано ИИ"
    elif info.ai.assisted is True:
        ai_status = "🎨 Создано при содействии ИИ"

    ai_table.add_row("Статус ИИ:", f"[bold]{ai_status}[/bold]")
    if info.ai.tools:
        ai_table.add_row("Инструменты ИИ:", ", ".join(info.ai.tools))
    if info.ai.prompts:
        ai_table.add_row("Промпт:", f'[italic]"{info.ai.prompts[0]}"[/italic]')

    mining_str = (
        "Разрешено"
        if info.permissions.data_mining_allowed is True
        else (
            "Запрещено (Do Not Train)"
            if info.permissions.data_mining_allowed is False
            else "Не заявлено"
        )
    )
    ai_table.add_row("Data Mining / Training:", mining_str)

    con.print(
        Panel(
            ai_table,
            title="[bold]🤖 ИИ и Политика использования данных[/bold]",
            border_style="green",
        )
    )

    # 4. Дерево происхождения Provenance DAG
    if info.provenance:
        root_node = info.provenance.root
        tree = Tree(
            f"[bold cyan]🌳 {root_node.title}[/bold cyan] [dim]({root_node.format or 'root'})[/dim]"
        )

        # Добавляем действия корневого узла
        for act in root_node.actions:
            soft_str = f" [blue]({act.software})[/blue]" if act.software else ""
            time_str = (
                f" [dim]({act.timestamp.strftime('%Y-%m-%d %H:%M')})[/dim]" if act.timestamp else ""
            )
            tree.add(f"⚡ [yellow]{act.name}[/yellow]{soft_str}{time_str}")

        # Добавляем ингредиенты
        for edge in info.provenance.edges():
            ing_node = info.provenance.get_node(edge.target_id)
            if ing_node:
                rel_badge = f"[magenta]<{edge.relationship}>[/magenta]"
                ing_branch = tree.add(
                    f"📎 {rel_badge} [bold]{ing_node.title}[/bold] [dim]({ing_node.format or 'unknown'})[/dim]"
                )
                for ing_act in ing_node.actions:
                    ing_branch.add(f"⚡ [dim yellow]{ing_act.name}[/dim yellow]")

        con.print(
            Panel(
                tree,
                title="[bold]🌿 Граф происхождения (Provenance DAG)[/bold]",
                border_style="cyan",
            )
        )


def render_verification_result(result: VerificationResult, console: Any = None) -> None:
    """Рендерит результат верификации C2PA."""
    con = console or get_console()
    if not con or not _RICH_AVAILABLE:
        print(result.explain())
        return

    status_styles = {
        VerificationStatus.VALID: ("✅ ДЕЙСТВИТЕЛЕН (VALID)", "green", "bold green"),
        VerificationStatus.INVALID: ("❌ НАРУШЕНА ЦЕЛОСТНОСТЬ (INVALID)", "red", "bold red"),
        VerificationStatus.UNTRUSTED: ("⚠️ НЕ ДОВЕРЕН (UNTRUSTED)", "yellow", "bold yellow"),
        VerificationStatus.NO_MANIFEST: ("ℹ️ МАНИФЕСТ C2PA ОТСУТСТВУЕТ", "dim", "dim"),
        VerificationStatus.UNSUPPORTED: ("🚫 НЕПОДДЕРЖИВАЕМЫЙ ФОРМАТ", "red", "bold red"),
        VerificationStatus.ERROR: ("🛑 ОШИБКА ВЕРИФИКАЦИИ", "red", "bold red"),
    }

    title, border_color, text_style = status_styles.get(
        result.status, (str(result.status), "white", "white")
    )

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")

    table.add_row("Статус:", f"[{text_style}]{title}[/{text_style}]")
    if result.signer:
        table.add_row("Подписант:", f"[cyan]{result.signer.signer_name}[/cyan]")
        if result.signer.cert_issuer:
            table.add_row("Издатель CA:", result.signer.cert_issuer)

    if result.timestamp:
        table.add_row("Метка времени:", result.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"))

    table.add_row(
        "Целостность хэшей:",
        "[green]✓ Совпадает[/green]"
        if result.integrity.content_hash_matches
        else "[red]✗ Поврежден[/red]",
    )
    table.add_row(
        "Цифровая подпись:",
        "[green]✓ Валидна[/green]"
        if result.integrity.signature_valid
        else "[red]✗ Недействительна[/red]",
    )
    table.add_row(
        "Доверие TrustStore:",
        "[green]✓ Доверен[/green]"
        if result.trust.signer_in_trust_store
        else "[yellow]✗ Не в TrustStore[/yellow]",
    )

    if result.errors:
        table.add_row("", "")
        for err in result.errors:
            table.add_row("❌ Ошибка:", f"[red]{err.message} [dim]({err.code})[/dim][/red]")

    if result.warnings:
        for warn in result.warnings:
            table.add_row(
                "⚠️ Предупреждение:", f"[yellow]{warn.message} [dim]({warn.code})[/dim][/yellow]"
            )

    con.print(
        Panel(
            table,
            title="[bold]🛡️ Криптографическая верификация C2PA[/bold]",
            border_style=border_color,
        )
    )


def render_semantic_diff(diff: SemanticDiff, console: Any = None) -> None:
    """Рендерит сравнительную таблицу различий ассетов."""
    con = console or get_console()
    if not con or not _RICH_AVAILABLE:
        print(diff.explain())
        return

    table = Table(title="🔍 Семантические различия между ассетами", border_style="cyan")
    table.add_column("Атрибут", style="bold")
    table.add_column("Статус / Значение", style="white")

    if diff.signer_changed:
        prev = diff.previous_signer.signer_name if diff.previous_signer else "Не подписан"
        curr = diff.current_signer.signer_name if diff.current_signer else "Не подписан"
        table.add_row("Подписант:", f"[yellow]{prev} ➔ [bold cyan]{curr}[/bold cyan][/yellow]")
    else:
        table.add_row("Подписант:", "[dim]Без изменений[/dim]")

    if diff.added_actions:
        actions_str = "\n".join(
            f"+ {a.name} ({a.software or 'unknown'})" for a in diff.added_actions
        )
        table.add_row(
            f"Новые действия ({len(diff.added_actions)}):", f"[green]{actions_str}[/green]"
        )
    else:
        table.add_row("Новые действия:", "[dim]Отсутствуют[/dim]")

    if diff.added_ingredients:
        ing_str = "\n".join(f"+ {i.title} [{i.format or 'raw'}]" for i in diff.added_ingredients)
        table.add_row(
            f"Новые ингредиенты ({len(diff.added_ingredients)}):", f"[blue]{ing_str}[/blue]"
        )
    else:
        table.add_row("Новые ингредиенты:", "[dim]Отсутствуют[/dim]")

    table.add_row(
        "ИИ-декларации:",
        "[yellow]Обнаружены изменения[/yellow]"
        if diff.ai_provenance_changed
        else "[dim]Без изменений[/dim]",
    )
    table.add_row(
        "Политика данных (Mining/AI):",
        "[yellow]Обнаружены изменения[/yellow]"
        if diff.permissions_changed
        else "[dim]Без изменений[/dim]",
    )

    if diff.metadata_diff:
        meta_str = "\n".join(f"{k}: {v1} ➔ {v2}" for k, (v1, v2) in diff.metadata_diff.items())
        table.add_row("Метаданные:", meta_str)

    con.print(table)
