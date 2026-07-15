#!/usr/bin/env python3
"""Generate crawlable work pages and the XML sitemap from data/works.json."""

from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "works.json"
WORKS_DIR = ROOT / "works"
SITE_ORIGIN = "https://lilidoll.ru"
SOCIAL_IMAGE = f"{SITE_ORIGIN}/assets/images/social-preview.jpg"

STATUS_LABELS = {
    "exhibition": "На выставке",
    "private": "Частная коллекция",
    "archive": "Архив",
    "available": "Доступна",
}


def localized(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("ru") or value.get("en") or "")
    return str(value)


def escaped(value: object, *, quote: bool = True) -> str:
    return html.escape(localized(value), quote=quote)


def root_path(path: str) -> str:
    if path.startswith(("http://", "https://", "/")):
        return path
    return f"/{path}"


def work_url(work: dict) -> str:
    return f"{SITE_ORIGIN}/works/{work['slug']}/"


def related_works(work: dict, works: list[dict]) -> list[dict]:
    related = [
        item
        for item in works
        if item["slug"] != work["slug"]
        and (item["series"] == work["series"] or item["direction"] == work["direction"])
    ]
    related.sort(
        key=lambda item: (
            0 if item["series"] == work["series"] else 1,
            item.get("sortOrder", 0),
        )
    )
    return related[:3]


def render_gallery(work: dict) -> str:
    figures = []
    for index, source in enumerate(work.get("gallery", []), start=1):
        figures.append(
            f'''          <figure class="work-gallery__item image-shell">
            <img src="{escaped(root_path(source))}" alt="{escaped(work['title'])}, деталь {index}" loading="lazy" decoding="async" />
          </figure>'''
        )
    return "\n".join(figures)


def render_sources(work: dict) -> str:
    links = []
    for index, url in enumerate(work.get("sourcePosts", []), start=1):
        links.append(
            f'          <a href="{escaped(url)}" target="_blank" rel="noreferrer">Оригинальная публикация {index:02d} ↗</a>'
        )
    return "\n".join(links)


def render_related(work: dict, works: list[dict]) -> str:
    cards = []
    for item in related_works(work, works):
        cards.append(
            f'''          <article class="related-card">
            <a class="related-card__link" href="/works/{escaped(item['slug'])}/">
              <img src="{escaped(root_path(item['hero']))}" alt="{escaped(item['title'])} — авторская кукла Lili Miller" loading="lazy" decoding="async" />
              <div class="related-card__meta"><span>{escaped(item['seriesLabel'])}</span><span>{escaped(item['year'])}</span></div>
              <h3>{escaped(item['title'])}</h3>
            </a>
          </article>'''
        )
    return "\n".join(cards)


def work_schema(work: dict) -> str:
    url = work_url(work)
    image = f"{SITE_ORIGIN}{root_path(work['hero'])}"
    description = localized(work["excerpt"])
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": f"{localized(work['title'])} — авторская кукла Lili Miller",
                "description": description,
                "isPartOf": {"@id": f"{SITE_ORIGIN}/#website"},
                "breadcrumb": {"@id": f"{url}#breadcrumb"},
                "mainEntity": {"@id": f"{url}#artwork"},
                "primaryImageOfPage": image,
                "inLanguage": "ru",
            },
            {
                "@type": "VisualArtwork",
                "@id": f"{url}#artwork",
                "url": url,
                "name": localized(work["title"]),
                "description": description,
                "image": image,
                "creator": {"@id": f"{SITE_ORIGIN}/#artist"},
                "artform": localized(work["directionLabel"]),
                "artMedium": localized(work["material"]),
                "dateCreated": str(work.get("yearSort", "")),
                "isPartOf": {
                    "@type": "CollectionPage",
                    "name": "Каталог работ Lili Miller",
                    "url": f"{SITE_ORIGIN}/catalog.html",
                },
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{url}#breadcrumb",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Lili Miller",
                        "item": f"{SITE_ORIGIN}/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "Каталог",
                        "item": f"{SITE_ORIGIN}/catalog.html",
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": localized(work["title"]),
                        "item": url,
                    },
                ],
            },
        ],
    }
    return json.dumps(schema, ensure_ascii=False, indent=2)


def render_work_page(work: dict, works: list[dict]) -> str:
    title = f"{localized(work['title'])} — авторская кукла Lili Miller"
    description = f"{localized(work['excerpt'])} Авторская работа Lili Miller, {work['year']}."
    url = work_url(work)
    status = STATUS_LABELS.get(work.get("status"), localized(work.get("status")))
    dimensions = localized(work.get("dimensions")) or "Уточняется"
    edition = localized(work.get("edition")) or "Уточняется"
    gallery = work.get("gallery", [])

    return f'''<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="{escaped(description)}" data-description />
    <meta name="author" content="Lili Miller" />
    <meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1" />
    <meta name="theme-color" content="#f2eee7" />
    <link rel="canonical" href="{url}" />
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />

    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="Lili Miller" />
    <meta property="og:locale" content="ru_RU" />
    <meta property="og:url" content="{url}" />
    <meta property="og:title" content="{escaped(title)}" />
    <meta property="og:description" content="{escaped(description)}" />
    <meta property="og:image" content="{SOCIAL_IMAGE}" />
    <meta property="og:image:type" content="image/jpeg" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta property="og:image:alt" content="Оцую — авторская кукла Lili Miller в образе красной лилии" />

    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{escaped(title)}" />
    <meta name="twitter:description" content="{escaped(description)}" />
    <meta name="twitter:image" content="{SOCIAL_IMAGE}" />
    <meta name="twitter:image:alt" content="Оцую — авторская кукла Lili Miller в образе красной лилии" />

    <title>{escaped(title)}</title>
    <script type="application/ld+json" data-work-schema>
{work_schema(work)}
    </script>
    <link rel="stylesheet" href="/styles.css" />
    <script src="/work.js" defer></script>
  </head>
  <body class="inner-page work-view">
    <a class="skip-link" href="#main">Перейти к содержанию</a>

    <header class="site-header site-header--inner" data-header>
      <a class="brand" href="/#top" aria-label="Lili Miller, на главную">
        <span class="brand__mark" aria-hidden="true">LM</span>
        <span class="brand__name">Lili Miller</span>
      </a>
      <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="main-navigation" data-menu-toggle>
        <span></span><span></span><span class="sr-only">Открыть меню</span>
      </button>
      <nav class="main-nav" id="main-navigation" aria-label="Основная навигация" data-menu>
        <a href="/catalog.html" aria-current="page">Каталог</a>
        <a href="/#works">Избранное</a>
        <a href="/#artist">Художник</a>
        <a href="/#exhibitions">Выставки</a>
        <a href="/#contact">Контакты</a>
      </nav>
      <span class="language-label" aria-label="Язык страницы: русский">RU</span>
    </header>

    <main id="main" class="work-page" data-work-root data-work-slug="{escaped(work['slug'])}">
      <nav class="work-breadcrumbs" aria-label="Хлебные крошки">
        <a href="/">Lili Miller</a><span>/</span><a href="/catalog.html">Каталог</a><span>/</span><span>{escaped(work['title'])}</span>
      </nav>

      <section class="work-hero" aria-labelledby="work-title">
        <figure class="work-hero__figure image-shell">
          <img src="{escaped(root_path(work['hero']))}" alt="{escaped(work['title'])} — авторская кукла Lili Miller" decoding="async" fetchpriority="high" />
        </figure>
        <div class="work-hero__content">
          <div class="work-hero__top"><span class="work-status work-status--{escaped(work['status'])}">{escaped(status)}</span><span>{escaped(work['year'])}</span></div>
          <p class="eyebrow">{escaped(work['seriesLabel'])}</p>
          <h1 id="work-title">{escaped(work['title'])}</h1>
          <p class="work-hero__lead">{escaped(work['excerpt'])}</p>
          <dl class="work-facts">
            <div class="work-facts__item"><dt>Материал</dt><dd>{escaped(work['material']) or 'Уточняется'}</dd></div>
            <div class="work-facts__item"><dt>Год</dt><dd>{escaped(work['year'])}</dd></div>
            <div class="work-facts__item"><dt>Статус</dt><dd>{escaped(status)}</dd></div>
            <div class="work-facts__item"><dt>Тираж</dt><dd>{escaped(edition)}</dd></div>
            <div class="work-facts__item"><dt>Размер</dt><dd>{escaped(dimensions)}</dd></div>
          </dl>
          <a class="work-inquiry" href="https://t.me/lilimiller" target="_blank" rel="noreferrer">Уточнить о работе в Telegram ↗</a>
        </div>
      </section>

      <section class="work-story">
        <div class="work-story__index">История / 01</div>
        <div class="work-story__content">
          <p class="eyebrow">{escaped(work['directionLabel'])}</p>
          <h2>История персонажа</h2>
          <p class="work-story__text">{escaped(work['story'])}</p>
        </div>
      </section>

      <section class="work-gallery-section">
        <div class="work-section-heading">
          <p class="eyebrow">Галерея · {len(gallery)} кадров</p>
          <h2>Детали образа</h2>
        </div>
        <div class="work-gallery">
{render_gallery(work)}
        </div>
      </section>

      <section class="work-sources">
        <p class="eyebrow">Архив художника</p>
        <h2>Публикации о работе</h2>
        <div class="work-sources__links">
{render_sources(work)}
        </div>
      </section>

      <section class="related-works">
        <div class="work-section-heading work-section-heading--row">
          <p class="eyebrow">Продолжить знакомство</p><h2>Другие работы</h2>
        </div>
        <div class="related-grid">
{render_related(work, works)}
        </div>
      </section>
    </main>

    <footer class="inner-footer">
      <span>© 2026 Lili Miller</span>
      <a href="https://t.me/lilimillerdoll" target="_blank" rel="noreferrer">Telegram-канал</a>
      <a href="/catalog.html">Все работы ↑</a>
    </footer>
  </body>
</html>
'''


def render_sitemap(works: list[dict], last_modified: str) -> str:
    entries = [
        (
            f"{SITE_ORIGIN}/",
            f"{SITE_ORIGIN}/assets/images/telegram-web/lilimillerdoll/232.webp",
            "Оцую — авторская кукла Lili Miller",
        ),
        (
            f"{SITE_ORIGIN}/catalog.html",
            SOCIAL_IMAGE,
            "Каталог авторских кукол Lili Miller",
        ),
    ]
    entries.extend(
        (
            work_url(work),
            f"{SITE_ORIGIN}{root_path(work['hero'])}",
            f"{localized(work['title'])} — авторская кукла Lili Miller",
        )
        for work in works
    )

    urls = []
    for location, image_url, caption in entries:
        urls.append(
            f'''  <url>
    <loc>{html.escape(location)}</loc>
    <lastmod>{html.escape(last_modified)}</lastmod>
    <image:image>
      <image:loc>{html.escape(image_url)}</image:loc>
      <image:caption>{html.escape(caption)}</image:caption>
    </image:image>
  </url>'''
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    works = data.get("works", [])
    last_modified = data.get("generatedAt", "2026-07-15")
    WORKS_DIR.mkdir(exist_ok=True)

    expected_dirs = set()
    for work in works:
        target_dir = WORKS_DIR / work["slug"]
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "index.html").write_text(render_work_page(work, works), encoding="utf-8")
        expected_dirs.add(target_dir)

    for target_dir in WORKS_DIR.iterdir():
        if target_dir.is_dir() and target_dir not in expected_dirs:
            generated_file = target_dir / "index.html"
            if generated_file.exists():
                generated_file.unlink()
            try:
                target_dir.rmdir()
            except OSError:
                pass

    (ROOT / "sitemap.xml").write_text(render_sitemap(works, last_modified), encoding="utf-8")
    (ROOT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_ORIGIN}/sitemap.xml\n",
        encoding="utf-8",
    )
    print(f"Generated {len(works)} work pages, sitemap.xml and robots.txt")


if __name__ == "__main__":
    main()
