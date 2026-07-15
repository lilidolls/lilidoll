#!/usr/bin/env python3
"""Create web-ready WebP copies of the local Telegram image archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "assets/images/telegram-originals"
SOURCE_MANIFEST = SOURCE_ROOT / "manifest.json"
OUTPUT_ROOT = PROJECT_ROOT / "assets/images/telegram-web"
OUTPUT_MANIFEST = PROJECT_ROOT / "data/telegram-media-manifest.json"
CONTENT_CATALOG = PROJECT_ROOT / "content/telegram-media-catalog.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-edge", type=int, default=2000, help="Maximum image side in pixels")
    parser.add_argument("--quality", type=int, default=82, help="WebP quality from 1 to 100")
    parser.add_argument("--workers", type=int, default=4, help="Parallel conversion workers")
    return parser.parse_args()


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def destination_for(source: Path) -> Path:
    relative = source.relative_to(SOURCE_ROOT)
    return (OUTPUT_ROOT / relative).with_suffix(".webp")


def optimize(source: Path, max_edge: int, quality: int) -> dict[str, Any]:
    destination = destination_for(source)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        source_width, source_height = image.size
        if max(image.size) > max_edge:
            image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS, reducing_gap=3.0)
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGB")
        image.save(destination, "WEBP", quality=quality, method=6, exact=True)
        width, height = image.size

    return {
        "source_path": source.relative_to(PROJECT_ROOT).as_posix(),
        "source_bytes": source.stat().st_size,
        "source_width": source_width,
        "source_height": source_height,
        "path": destination.relative_to(PROJECT_ROOT).as_posix(),
        "bytes": destination.stat().st_size,
        "width": width,
        "height": height,
        "sha256": digest(destination),
    }


class ProgressBar:
    def __init__(self, total: int, source_bytes: int, width: int = 34) -> None:
        self.total = total
        self.source_bytes = source_bytes
        self.width = width
        self.current = 0
        self.output_bytes = 0
        self.failed = 0
        self.is_tty = sys.stdout.isatty()
        self.render(force=True)

    def advance(self, result: dict[str, Any] | None) -> None:
        self.current += 1
        if result is None:
            self.failed += 1
        else:
            self.output_bytes += int(result["bytes"])
        self.render()

    def render(self, *, force: bool = False) -> None:
        if not self.is_tty and not force and self.current != self.total and self.current % 10:
            return
        ratio = self.current / self.total if self.total else 1
        filled = round(self.width * ratio)
        bar = "█" * filled + "░" * (self.width - filled)
        percent = round(ratio * 100)
        saved = 1 - self.output_bytes / self.source_bytes if self.source_bytes else 0
        line = (
            f"WebP [{bar}] {percent:3d}%  {self.current}/{self.total}  "
            f"результат: {self.output_bytes / 1024 / 1024:6.1f} МБ · "
            f"экономия: {saved * 100:4.0f}% · ошибок: {self.failed}"
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


def main() -> None:
    args = parse_args()
    if not SOURCE_MANIFEST.is_file():
        raise SystemExit(f"Source manifest is missing: {SOURCE_MANIFEST}")
    if args.max_edge < 320:
        raise SystemExit("--max-edge must be at least 320")
    if not 1 <= args.quality <= 100:
        raise SystemExit("--quality must be between 1 and 100")

    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    indexed = {item["path"]: item for item in source_manifest["images"]}
    sources = [PROJECT_ROOT / path for path in indexed]
    missing = [path for path in sources if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing source images: {len(missing)}")

    progress = ProgressBar(len(sources), sum(path.stat().st_size for path in sources))
    results: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(optimize, source, args.max_edge, args.quality): source
            for source in sources
        }
        for future in as_completed(futures):
            source = futures[future]
            try:
                result = future.result()
                results[source.relative_to(PROJECT_ROOT).as_posix()] = result
                progress.advance(result)
            except Exception as error:  # noqa: BLE001 - keep batch conversion running
                errors.append({"path": source.relative_to(PROJECT_ROOT).as_posix(), "error": str(error)})
                progress.advance(None)
    progress.finish()

    web_manifest = deepcopy(source_manifest)
    web_manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    web_manifest["profile"] = {
        "format": "webp",
        "quality": args.quality,
        "max_edge": args.max_edge,
        "metadata": "stripped",
    }
    web_manifest["source_archive"] = "Local only; excluded from Git"
    web_manifest["images"] = []
    for source_path, item in indexed.items():
        converted = results.get(source_path)
        if not converted:
            continue
        web_item = deepcopy(item)
        web_item["source_path"] = converted["source_path"]
        web_item["source_bytes"] = converted["source_bytes"]
        web_item["source_sha256"] = web_item.pop("sha256", None)
        web_item.update({key: value for key, value in converted.items() if not key.startswith("source_")})
        web_item["format"] = "webp"
        web_manifest["images"].append(web_item)
    web_manifest["count"] = len(web_manifest["images"])
    web_manifest["errors"] = errors
    web_manifest["source_bytes"] = sum(path.stat().st_size for path in sources)
    web_manifest["web_bytes"] = sum(item["bytes"] for item in results.values())

    OUTPUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MANIFEST.write_text(
        json.dumps(web_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if CONTENT_CATALOG.is_file():
        catalog = CONTENT_CATALOG.read_text(encoding="utf-8")
        for source_path, converted in results.items():
            catalog = catalog.replace(source_path, converted["path"])
        CONTENT_CATALOG.write_text(catalog, encoding="utf-8")

    if errors:
        raise SystemExit(f"Completed with {len(errors)} errors; see {OUTPUT_MANIFEST}")

    source_mb = web_manifest["source_bytes"] / 1024 / 1024
    web_mb = web_manifest["web_bytes"] / 1024 / 1024
    print(f"Готово: {web_manifest['count']} файлов · {source_mb:.1f} → {web_mb:.1f} МБ")
    print(OUTPUT_MANIFEST.relative_to(PROJECT_ROOT))
    if CONTENT_CATALOG.is_file():
        print(CONTENT_CATALOG.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
