"""Тесты универсального адаптера AssetSourceAdapter."""

import io
from pathlib import Path

import pytest

from c2pax.core.exceptions import AssetNotFoundError
from c2pax.core.source import AssetSourceAdapter, detect_mime_type_from_bytes


def test_detect_mime_type() -> None:
    assert detect_mime_type_from_bytes(b"\xff\xd8\xff\xe0") == "image/jpeg"
    assert detect_mime_type_from_bytes(b"\x89PNG\r\n\x1a\n") == "image/png"
    assert detect_mime_type_from_bytes(b"RIFF\x00\x00\x00\x00WEBP") == "image/webp"
    assert detect_mime_type_from_bytes(b"%PDF-1.4") == "application/pdf"
    assert detect_mime_type_from_bytes(b"\x00\x00\x00\x18ftypmp42") == "video/mp4"
    assert detect_mime_type_from_bytes(b"", filename="photo.jpg") == "image/jpeg"


def test_asset_source_bytes(sample_jpeg_bytes: bytes) -> None:
    with AssetSourceAdapter(sample_jpeg_bytes) as adapter:
        assert adapter.get_mime_type() == "image/jpeg"
        assert adapter.get_size() == len(sample_jpeg_bytes)
        assert adapter.get_bytes() == sample_jpeg_bytes

        stream = adapter.get_stream()
        assert stream.read(4) == sample_jpeg_bytes[:4]


def test_asset_source_file(tmp_path: Path, sample_png_bytes: bytes) -> None:
    file_path = tmp_path / "test.png"
    file_path.write_bytes(sample_png_bytes)

    with AssetSourceAdapter(file_path) as adapter:
        assert adapter.get_mime_type() == "image/png"
        assert adapter.get_size() == len(sample_png_bytes)
        assert adapter.get_bytes() == sample_png_bytes
        assert adapter.path == file_path


def test_asset_source_not_found(tmp_path: Path) -> None:
    non_existent = tmp_path / "missing.jpg"
    with pytest.raises(AssetNotFoundError):
        with AssetSourceAdapter(non_existent):
            pass


def test_asset_source_seekable_stream(sample_jpeg_bytes: bytes) -> None:
    bio = io.BytesIO(sample_jpeg_bytes)
    with AssetSourceAdapter(bio) as adapter:
        assert adapter.get_mime_type() == "image/jpeg"
        assert adapter.get_size() == len(sample_jpeg_bytes)
        assert adapter.get_bytes() == sample_jpeg_bytes
