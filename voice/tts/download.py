"""Shared streaming download helpers for local TTS backends."""
from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from pathlib import Path

import requests

from .errors import TTSError

logger = logging.getLogger("jarvis.tts.download")

ProgressCallback = Callable[[int, int | None, str], None]


def download_file(
    url: str,
    target: Path,
    *,
    max_bytes: int = 512 * 1024 * 1024,
    progress_callback: ProgressCallback | None = None,
    base_downloaded: int = 0,
    total_bytes_override: int | None = None,
    label: str = "",
) -> int:
    """Download an HTTPS asset into ``target`` atomically while reporting byte progress."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".part")
    temporary.unlink(missing_ok=True)
    written = 0
    file_label = label or target.name

    try:
        with requests.get(url, stream=True, timeout=(10, 60), allow_redirects=True) as response:
            final_url = str(getattr(response, "url", url))
            if not final_url.lower().startswith("https://"):
                raise TTSError("Загрузка модели остановлена: небезопасный URL.")
            response.raise_for_status()
            content_length = response.headers.get("Content-Length")
            parsed_length = int(content_length) if content_length and content_length.isdigit() else None
            total_bytes = total_bytes_override if total_bytes_override is not None else (
                (base_downloaded + parsed_length) if parsed_length is not None else None
            )

            if progress_callback is not None:
                progress_callback(base_downloaded, total_bytes, file_label)

            with temporary.open("wb") as output:
                for chunk in response.iter_content(chunk_size=512 * 1024):
                    if not chunk:
                        continue
                    written += len(chunk)
                    if written > max_bytes:
                        raise TTSError(f"Файл {file_label} превышает допустимый размер.")
                    output.write(chunk)
                    if progress_callback is not None:
                        progress_callback(base_downloaded + written, total_bytes, file_label)

        if written == 0:
            raise TTSError(f"Скачанный файл {file_label} пуст.")
        temporary.replace(target)
        return written
    except TTSError:
        temporary.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        raise TTSError(f"Не удалось скачать {file_label}: {exc}") from exc


def _resolve_hf_sizes(repo_id: str, rel_paths: Sequence[str]) -> dict[str, int]:
    """Query file sizes on Hugging Face Hub once so total download progress is accurate."""
    try:
        from huggingface_hub import HfApi

        wanted = set(rel_paths)
        sizes: dict[str, int] = {}
        for item in HfApi().list_repo_tree(repo_id=repo_id, recursive=True):
            path = getattr(item, "path", None)
            size = getattr(item, "size", None)
            if path in wanted and isinstance(size, int) and size > 0:
                sizes[path] = size
        return sizes
    except Exception:
        logger.debug("hf_size_lookup_skipped repo=%s", repo_id, exc_info=True)
        return {}


def download_hf_assets(
    repo_id: str,
    rel_paths: Sequence[str],
    target_dir: Path,
    *,
    max_file_bytes: int = 512 * 1024 * 1024,
    progress_callback: ProgressCallback | None = None,
) -> None:
    """Download required Hugging Face repository files into ``target_dir`` with aggregate progress."""
    sizes = _resolve_hf_sizes(repo_id, rel_paths)
    total_bytes = sum(sizes.get(rel, 0) for rel in rel_paths) or None

    downloaded = 0
    for rel in rel_paths:
        target = target_dir / rel
        if target.is_file() and target.stat().st_size >= 16:
            downloaded += target.stat().st_size
            if progress_callback is not None:
                progress_callback(downloaded, total_bytes, rel)
            continue

        url = f"https://huggingface.co/{repo_id}/resolve/main/{rel}?download=true"
        written = download_file(
            url,
            target,
            max_bytes=max_file_bytes,
            progress_callback=progress_callback,
            base_downloaded=downloaded,
            total_bytes_override=total_bytes,
            label=rel,
        )
        downloaded += written
