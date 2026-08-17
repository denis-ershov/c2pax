"""Главная точка входа для консольного интерфейса c2pax."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from c2pax import __version__
from c2pax import diff as c2pax_diff
from c2pax import inspect as c2pax_inspect
from c2pax import verify as c2pax_verify
from c2pax.cli.exit_codes import (
    EXIT_ERROR,
    EXIT_INVALID,
    EXIT_NO_MANIFEST,
    EXIT_UNTRUSTED,
    EXIT_VALID,
)
from c2pax.cli.renderers import (
    render_asset_info,
    render_json,
    render_semantic_diff,
    render_verification_result,
)
from c2pax.core.exceptions import C2PAError
from c2pax.signing.builder import sign as c2pax_sign
from c2pax.signing.signer import Signer
from c2pax.verification.policy import VerificationPolicy
from c2pax.verification.status import VerificationStatus
from c2pax.verification.trust import TrustStore


@click.group()
@click.version_option(version=__version__, prog_name="c2pax")
def cli() -> None:
    """c2pax — Python-native CLI для инспекции, верификации и подписи стандартом C2PA."""
    pass


@cli.command(name="inspect")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "json_output", is_flag=True, help="Машиночитаемый вывод в формате JSON.")
def inspect_cmd(file_path: Path, json_output: bool) -> None:
    """Инспекция медиа-ассета и извлечение декларативной информации C2PA."""
    try:
        info = c2pax_inspect(file_path)
        if json_output:
            render_json(info.to_dict())
        else:
            render_asset_info(info)
        sys.exit(EXIT_VALID if info.has_c2pa else EXIT_NO_MANIFEST)
    except Exception as e:
        click.echo(f"Ошибка при инспекции файла: {e}", err=True)
        sys.exit(EXIT_ERROR)


@cli.command(name="verify")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--policy",
    type=click.Choice(["strict", "standard", "permissive"], case_sensitive=False),
    default="standard",
    help="Политика верификации цифрового манифеста.",
)
@click.option(
    "--trust",
    "trust_path",
    type=click.Path(exists=True, path_type=Path),
    help="Путь к PEM-файлу или директории доверенных сертификатов (TrustStore).",
)
@click.option("--json", "json_output", is_flag=True, help="Вывод в формате JSON.")
def verify_cmd(file_path: Path, policy: str, trust_path: Path | None, json_output: bool) -> None:
    """Криптографическая верификация C2PA манифеста с проверкой целостности и доверия."""
    try:
        # Выбор политики
        if policy == "strict":
            ver_policy = VerificationPolicy.strict()
        elif policy == "permissive":
            ver_policy = VerificationPolicy.permissive()
        else:
            ver_policy = VerificationPolicy.standard()

        # Загрузка TrustStore
        trust_store = TrustStore()
        if trust_path:
            if trust_path.is_dir():
                trust_store = TrustStore.from_directory(trust_path)
            else:
                trust_store = TrustStore.from_pem(trust_path)

        result = c2pax_verify(file_path, policy=ver_policy, trust_store=trust_store)

        if json_output:
            render_json(result.to_dict())
        else:
            render_verification_result(result)

        # Стандартизированные коды завершения
        if result.status == VerificationStatus.VALID:
            sys.exit(EXIT_VALID)
        elif result.status == VerificationStatus.INVALID:
            sys.exit(EXIT_INVALID)
        elif result.status == VerificationStatus.UNTRUSTED:
            sys.exit(EXIT_UNTRUSTED)
        elif result.status == VerificationStatus.NO_MANIFEST:
            sys.exit(EXIT_NO_MANIFEST)
        else:
            sys.exit(EXIT_ERROR)

    except Exception as e:
        click.echo(f"Ошибка при верификации: {e}", err=True)
        sys.exit(EXIT_ERROR)


@cli.command(name="diff")
@click.argument("file1", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("file2", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "json_output", is_flag=True, help="Вывод различий в формате JSON.")
def diff_cmd(file1: Path, file2: Path, json_output: bool) -> None:
    """Семантическое сравнение истории изменений двух версий цифрового ассета."""
    try:
        diff_res = c2pax_diff(file1, file2)
        if json_output:
            render_json(diff_res.to_dict())
        else:
            render_semantic_diff(diff_res)
        sys.exit(EXIT_VALID)
    except Exception as e:
        click.echo(f"Ошибка при сравнении файлов: {e}", err=True)
        sys.exit(EXIT_ERROR)


@cli.command(name="sign")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_path", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--cert",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Путь к PEM-сертификату подписанта.",
)
@click.option(
    "--key",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Путь к закрытому ключу подписанта (PEM).",
)
@click.option("--title", help="Название цифрового ассета.")
@click.option("--creator", help="Имя или ПО создателя/подписанта.")
@click.option("--ai-tool", help="Инструмент генеративного ИИ (если контент сгенерирован).")
@click.option("--alg", default="es256", help="Криптографический алгоритм (es256, ps256, ed25519).")
@click.option("--tsa", help="URL службы штампов времени (RFC 3161 TSA).")
def sign_cmd(
    input_path: Path,
    output_path: Path,
    cert: Path,
    key: Path,
    title: str | None,
    creator: str | None,
    ai_tool: str | None,
    alg: str,
    tsa: str | None,
) -> None:
    """Создание и наложение цифровой подписи C2PA на медиа-файл."""
    try:
        signer = Signer.from_pem(certificate=cert, private_key=key, alg=alg, tsa_url=tsa)
        c2pax_sign(
            input_file=input_path,
            output_file=output_path,
            signer=signer,
            title=title,
            creator=creator,
            ai_tool=ai_tool,
        )
        click.echo(f"✅ Файл успешно подписан и сохранён в: {output_path}")
        sys.exit(EXIT_VALID)
    except C2PAError as e:
        click.echo(f"❌ Ошибка подписи C2PA: {e}", err=True)
        sys.exit(EXIT_ERROR)
    except Exception as e:
        click.echo(f"❌ Системная ошибка: {e}", err=True)
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    cli()
