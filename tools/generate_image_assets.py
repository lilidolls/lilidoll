#!/usr/bin/env python3
"""Generate responsive image variants and per-work social preview cards."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
WORKS_PATH = ROOT / "data" / "works.json"
INDEX_PATH = ROOT / "index.html"
OUTPUT_MANIFEST = ROOT / "data" / "image-assets.json"
RESPONSIVE_ROOT = ROOT / "assets" / "images" / "responsive"
SOCIAL_ROOT = ROOT / "assets" / "images" / "social" / "works"
RESPONSIVE_WIDTHS = (480, 960, 1440)
SOCIAL_SIZE = (1200, 630)


def write_if_changed(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_bytes() == payload:
        return
    path.write_bytes(payload)


def responsive_path(source: str, width: int) -> Path:
    relative = Path(source).relative_to("assets/images/telegram-web")
    return RESPONSIVE_ROOT / relative.parent / f"{relative.stem}-{width}.webp"


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def webp_payload(image: Image.Image, quality: int = 78) -> bytes:
    output = io.BytesIO()
    image.save(output, "WEBP", quality=quality, method=6, exact=True)
    return output.getvalue()


def jpeg_payload(image: Image.Image, quality: int = 89) -> bytes:
    output = io.BytesIO()
    image.save(output, "JPEG", quality=quality, optimize=True, progressive=True, subsampling=1)
    return output.getvalue()


def load_rgb(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened)
        return image.convert("RGB")


def collect_sources(works: list[dict[str, Any]]) -> list[str]:
    sources: set[str] = set()
    for work in works:
        sources.add(work["hero"])
        sources.update(work.get("gallery", []))

    index = INDEX_PATH.read_text(encoding="utf-8")
    sources.update(
        match
        for match in re.findall(r'\bsrc="([^"]+)"', index)
        if match.startswith("assets/images/telegram-web/")
    )
    return sorted(sources)


def create_responsive_variants(source: str) -> dict[str, Any]:
    source_path = ROOT / source
    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    image = load_rgb(source_path)
    width, height = image.size
    variants: list[dict[str, Any]] = []

    for target_width in RESPONSIVE_WIDTHS:
        if target_width >= width:
            continue
        target_height = round(height * target_width / width)
        resized = image.resize((target_width, target_height), Image.Resampling.LANCZOS, reducing_gap=3.0)
        destination = responsive_path(source, target_width)
        payload = webp_payload(resized)
        write_if_changed(destination, payload)
        variants.append(
            {
                "path": relative(destination),
                "width": target_width,
                "height": target_height,
                "bytes": len(payload),
            }
        )

    variants.append(
        {
            "path": source,
            "width": width,
            "height": height,
            "bytes": source_path.stat().st_size,
        }
    )
    variants.sort(key=lambda item: item["width"])
    return {"width": width, "height": height, "variants": variants}


def create_social_preview(work: dict[str, Any]) -> dict[str, Any]:
    image = load_rgb(ROOT / work["hero"])

    background = ImageOps.fit(
        image,
        SOCIAL_SIZE,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.22),
    )
    background = background.filter(ImageFilter.GaussianBlur(28))
    background = ImageEnhance.Brightness(background).enhance(0.48).convert("RGBA")
    tint = Image.new("RGBA", SOCIAL_SIZE, (38, 23, 24, 72))
    canvas = Image.alpha_composite(background, tint)

    foreground = ImageOps.contain(image, (1080, 582), method=Image.Resampling.LANCZOS)
    foreground = ImageOps.expand(foreground, border=2, fill=(232, 225, 216)).convert("RGBA")
    x = (SOCIAL_SIZE[0] - foreground.width) // 2
    y = (SOCIAL_SIZE[1] - foreground.height) // 2

    shadow = Image.new("RGBA", SOCIAL_SIZE, (0, 0, 0, 0))
    shadow_box = Image.new("RGBA", foreground.size, (0, 0, 0, 150)).filter(ImageFilter.GaussianBlur(18))
    shadow.alpha_composite(shadow_box, (x + 8, y + 12))
    canvas = Image.alpha_composite(canvas, shadow)
    canvas.alpha_composite(foreground, (x, y))

    destination = SOCIAL_ROOT / f"{work['slug']}.jpg"
    payload = jpeg_payload(canvas.convert("RGB"))
    write_if_changed(destination, payload)
    return {
        "path": relative(destination),
        "width": SOCIAL_SIZE[0],
        "height": SOCIAL_SIZE[1],
        "bytes": len(payload),
    }


def remove_stale_files(root: Path, expected: set[Path]) -> None:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_file() and path not in expected:
            path.unlink()


def main() -> None:
    data = json.loads(WORKS_PATH.read_text(encoding="utf-8"))
    works = data.get("works", [])
    sources = collect_sources(works)

    images: dict[str, dict[str, Any]] = {}
    expected_responsive: set[Path] = set()
    for source in sources:
        images[source] = create_responsive_variants(source)
        expected_responsive.update(
            ROOT / item["path"]
            for item in images[source]["variants"]
            if item["path"].startswith("assets/images/responsive/")
        )

    social_previews: dict[str, dict[str, Any]] = {}
    expected_social: set[Path] = set()
    for work in works:
        social_previews[work["slug"]] = create_social_preview(work)
        expected_social.add(ROOT / social_previews[work["slug"]]["path"])

    remove_stale_files(RESPONSIVE_ROOT, expected_responsive)
    remove_stale_files(SOCIAL_ROOT, expected_social)

    manifest = {
        "generatedAt": data.get("generatedAt"),
        "profile": {
            "responsiveFormat": "webp",
            "responsiveQuality": 78,
            "responsiveWidths": list(RESPONSIVE_WIDTHS),
            "socialFormat": "jpeg",
            "socialQuality": 89,
            "socialSize": list(SOCIAL_SIZE),
        },
        "images": images,
        "socialPreviews": social_previews,
    }
    payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    write_if_changed(OUTPUT_MANIFEST, payload)

    responsive_count = sum(
        1
        for item in images.values()
        for variant in item["variants"]
        if variant["path"].startswith("assets/images/responsive/")
    )
    responsive_bytes = sum(path.stat().st_size for path in expected_responsive)
    social_bytes = sum(path.stat().st_size for path in expected_social)
    print(
        f"Generated {responsive_count} responsive variants for {len(images)} images "
        f"({responsive_bytes / 1024 / 1024:.1f} MB) and {len(social_previews)} social previews "
        f"({social_bytes / 1024 / 1024:.1f} MB)"
    )


if __name__ == "__main__":
    main()
