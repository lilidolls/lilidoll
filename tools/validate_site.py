#!/usr/bin/env python3
"""Validate localized pages, links, structured data and generated image assets."""

from __future__ import annotations

import json
import re
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_LANGUAGES = {"ru", "en", "zh-Hans", "x-default"}


def image_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X":
            return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
        if chunk == b"VP8 ":
            marker = data.find(b"\x9d\x01\x2a", 20)
            if marker >= 0:
                width, height = struct.unpack_from("<HH", data, marker + 3)
                return width & 0x3FFF, height & 0x3FFF
        if chunk == b"VP8L" and data[20] == 0x2F:
            bits = int.from_bytes(data[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if data.startswith(b"\xff\xd8"):
        offset = 2
        while offset + 9 < len(data):
            if data[offset] != 0xFF:
                offset += 1
                continue
            marker = data[offset + 1]
            offset += 2
            if marker in {0xD8, 0xD9}:
                continue
            length = int.from_bytes(data[offset : offset + 2], "big")
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                height = int.from_bytes(data[offset + 3 : offset + 5], "big")
                width = int.from_bytes(data[offset + 5 : offset + 7], "big")
                return width, height
            offset += length
    raise ValueError(f"Unsupported image format: {path}")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.json_ld: list[str] = []
        self._in_script = False
        self._script_type = ""
        self._script_data: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        self.tags.append((tag, attributes))
        if tag == "script":
            self._in_script = True
            self._script_type = attributes.get("type", "")
            self._script_data = []

    def handle_endtag(self, tag: str) -> None:
        if tag != "script" or not self._in_script:
            return
        if self._script_type == "application/ld+json":
            self.json_ld.append("".join(self._script_data))
        self._in_script = False

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._script_data.append(data)


def page_list(works: list[dict]) -> list[Path]:
    slugs = [work["slug"] for work in works]
    pages = [ROOT / "index.html", ROOT / "catalog.html"]
    pages.extend(ROOT / "works" / slug / "index.html" for slug in slugs)
    for language in ("en", "zh"):
        pages.extend([ROOT / language / "index.html", ROOT / language / "catalog.html"])
        pages.extend(ROOT / language / "works" / slug / "index.html" for slug in slugs)
    return pages


def expected_html_language(page: Path) -> str:
    relative = page.relative_to(ROOT)
    if relative.parts[0] == "en":
        return "en"
    if relative.parts[0] == "zh":
        return "zh-Hans"
    return "ru"


def local_target(page: Path, value: str) -> Path | None:
    if not value or value.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:")):
        return None
    path = value.split("?", 1)[0].split("#", 1)[0]
    if not path:
        return None
    target = ROOT / path.lstrip("/") if path.startswith("/") else page.parent / path
    if path.endswith("/") or target.is_dir():
        target /= "index.html"
    return target


def validate_page(page: Path, image_assets: dict, errors: list[str]) -> None:
    if not page.is_file():
        errors.append(f"Missing page: {page.relative_to(ROOT)}")
        return
    source = page.read_text(encoding="utf-8")
    parser = PageParser()
    parser.feed(source)
    label = page.relative_to(ROOT)

    html_attrs = next((attrs for tag, attrs in parser.tags if tag == "html"), {})
    if html_attrs.get("lang") != expected_html_language(page):
        errors.append(f"{label}: incorrect html lang")

    canonical = [attrs.get("href") for tag, attrs in parser.tags if tag == "link" and attrs.get("rel") == "canonical"]
    if len(canonical) != 1:
        errors.append(f"{label}: expected one canonical URL")

    alternates = {
        attrs.get("hreflang")
        for tag, attrs in parser.tags
        if tag == "link" and attrs.get("rel") == "alternate" and attrs.get("hreflang")
    }
    if alternates != EXPECTED_LANGUAGES:
        errors.append(f"{label}: incomplete hreflang set {sorted(alternates)}")

    for payload in parser.json_ld:
        try:
            json.loads(payload)
        except json.JSONDecodeError as error:
            errors.append(f"{label}: invalid JSON-LD: {error}")

    if source.count("ym(110756646, 'init'") != 1:
        errors.append(f"{label}: expected one Metrika initialization")

    for tag, attrs in parser.tags:
        attribute = "src" if tag in {"img", "script", "source"} else "href" if tag in {"a", "link"} else None
        if attribute:
            target = local_target(page, attrs.get(attribute, ""))
            if target and not target.exists():
                errors.append(f"{label}: missing local target {attrs.get(attribute)}")

        if tag != "img":
            continue
        src = attrs.get("src", "").lstrip("/")
        if src not in image_assets.get("images", {}):
            continue
        if not attrs.get("srcset") or not attrs.get("sizes"):
            errors.append(f"{label}: responsive attributes missing for {src}")
        for candidate in attrs.get("srcset", "").split(","):
            candidate_path = candidate.strip().split(" ", 1)[0]
            target = local_target(page, candidate_path)
            if target and not target.is_file():
                errors.append(f"{label}: missing srcset candidate {candidate_path}")

    relative = page.relative_to(ROOT)
    if "works" in relative.parts:
        slug = relative.parts[-2]
        preview = image_assets.get("socialPreviews", {}).get(slug, {}).get("path")
        expected_preview = f"https://lilidoll.ru/{preview}" if preview else ""
        og_image = next(
            (attrs.get("content") for tag, attrs in parser.tags if tag == "meta" and attrs.get("property") == "og:image"),
            None,
        )
        if og_image != expected_preview:
            errors.append(f"{label}: incorrect work social preview")
        if source.count('data-ym-goal="inquiry_start"') < 2 or "t.me/lilimiller?text=" not in source:
            errors.append(f"{label}: contextual inquiry path is incomplete")


def validate_media(image_assets: dict, errors: list[str]) -> None:
    for source, metadata in image_assets.get("images", {}).items():
        source_path = ROOT / source
        if not source_path.is_file():
            errors.append(f"Missing image source: {source}")
            continue
        if image_dimensions(source_path) != (metadata["width"], metadata["height"]):
            errors.append(f"{source}: source dimensions differ from manifest")
        widths: set[int] = set()
        for variant in metadata.get("variants", []):
            variant_path = ROOT / variant["path"]
            if not variant_path.is_file():
                errors.append(f"Missing image variant: {variant['path']}")
                continue
            if variant["width"] in widths:
                errors.append(f"{source}: duplicate srcset width {variant['width']}")
            widths.add(variant["width"])
            if image_dimensions(variant_path) != (variant["width"], variant["height"]):
                errors.append(f"{variant['path']}: dimensions differ from manifest")

    for slug, preview in image_assets.get("socialPreviews", {}).items():
        preview_path = ROOT / preview["path"]
        if not preview_path.is_file():
            errors.append(f"Missing social preview: {slug}")
            continue
        if image_dimensions(preview_path) != (1200, 630):
            errors.append(f"{slug}: social preview must be 1200x630")


def validate_sitemap(errors: list[str]) -> None:
    namespaces = {
        "s": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "x": "http://www.w3.org/1999/xhtml",
    }
    urls = ET.parse(ROOT / "sitemap.xml").findall("s:url", namespaces)
    if len(urls) != 42:
        errors.append(f"sitemap.xml: expected 42 URLs, got {len(urls)}")
    for url in urls:
        languages = {link.attrib.get("hreflang") for link in url.findall("x:link", namespaces)}
        if languages != EXPECTED_LANGUAGES:
            errors.append("sitemap.xml: incomplete alternate language set")


def main() -> None:
    works = json.loads((ROOT / "data" / "works.json").read_text(encoding="utf-8"))["works"]
    image_assets = json.loads((ROOT / "data" / "image-assets.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    pages = page_list(works)

    for page in pages:
        validate_page(page, image_assets, errors)

    for folder in (ROOT / "en", ROOT / "zh"):
        for page in folder.rglob("*.html"):
            if re.search(r"[А-Яа-яЁё]", page.read_text(encoding="utf-8")):
                errors.append(f"{page.relative_to(ROOT)}: contains Cyrillic text")

    validate_media(image_assets, errors)
    validate_sitemap(errors)

    work_script = (ROOT / "work.js").read_text(encoding="utf-8")
    if "if (root && !root.dataset.workSlug) loadWork();" not in work_script:
        errors.append("work.js: static work pages are not protected from repeat rendering")

    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print(
        f"Validated {len(pages)} localized pages, {len(image_assets['images'])} responsive images, "
        f"{len(image_assets['socialPreviews'])} social previews and 42 sitemap URLs"
    )


if __name__ == "__main__":
    main()
