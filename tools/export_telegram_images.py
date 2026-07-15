#!/usr/bin/env python3
"""Export full-resolution image media from the Lili Miller Telegram sources."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from telegram_mcp.runtime import ensure_connected, get_client, resolve_entity


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = PROJECT_ROOT / "assets/images/telegram-originals"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff"}
SOURCES = (
    {
        "name": "Douls for soul site",
        "chat_id": -5265896039,
        "slug": "douls-for-soul-site",
        "username": None,
    },
    {
        "name": "lilimillerdoll",
        "chat_id": -1001669754520,
        "slug": "lilimillerdoll",
        "username": "lilimillerdoll",
    },
)


@dataclass
class ExportedImage:
    source: str
    chat_id: int
    message_id: int
    post_id: int
    date: str
    grouped_id: int | None
    message_caption: str
    post_comment: str
    comment_source_message_id: int | None
    post_url: str | None
    kind: str
    original_name: str | None
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class PostContext:
    post_id: int
    comment: str
    comment_source_message_id: int | None
    post_url: str | None


class ProgressBar:
    def __init__(self, total: int, width: int = 36) -> None:
        self.total = total
        self.width = width
        self.current = 0
        self.cached = 0
        self.downloaded = 0
        self.failed = 0
        self.is_tty = sys.stdout.isatty()
        self.render(force=True)

    def advance(self, *, downloaded: bool = False, failed: bool = False) -> None:
        self.current += 1
        if failed:
            self.failed += 1
        elif downloaded:
            self.downloaded += 1
        else:
            self.cached += 1
        self.render()

    def render(self, *, force: bool = False) -> None:
        if not self.is_tty and not force and self.current != self.total and self.current % 10:
            return
        ratio = self.current / self.total if self.total else 1
        filled = round(self.width * ratio)
        bar = "█" * filled + "░" * (self.width - filled)
        percent = round(ratio * 100)
        line = (
            f"Экспорт [{bar}] {percent:3d}%  {self.current}/{self.total}  "
            f"новых: {self.downloaded} · в кэше: {self.cached} · ошибок: {self.failed}"
        )
        if self.is_tty:
            sys.stdout.write(f"\r\x1b[2K{line}")
            sys.stdout.flush()
        else:
            print(line, flush=True)

    def finish(self) -> None:
        self.render(force=True)
        if self.is_tty:
            print(flush=True)


def document_filename(message: Any) -> str | None:
    document = getattr(message, "document", None)
    if document is None:
        return None
    for attribute in getattr(document, "attributes", ()):
        name = getattr(attribute, "file_name", None)
        if name:
            return str(name)
    return None


def is_image_message(message: Any) -> tuple[bool, str, str | None]:
    if getattr(message, "photo", None) is not None:
        return True, "photo", None

    document = getattr(message, "document", None)
    if document is None:
        return False, "", None

    original_name = document_filename(message)
    mime_type = (getattr(document, "mime_type", None) or "").lower()
    suffix = Path(original_name or "").suffix.lower()
    if mime_type.startswith("image/") or suffix in IMAGE_EXTENSIONS:
        return True, "document", original_name
    return False, "", original_name


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def existing_download(directory: Path, message_id: int) -> Path | None:
    matches = sorted(directory.glob(f"{message_id}.*"))
    return matches[0] if matches else None


def build_post_contexts(
    source: dict[str, Any], image_messages: list[Any]
) -> dict[int, PostContext]:
    grouped_messages: dict[int | str, list[Any]] = defaultdict(list)
    for message in image_messages:
        key: int | str = getattr(message, "grouped_id", None) or f"message:{message.id}"
        grouped_messages[key].append(message)

    contexts: dict[int, PostContext] = {}
    for messages in grouped_messages.values():
        messages.sort(key=lambda item: item.id)
        comment_message = next(
            (item for item in messages if (getattr(item, "message", None) or "").strip()),
            None,
        )
        post_id = comment_message.id if comment_message else messages[0].id
        comment = (getattr(comment_message, "message", None) or "") if comment_message else ""
        username = source.get("username")
        post_url = f"https://t.me/{username}/{post_id}" if username else None
        context = PostContext(
            post_id=post_id,
            comment=comment,
            comment_source_message_id=comment_message.id if comment_message else None,
            post_url=post_url,
        )
        for message in messages:
            contexts[message.id] = context
    return contexts


async def download_one(
    client: Any,
    source: dict[str, Any],
    message: Any,
    context: PostContext,
    semaphore: asyncio.Semaphore,
) -> tuple[ExportedImage, bool]:
    is_image, kind, original_name = is_image_message(message)
    if not is_image:
        raise ValueError(f"Message {message.id} does not contain an image")

    directory = EXPORT_ROOT / source["slug"]
    directory.mkdir(parents=True, exist_ok=True)
    path = existing_download(directory, message.id)
    was_downloaded = path is None

    if path is None:
        requested_path = directory / str(message.id)
        async with semaphore:
            downloaded = await client.download_media(message, file=str(requested_path))
        if not downloaded:
            raise RuntimeError(f"Telegram returned no file for message {message.id}")
        path = Path(downloaded).resolve()

    date = getattr(message, "date", None)
    if date is None:
        date_text = ""
    else:
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        date_text = date.isoformat()

    return ExportedImage(
        source=source["name"],
        chat_id=source["chat_id"],
        message_id=message.id,
        post_id=context.post_id,
        date=date_text,
        grouped_id=getattr(message, "grouped_id", None),
        message_caption=getattr(message, "message", None) or "",
        post_comment=context.comment,
        comment_source_message_id=context.comment_source_message_id,
        post_url=context.post_url,
        kind=kind,
        original_name=original_name,
        path=str(path.relative_to(PROJECT_ROOT)),
        bytes=path.stat().st_size,
        sha256=sha256(path),
    ), was_downloaded


async def download_with_progress(
    client: Any,
    source: dict[str, Any],
    message: Any,
    context: PostContext,
    semaphore: asyncio.Semaphore,
    progress: ProgressBar,
) -> ExportedImage | Exception:
    try:
        exported, was_downloaded = await download_one(
            client, source, message, context, semaphore
        )
    except Exception as error:
        progress.advance(failed=True)
        return error
    progress.advance(downloaded=was_downloaded)
    return exported


def write_catalog(images: list[ExportedImage], generated_at: str) -> Path:
    catalog_path = PROJECT_ROOT / "content/telegram-media-catalog.md"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Каталог изображений из Telegram",
        "",
        f"Обновлено: `{generated_at}`",
        "",
        "Поле «Комментарий к посту» содержит подпись Telegram-поста. Для альбомов подпись привязана ко всем изображениям альбома.",
        "",
    ]

    for source in SOURCES:
        source_images = [item for item in images if item.chat_id == source["chat_id"]]
        lines.extend([f"## {source['name']}", "", f"Изображений: **{len(source_images)}**", ""])
        posts: dict[tuple[int | None, int], list[ExportedImage]] = defaultdict(list)
        for item in source_images:
            posts[(item.grouped_id, item.post_id)].append(item)

        ordered_posts = sorted(posts.values(), key=lambda items: (items[0].date, items[0].post_id))
        for post_images in ordered_posts:
            post_images.sort(key=lambda item: item.message_id)
            first = post_images[0]
            date = first.date[:10] if first.date else "без даты"
            title = f"### {date} · post {first.post_id}"
            if first.grouped_id:
                title += f" · album {first.grouped_id}"
            lines.extend([title, ""])
            if first.post_url:
                lines.extend([f"Источник: [{first.post_url}]({first.post_url})", ""])
            lines.append("Комментарий к посту:")
            if first.post_comment.strip():
                lines.extend(f"> {line}" for line in first.post_comment.splitlines())
            else:
                lines.append("> —")
            lines.extend(["", "Изображения:", ""])
            for item in post_images:
                original = f" · `{item.original_name}`" if item.original_name else ""
                lines.append(f"- `{item.path}` · message `{item.message_id}`{original}")
            lines.append("")

    catalog_path.write_text("\n".join(lines), encoding="utf-8")
    return catalog_path


async def main() -> None:
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    client = get_client()
    await ensure_connected(client)
    semaphore = asyncio.Semaphore(6)
    exported: list[ExportedImage] = []
    errors: list[dict[str, Any]] = []
    prepared_sources: list[tuple[dict[str, Any], list[Any], dict[int, PostContext]]] = []
    progress: ProgressBar | None = None

    try:
        for source in SOURCES:
            entity = await resolve_entity(source["chat_id"], client)
            image_messages = []
            async for message in client.iter_messages(entity, reverse=True):
                if is_image_message(message)[0]:
                    image_messages.append(message)
            contexts = build_post_contexts(source, image_messages)
            prepared_sources.append((source, image_messages, contexts))
            print(f"{source['name']} ({source['chat_id']}): {len(image_messages)} изображений", flush=True)

        total = sum(len(messages) for _, messages, _ in prepared_sources)
        progress = ProgressBar(total)
        for source, messages, contexts in prepared_sources:
            for start in range(0, len(messages), 24):
                batch = messages[start : start + 24]
                results = await asyncio.gather(
                    *(
                        download_with_progress(
                            client,
                            source,
                            message,
                            contexts[message.id],
                            semaphore,
                            progress,
                        )
                        for message in batch
                    )
                )
                for message, result in zip(batch, results):
                    if isinstance(result, Exception):
                        errors.append(
                            {
                                "source": source["name"],
                                "chat_id": source["chat_id"],
                                "message_id": message.id,
                                "error": str(result),
                            }
                        )
                    else:
                        exported.append(result)
    finally:
        if progress:
            progress.finish()
        await client.disconnect()

    exported.sort(key=lambda item: (item.chat_id, item.date, item.message_id))
    generated_at = datetime.now(timezone.utc).isoformat()
    unique_posts = {(item.chat_id, item.grouped_id or item.post_id) for item in exported}
    manifest = {
        "generated_at": generated_at,
        "count": len(exported),
        "post_count": len(unique_posts),
        "images_with_post_comment": sum(bool(item.post_comment.strip()) for item in exported),
        "post_comment_note": (
            "post_comment is the Telegram post caption. For albums, the same caption "
            "is attached to every image in the album."
        ),
        "sources": [dict(source) for source in SOURCES],
        "images": [asdict(item) for item in exported],
        "errors": errors,
    }
    manifest_path = EXPORT_ROOT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    catalog_path = write_catalog(exported, generated_at)
    print(f"Манифест: {manifest_path}", flush=True)
    print(f"Каталог с комментариями: {catalog_path}", flush=True)
    print(
        f"Готово: {len(exported)} изображений, {len(unique_posts)} постов, "
        f"{sum(bool(item.post_comment.strip()) for item in exported)} изображений с комментарием.",
        flush=True,
    )
    if errors:
        raise SystemExit(f"Не удалось выгрузить файлов: {len(errors)}")


if __name__ == "__main__":
    asyncio.run(main())
