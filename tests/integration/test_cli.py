"""Интеграционные тесты консольного интерфейса c2pax CLI."""

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from c2pax.backend import set_default_backend
from c2pax.backend.mock import MockC2paBackend
from c2pax.cli.exit_codes import EXIT_NO_MANIFEST, EXIT_UNTRUSTED, EXIT_VALID
from c2pax.cli.main import cli


@pytest.fixture(autouse=True)
def use_mock_backend_globally(mock_backend: MockC2paBackend) -> None:
    set_default_backend(mock_backend)


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "c2pax" in result.output


def test_cli_inspect_no_manifest(tmp_path: Path, sample_jpeg_bytes: bytes) -> None:
    img_file = tmp_path / "plain.jpg"
    img_file.write_bytes(sample_jpeg_bytes)

    runner = CliRunner()
    result = runner.invoke(cli, ["inspect", str(img_file)])
    assert result.exit_code == EXIT_NO_MANIFEST


def test_cli_inspect_json(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    sample_c2pa_manifest_data: dict[str, Any],
    mock_backend: MockC2paBackend,
) -> None:
    img_file = tmp_path / "signed.jpg"
    img_file.write_bytes(sample_jpeg_bytes)
    mock_backend.set_mock_manifest(str(img_file), sample_c2pa_manifest_data)

    runner = CliRunner()
    result = runner.invoke(cli, ["inspect", str(img_file), "--json"])
    assert result.exit_code == EXIT_VALID

    data = json.loads(result.output)
    assert data["has_c2pa"] is True
    assert data["metadata"]["title"] == "Sunset Landscape"


def test_cli_verify_with_policy(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    sample_c2pa_manifest_data: dict[str, Any],
    mock_backend: MockC2paBackend,
) -> None:
    img_file = tmp_path / "signed.jpg"
    img_file.write_bytes(sample_jpeg_bytes)
    mock_backend.set_mock_manifest(str(img_file), sample_c2pa_manifest_data)

    runner = CliRunner()
    # 1. Permissive -> VALID (0)
    res_perm = runner.invoke(cli, ["verify", str(img_file), "--policy", "permissive"])
    assert res_perm.exit_code == EXIT_VALID

    # 2. Standard без TrustStore -> UNTRUSTED (2)
    res_std = runner.invoke(cli, ["verify", str(img_file), "--policy", "standard"])
    assert res_std.exit_code == EXIT_UNTRUSTED


def test_cli_diff(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    sample_png_bytes: bytes,
) -> None:
    f1 = tmp_path / "f1.jpg"
    f2 = tmp_path / "f2.png"
    f1.write_bytes(sample_jpeg_bytes)
    f2.write_bytes(sample_png_bytes)

    runner = CliRunner()
    result = runner.invoke(cli, ["diff", str(f1), str(f2), "--json"])
    assert result.exit_code == EXIT_VALID
    data = json.loads(result.output)
    assert "added_actions" in data


def test_cli_sign(
    tmp_path: Path,
    sample_jpeg_bytes: bytes,
    ec_keypair: tuple[Any, Any, str, str],
) -> None:
    _, _, cert_pem, key_pem = ec_keypair

    cert_file = tmp_path / "cert.pem"
    key_file = tmp_path / "key.pem"
    in_file = tmp_path / "input.jpg"
    out_file = tmp_path / "signed.jpg"

    cert_file.write_text(cert_pem, encoding="utf-8")
    key_file.write_text(key_pem, encoding="utf-8")
    in_file.write_bytes(sample_jpeg_bytes)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "sign",
            str(in_file),
            str(out_file),
            "--cert",
            str(cert_file),
            "--key",
            str(key_file),
            "--title",
            "CLI Signed Photo",
        ],
    )
    assert result.exit_code == EXIT_VALID
    assert out_file.exists()
