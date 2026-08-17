"""Универсальный адаптер источников данных (AssetSource) для c2pax."""

from __future__ import annotations

import io
import mimetypes
import os
from pathlib import Path
from typing import BinaryIO, TypeAlias

from c2pax.core.exceptions import AssetNotFoundError

AssetSource: TypeAlias = str | Path | bytes | bytearray | memoryview | BinaryIO

# Магические сигнатуры для определения MIME-типов
_MAGIC_SIGNATURES: list[tuple[bytes, str, int]] = [
    (b"\xff\xd8\xff", "image/jpeg", 0),
    (b"\x89PNG\r\n\x1a\n", "image/png", 0),
    (b"GIF87a", "image/gif", 0),
    (b"GIF89a", "image/gif", 0),
    (b"RIFF", "image/webp", 0),  # Дополнительно проверяется WEBP на смещении 8
    (b"%PDF", "application/pdf", 0),
    (b"II*\x00", "image/tiff", 0),
    (b"MM\x00*", "image/tiff", 0),
    (b"ftypavif", "image/avif", 4),
    (b"ftypavis", "image/avif", 4),
    (b"ftypheic", "image/heic", 4),
    (b"ftypheix", "image/heic", 4),
    (b"ftypmif1", "image/heif", 4),
    (b"ftypisom", "video/mp4", 4),
    (b"ftypmp41", "video/mp4", 4),
    (b"ftypmp42", "video/mp4", 4),
    (b"ftypdash", "video/mp4", 4),
    (b"ftypqt  ", "video/quicktime", 4),
    (b"ID3", "audio/mpeg", 0),
    (b"\xff\xfb", "audio/mpeg", 0),
    (b"\xff\xf3", "audio/mpeg", 0),
    (b"\xff\xf2", "audio/mpeg", 0),
    (b"RIFF", "audio/wav", 0),  # Смещение 8 = WAVE
]

# Карта расширений в стандартные MIME-типы
_EXTENSION_MIME_MAP: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".avif": "image/avif",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".pdf": "application/pdf",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
}


def detect_mime_type_from_bytes(header: bytes, filename: str | None = None) -> str | None:
    """Определяет MIME-тип по начальным байтам файла или имени файла."""
    if len(header) >= 12:
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return "image/webp"
        if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
            return "audio/wav"

    for magic, mime, offset in _MAGIC_SIGNATURES:
        if len(header) >= offset + len(magic):
            if header[offset : offset + len(magic)] == magic:
                return mime

    if filename:
        ext = Path(filename).suffix.lower()
        if ext in _EXTENSION_MIME_MAP:
            return _EXTENSION_MIME_MAP[ext]
        guessed, _ = mimetypes.guess_type(filename)
        if guessed:
            return guessed

    return None


class AssetSourceAdapter:
    """Контекстный адаптер для безопасного чтения и буферизации источников данных."""

    def __init__(
        self,
        source: AssetSource,
        mime_type: str | None = None,
        filename: str | None = None,
    ) -> None:
        self._source = source
        self._explicit_mime = mime_type
        self._explicit_filename = filename
        self._stream: BinaryIO | None = None
        self._owns_stream: bool = False
        self._cached_bytes: bytes | None = None
        self._detected_mime: str | None = None
        self._file_size: int | None = None
        self._path: Path | None = None

    @property
    def path(self) -> Path | None:
        """Возвращает путь к файлу на диске, если источник является файлом."""
        if isinstance(self._source, (str, Path)):
            return Path(self._source)
        return self._path

    def __enter__(self) -> AssetSourceAdapter:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        self.close()

    def open(self) -> BinaryIO:
        """Открывает поток данных и подготавливает его к seekable-чтению."""
        if self._stream is not None and not self._stream.closed:
            return self._stream

        if isinstance(self._source, (str, Path)):
            path = Path(self._source)
            if not path.exists():
                raise AssetNotFoundError(f"Файл ассета не найден: {path}")
            if not path.is_file():
                raise AssetNotFoundError(f"Указанный путь не является файлом: {path}")
            self._path = path
            self._file_size = path.stat().st_size
            self._stream = open(path, "rb")
            self._owns_stream = True

        elif isinstance(self._source, (bytes, bytearray, memoryview)):
            raw_bytes = bytes(self._source)
            self._cached_bytes = raw_bytes
            self._file_size = len(raw_bytes)
            self._stream = io.BytesIO(raw_bytes)
            self._owns_stream = True

        elif hasattr(self._source, "read"):
            stream = self._source
            # Проверяем, является ли поток seekable
            if stream.seekable():
                stream.seek(0, os.SEEK_END)
                self._file_size = stream.tell()
                stream.seek(0)
                self._stream = stream
                self._owns_stream = False
            else:
                # Читаем не-seekable поток в буфер BytesIO
                content = stream.read()
                self._cached_bytes = content
                self._file_size = len(content)
                self._stream = io.BytesIO(content)
                self._owns_stream = True
        else:
            raise TypeError(f"Неподдерживаемый тип источника данных: {type(self._source)}")

        # Определение MIME-типа
        self._resolve_mime_type()
        return self._stream

    def _resolve_mime_type(self) -> None:
        """Определяет MIME-тип контента."""
        if self._explicit_mime:
            self._detected_mime = self._explicit_mime
            return

        filename = self._explicit_filename or (self.path.name if self.path else None)

        if self._stream is not None:
            current_pos = self._stream.tell()
            header = self._stream.read(64)
            self._stream.seek(current_pos)
            mime = detect_mime_type_from_bytes(header, filename=filename)
            if mime:
                self._detected_mime = mime
                return

        if filename:
            mime = detect_mime_type_from_bytes(b"", filename=filename)
            if mime:
                self._detected_mime = mime
                return

        # По умолчанию для медиа или fallback
        self._detected_mime = "application/octet-stream"

    def get_stream(self) -> BinaryIO:
        """Возвращает открытый seekable поток данных."""
        if self._stream is None or self._stream.closed:
            return self.open()
        self._stream.seek(0)
        return self._stream

    def get_bytes(self) -> bytes:
        """Возвращает полное байтовое содержимое ассета."""
        if self._cached_bytes is not None:
            return self._cached_bytes

        stream = self.get_stream()
        stream.seek(0)
        self._cached_bytes = stream.read()
        stream.seek(0)
        return self._cached_bytes

    def get_mime_type(self) -> str:
        """Возвращает MIME-тип ассета."""
        if self._detected_mime is None:
            self.open()
        return self._detected_mime or "application/octet-stream"

    def get_size(self) -> int:
        """Возвращает размер ассета в байтах."""
        if self._file_size is None:
            self.open()
        return self._file_size or 0

    def close(self) -> None:
        """Безопасно закрывает созданный поток и освобождает ресурсы."""
        if self._owns_stream and self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None
