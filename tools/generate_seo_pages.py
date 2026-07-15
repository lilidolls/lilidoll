#!/usr/bin/env python3
"""Generate localized pages, crawlable work pages and the XML sitemap."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "works.json"
I18N_PATH = ROOT / "data" / "i18n.json"
SITE_ORIGIN = "https://lilidoll.ru"
SOCIAL_IMAGE = f"{SITE_ORIGIN}/assets/images/social-preview.jpg"
METRIKA_HEAD = '''    <!-- Yandex.Metrika counter -->
    <script type="text/javascript">
      window.dataLayer = window.dataLayer || [];
      (function(m,e,t,r,i,k,a){
          m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
          m[i].l=1*new Date();
          for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
          k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)
      })(window, document,'script','https://mc.yandex.ru/metrika/tag.js?id=110756646', 'ym');

      ym(110756646, 'init', {ssr:true, webvisor:true, clickmap:true, ecommerce:"dataLayer", referrer: document.referrer, url: location.href, accurateTrackBounce:true, trackLinks:true});
    </script>
    <!-- /Yandex.Metrika counter -->'''


def localized(value: object, language: str) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get(language) or value.get("en") or value.get("ru") or "")
    return str(value)


def escaped(value: object, language: str | None = None) -> str:
    text = localized(value, language) if language else str(value)
    return html.escape(text, quote=True)


def root_path(path: str) -> str:
    if path.startswith(("http://", "https://", "/")):
        return path
    return f"/{path}"


def language_prefix(language: str, i18n: dict) -> str:
    return i18n["languages"][language]["prefix"]


def page_path(language: str, page: str, i18n: dict, slug: str | None = None) -> str:
    prefix = language_prefix(language, i18n)
    if page == "home":
        return f"{prefix}/" or "/"
    if page == "catalog":
        return f"{prefix}/catalog.html"
    if page == "work" and slug:
        return f"{prefix}/works/{slug}/"
    raise ValueError(f"Unsupported page: {page}")


def page_url(language: str, page: str, i18n: dict, slug: str | None = None) -> str:
    return f"{SITE_ORIGIN}{page_path(language, page, i18n, slug)}"


def translate(i18n: dict, language: str, section: str, key: str) -> object:
    section_data = i18n[language].get(section, {})
    if key in section_data:
        return section_data[key]
    common = i18n[language].get("common", {})
    if key in common:
        return common[key]
    raise KeyError(f"Missing translation: {language}.{section}.{key}")


def format_text(template: str, **values: object) -> str:
    for key, value in values.items():
        template = template.replace(f"{{{key}}}", str(value))
    return template


def alternate_links(page: str, i18n: dict, slug: str | None = None, indent: str = "    ") -> str:
    links = []
    for language, config in i18n["languages"].items():
        links.append(
            f'{indent}<link rel="alternate" hreflang="{config["hreflang"]}" href="{page_url(language, page, i18n, slug)}" />'
        )
    links.append(
        f'{indent}<link rel="alternate" hreflang="x-default" href="{page_url("ru", page, i18n, slug)}" />'
    )
    return "\n".join(links)


def language_switch(language: str, page: str, i18n: dict, slug: str | None = None) -> str:
    common = i18n[language]["common"]
    items = []
    for code, config in i18n["languages"].items():
        current = ' aria-current="page"' if code == language else ""
        items.append(
            f'<a href="{page_path(code, page, i18n, slug)}" lang="{config["htmlLang"]}"{current}>{config["short"]}</a>'
        )
    return (
        f'<nav class="language-toggle" aria-label="{escaped(common["languageNav"])}">'
        + "<span>/</span>".join(items)
        + "</nav>"
    )


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


def home_schema(language: str, i18n: dict) -> dict:
    seo = i18n[language]["seo"]
    home = i18n[language]["home"]
    config = i18n["languages"][language]
    url = page_url(language, "home", i18n)
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": f"{SITE_ORIGIN}/#website",
                "url": f"{SITE_ORIGIN}/",
                "name": "Lili Miller",
                "alternateName": "Lili Miller Dolls",
                "inLanguage": [item["htmlLang"] for item in i18n["languages"].values()],
                "publisher": {"@id": f"{SITE_ORIGIN}/#artist"},
            },
            {
                "@type": "Person",
                "@id": f"{SITE_ORIGIN}/#artist",
                "name": "Lili Miller",
                "url": f"{SITE_ORIGIN}/#artist",
                "jobTitle": seo["artistJobTitle"],
                "description": seo["artistDescription"],
                "homeLocation": {"@type": "City", "name": seo["city"]},
                "knowsAbout": seo["knowsAbout"],
                "sameAs": ["https://t.me/lilimillerdoll"],
            },
            {
                "@type": "WebPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": seo["homeTitle"],
                "description": seo["homeDescription"],
                "isPartOf": {"@id": f"{SITE_ORIGIN}/#website"},
                "about": {"@id": f"{SITE_ORIGIN}/#artist"},
                "primaryImageOfPage": {
                    "@type": "ImageObject",
                    "url": f"{SITE_ORIGIN}/assets/images/telegram-web/lilimillerdoll/232.webp",
                    "contentUrl": f"{SITE_ORIGIN}/assets/images/telegram-web/lilimillerdoll/232.webp",
                    "caption": home["heroImageAlt"],
                },
                "inLanguage": config["htmlLang"],
            },
        ],
    }


def catalog_schema(language: str, works: list[dict], i18n: dict) -> dict:
    seo = i18n[language]["seo"]
    work_ui = i18n[language]["work"]
    config = i18n["languages"][language]
    url = page_url(language, "catalog", i18n)
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": seo["catalogTitle"],
                "description": seo["catalogDescription"],
                "isPartOf": {"@id": f"{SITE_ORIGIN}/#website"},
                "breadcrumb": {"@id": f"{url}#breadcrumb"},
                "mainEntity": {"@id": f"{url}#works"},
                "inLanguage": config["htmlLang"],
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{url}#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Lili Miller", "item": page_url(language, "home", i18n)},
                    {"@type": "ListItem", "position": 2, "name": work_ui["catalog"], "item": url},
                ],
            },
            {
                "@type": "ItemList",
                "@id": f"{url}#works",
                "name": seo["catalogTitle"],
                "numberOfItems": len(works),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index,
                        "name": localized(work["title"], language),
                        "url": page_url(language, "work", i18n, work["slug"]),
                    }
                    for index, work in enumerate(works, start=1)
                ],
            },
        ],
    }


def work_schema(work: dict, language: str, i18n: dict) -> dict:
    ui = i18n[language]["work"]
    config = i18n["languages"][language]
    url = page_url(language, "work", i18n, work["slug"])
    image = f"{SITE_ORIGIN}{root_path(work['hero'])}"
    title = localized(work["title"], language)
    description = localized(work["excerpt"], language)
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": f"{title} {ui['titleSuffix']}",
                "description": description,
                "isPartOf": {"@id": f"{SITE_ORIGIN}/#website"},
                "breadcrumb": {"@id": f"{url}#breadcrumb"},
                "mainEntity": {"@id": f"{url}#artwork"},
                "primaryImageOfPage": image,
                "inLanguage": config["htmlLang"],
            },
            {
                "@type": "VisualArtwork",
                "@id": f"{url}#artwork",
                "url": url,
                "name": title,
                "description": description,
                "image": image,
                "creator": {"@id": f"{SITE_ORIGIN}/#artist"},
                "artform": localized(work["directionLabel"], language),
                "artMedium": localized(work["material"], language),
                "dateCreated": str(work.get("yearSort", "")),
                "isPartOf": {
                    "@type": "CollectionPage",
                    "name": i18n[language]["seo"]["catalogTitle"],
                    "url": page_url(language, "catalog", i18n),
                },
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{url}#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Lili Miller", "item": page_url(language, "home", i18n)},
                    {"@type": "ListItem", "position": 2, "name": ui["catalog"], "item": page_url(language, "catalog", i18n)},
                    {"@type": "ListItem", "position": 3, "name": title, "item": url},
                ],
            },
        ],
    }


def replace_tag_attribute(
    document: str,
    tag: str,
    selector_attribute: str,
    selector_value: str,
    target_attribute: str,
    target_value: str,
) -> str:
    pattern = re.compile(
        rf'<{tag}\b(?=[^>]*\b{re.escape(selector_attribute)}="{re.escape(selector_value)}")[^>]*>',
        re.DOTALL,
    )

    def replacer(match: re.Match[str]) -> str:
        source = match.group(0)
        value = html.escape(target_value, quote=True)
        target = re.compile(rf'\b{re.escape(target_attribute)}="[^"]*"')
        if target.search(source):
            return target.sub(f'{target_attribute}="{value}"', source, count=1)
        return source[:-1] + f' {target_attribute}="{value}">'

    return pattern.sub(replacer, document, count=1)


def replace_translations(document: str, language: str, section: str, i18n: dict) -> str:
    element_pattern = re.compile(
        r'(<(?P<tag>[A-Za-z][\w:-]*)\b(?=[^>]*\bdata-i18n="(?P<key>[^"]+)")[^>]*>)(?P<body>.*?)(</(?P=tag)>)',
        re.DOTALL,
    )

    def element_replacer(match: re.Match[str]) -> str:
        value = translate(i18n, language, section, match.group("key"))
        if not isinstance(value, str):
            raise TypeError(f"Element translation must be a string: {language}.{section}.{match.group('key')}")
        return f"{match.group(1)}{value}{match.group(5)}"

    document = element_pattern.sub(element_replacer, document)

    attribute_map = {
        "data-i18n-alt": "alt",
        "data-i18n-aria-label": "aria-label",
        "data-i18n-placeholder": "placeholder",
    }
    tag_pattern = re.compile(r'<[A-Za-z][^>]*\bdata-i18n-(?:alt|aria-label|placeholder)="[^"]+"[^>]*>', re.DOTALL)

    def tag_replacer(match: re.Match[str]) -> str:
        source = match.group(0)
        for data_attribute, target_attribute in attribute_map.items():
            key_match = re.search(rf'\b{re.escape(data_attribute)}="([^"]+)"', source)
            if not key_match:
                continue
            value = str(translate(i18n, language, section, key_match.group(1)))
            escaped_value = html.escape(value, quote=True)
            target = re.compile(rf'\b{re.escape(target_attribute)}="[^"]*"')
            if target.search(source):
                source = target.sub(f'{target_attribute}="{escaped_value}"', source, count=1)
            else:
                source = source[:-1] + f' {target_attribute}="{escaped_value}">'
        return source

    return tag_pattern.sub(tag_replacer, document)


def set_active_language(document: str, language: str, page: str, i18n: dict) -> str:
    pattern = re.compile(r'<nav class="language-toggle".*?</nav>', re.DOTALL)
    block_match = pattern.search(document)
    if not block_match:
        return document
    block = re.sub(r' aria-current="page"', "", block_match.group(0))
    href = page_path(language, page, i18n)
    block = block.replace(f'href="{href}"', f'href="{href}" aria-current="page"', 1)
    return document[: block_match.start()] + block + document[block_match.end() :]


def set_og_locales(document: str, language: str, i18n: dict) -> str:
    document = re.sub(r'\n\s*<meta property="og:locale:alternate"[^>]*>', "", document)
    current = i18n["languages"][language]["ogLocale"]
    document = replace_tag_attribute(document, "meta", "property", "og:locale", "content", current)
    alternates = [
        config["ogLocale"]
        for code, config in i18n["languages"].items()
        if code != language
    ]
    insertion = "".join(f'\n    <meta property="og:locale:alternate" content="{locale}" />' for locale in alternates)
    return re.sub(
        r'(<meta property="og:locale"[^>]*>)',
        lambda match: match.group(1) + insertion,
        document,
        count=1,
    )


def localize_shell(template: str, language: str, page: str, works: list[dict], i18n: dict) -> str:
    seo = i18n[language]["seo"]
    config = i18n["languages"][language]
    document = template.replace('<html lang="ru">', f'<html lang="{config["htmlLang"]}">', 1)
    document = replace_translations(document, language, page, i18n)

    if page == "home":
        title = seo["homeTitle"]
        description = seo["homeDescription"]
        social_description = seo["homeSocialDescription"]
        canonical = page_url(language, "home", i18n)
        schema = home_schema(language, i18n)
        schema_marker = "data-home-schema"
    else:
        title = seo["catalogTitle"]
        description = seo["catalogDescription"]
        social_description = seo["catalogSocialDescription"]
        canonical = page_url(language, "catalog", i18n)
        schema = catalog_schema(language, works, i18n)
        schema_marker = "data-catalog-schema"

    document = replace_tag_attribute(document, "meta", "name", "description", "content", description)
    document = replace_tag_attribute(document, "link", "rel", "canonical", "href", canonical)
    document = replace_tag_attribute(document, "meta", "property", "og:url", "content", canonical)
    document = replace_tag_attribute(document, "meta", "property", "og:title", "content", title)
    document = replace_tag_attribute(document, "meta", "property", "og:description", "content", social_description)
    document = replace_tag_attribute(document, "meta", "property", "og:image:alt", "content", seo["socialImageAlt"])
    document = replace_tag_attribute(document, "meta", "name", "twitter:title", "content", title)
    document = replace_tag_attribute(document, "meta", "name", "twitter:description", "content", social_description)
    document = replace_tag_attribute(document, "meta", "name", "twitter:image:alt", "content", seo["socialImageAlt"])
    document = re.sub(r'<title>.*?</title>', f'<title>{escaped(title)}</title>', document, count=1, flags=re.DOTALL)
    document = set_og_locales(document, language, i18n)
    document = set_active_language(document, language, page, i18n)

    script_pattern = re.compile(
        rf'<script type="application/ld\+json" {schema_marker}>.*?</script>',
        re.DOTALL,
    )
    script = (
        f'<script type="application/ld+json" {schema_marker}>\n'
        + json.dumps(schema, ensure_ascii=False, indent=2)
        + "\n    </script>"
    )
    document = script_pattern.sub(script, document, count=1)

    if page == "catalog":
        for work in works:
            pattern = re.compile(
                rf'(<a href="works/{re.escape(work["slug"])}/">).*?(</a>)',
                re.DOTALL,
            )
            document = pattern.sub(
                rf'\1{escaped(localized(work["title"], language))}\2',
                document,
                count=1,
            )

    document = document.replace('src="assets/', 'src="/assets/')
    document = document.replace('href="styles.css"', 'href="/styles.css"')
    document = document.replace('href="favicon.svg"', 'href="/favicon.svg"')
    document = document.replace('src="script.js"', 'src="/script.js"')
    document = document.replace('src="catalog.js"', 'src="/catalog.js"')
    return document


def render_gallery(work: dict, language: str, ui: dict) -> str:
    figures = []
    title = localized(work["title"], language)
    for index, source in enumerate(work.get("gallery", []), start=1):
        alt = format_text(ui["detailAlt"], title=title, index=index)
        figures.append(
            f'''          <figure class="work-gallery__item image-shell">
            <img src="{escaped(root_path(source))}" alt="{escaped(alt)}" loading="lazy" decoding="async" />
          </figure>'''
        )
    return "\n".join(figures)


def render_sources(work: dict, ui: dict) -> str:
    links = []
    for index, url in enumerate(work.get("sourcePosts", []), start=1):
        label = format_text(ui["originalPost"], index=f"{index:02d}")
        links.append(
            f'          <a href="{escaped(url)}" target="_blank" rel="noreferrer">{escaped(label)}</a>'
        )
    return "\n".join(links)


def render_related(work: dict, works: list[dict], language: str, i18n: dict, ui: dict) -> str:
    cards = []
    for item in related_works(work, works):
        title = localized(item["title"], language)
        alt = format_text(ui["imageAlt"], title=title)
        cards.append(
            f'''          <article class="related-card">
            <a class="related-card__link" href="{page_path(language, 'work', i18n, item['slug'])}">
              <img src="{escaped(root_path(item['hero']))}" alt="{escaped(alt)}" loading="lazy" decoding="async" />
              <div class="related-card__meta"><span>{escaped(localized(item['seriesLabel'], language))}</span><span>{escaped(item['year'])}</span></div>
              <h3>{escaped(title)}</h3>
            </a>
          </article>'''
        )
    return "\n".join(cards)


def render_work_page(work: dict, works: list[dict], language: str, i18n: dict) -> str:
    common = i18n[language]["common"]
    ui = i18n[language]["work"]
    seo = i18n[language]["seo"]
    config = i18n["languages"][language]
    title_text = localized(work["title"], language)
    title = f"{title_text} {ui['titleSuffix']}"
    description = f"{localized(work['excerpt'], language)} {format_text(ui['descriptionSuffix'], year=work['year'])}"
    url = page_url(language, "work", i18n, work["slug"])
    status_key = f"status{work['status'].capitalize()}"
    status = ui.get(status_key, work["status"])
    dimensions = localized(work.get("dimensions"), language) or ui["unknown"]
    edition = localized(work.get("edition"), language) or ui["unknown"]
    image_alt = format_text(ui["imageAlt"], title=title_text)
    gallery = work.get("gallery", [])
    og_alternates = "\n".join(
        f'    <meta property="og:locale:alternate" content="{item["ogLocale"]}" />'
        for code, item in i18n["languages"].items()
        if code != language
    )

    return f'''<!doctype html>
<html lang="{config['htmlLang']}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="{escaped(description)}" data-description />
    <meta name="author" content="Lili Miller" />
    <meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1" />
    <meta name="theme-color" content="#f2eee7" />
    <link rel="canonical" href="{url}" />
{alternate_links('work', i18n, work['slug'])}
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />

    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="Lili Miller" />
    <meta property="og:locale" content="{config['ogLocale']}" />
{og_alternates}
    <meta property="og:url" content="{url}" />
    <meta property="og:title" content="{escaped(title)}" />
    <meta property="og:description" content="{escaped(description)}" />
    <meta property="og:image" content="{SOCIAL_IMAGE}" />
    <meta property="og:image:type" content="image/jpeg" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta property="og:image:alt" content="{escaped(seo['socialImageAlt'])}" />

    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{escaped(title)}" />
    <meta name="twitter:description" content="{escaped(description)}" />
    <meta name="twitter:image" content="{SOCIAL_IMAGE}" />
    <meta name="twitter:image:alt" content="{escaped(seo['socialImageAlt'])}" />

    <title>{escaped(title)}</title>
    <script type="application/ld+json" data-work-schema>
{json.dumps(work_schema(work, language, i18n), ensure_ascii=False, indent=2)}
    </script>
    <link rel="stylesheet" href="/styles.css" />
{METRIKA_HEAD}
    <script src="/analytics.js" defer></script>
    <script src="/work.js" defer></script>
  </head>
  <body class="inner-page work-view">
    <noscript><div><img src="https://mc.yandex.ru/watch/110756646" style="position:absolute; left:-9999px;" alt="" /></div></noscript>
    <a class="skip-link" href="#main">{escaped(common['skipLink'])}</a>

    <header class="site-header site-header--inner" data-header>
      <a class="brand" href="{page_path(language, 'home', i18n)}#top" aria-label="{escaped(common['brandHome'])}">
        <span class="brand__mark" aria-hidden="true">LM</span><span class="brand__name">Lili Miller</span>
      </a>
      <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="main-navigation" data-menu-toggle>
        <span></span><span></span><span class="sr-only">{escaped(common['menuOpen'])}</span>
      </button>
      <nav class="main-nav" id="main-navigation" aria-label="{escaped(common['navLabel'])}" data-menu>
        <a href="{page_path(language, 'catalog', i18n)}" aria-current="page">{escaped(common['navCatalog'])}</a>
        <a href="{page_path(language, 'home', i18n)}#works">{escaped(common['navSelected'])}</a>
        <a href="{page_path(language, 'home', i18n)}#artist">{escaped(common['navArtist'])}</a>
        <a href="{page_path(language, 'home', i18n)}#exhibitions">{escaped(common['navExhibitions'])}</a>
        <a href="{page_path(language, 'home', i18n)}#contact">{escaped(common['navContact'])}</a>
      </nav>
      {language_switch(language, 'work', i18n, work['slug'])}
    </header>

    <main id="main" class="work-page" data-work-root data-work-slug="{escaped(work['slug'])}">
      <nav class="work-breadcrumbs" aria-label="{escaped(ui['breadcrumbs'])}">
        <a href="{page_path(language, 'home', i18n)}">Lili Miller</a><span>/</span><a href="{page_path(language, 'catalog', i18n)}">{escaped(ui['catalog'])}</a><span>/</span><span>{escaped(title_text)}</span>
      </nav>

      <section class="work-hero" aria-labelledby="work-title">
        <figure class="work-hero__figure image-shell">
          <img src="{escaped(root_path(work['hero']))}" alt="{escaped(image_alt)}" decoding="async" fetchpriority="high" />
        </figure>
        <div class="work-hero__content">
          <div class="work-hero__top"><span class="work-status work-status--{escaped(work['status'])}">{escaped(status)}</span><span>{escaped(work['year'])}</span></div>
          <p class="eyebrow">{escaped(localized(work['seriesLabel'], language))}</p>
          <h1 id="work-title">{escaped(title_text)}</h1>
          <p class="work-hero__lead">{escaped(localized(work['excerpt'], language))}</p>
          <dl class="work-facts">
            <div class="work-facts__item"><dt>{escaped(ui['material'])}</dt><dd>{escaped(localized(work['material'], language) or ui['unknown'])}</dd></div>
            <div class="work-facts__item"><dt>{escaped(ui['year'])}</dt><dd>{escaped(work['year'])}</dd></div>
            <div class="work-facts__item"><dt>{escaped(ui['status'])}</dt><dd>{escaped(status)}</dd></div>
            <div class="work-facts__item"><dt>{escaped(ui['edition'])}</dt><dd>{escaped(edition)}</dd></div>
            <div class="work-facts__item"><dt>{escaped(ui['size'])}</dt><dd>{escaped(dimensions)}</dd></div>
          </dl>
          <a class="work-inquiry" href="https://t.me/lilimiller" target="_blank" rel="noreferrer">{escaped(ui['inquiry'])}</a>
        </div>
      </section>

      <section class="work-story">
        <div class="work-story__index">{escaped(ui['storyIndex'])}</div>
        <div class="work-story__content">
          <p class="eyebrow">{escaped(localized(work['directionLabel'], language))}</p>
          <h2>{escaped(ui['storyTitle'])}</h2>
          <p class="work-story__text">{escaped(localized(work['story'], language))}</p>
        </div>
      </section>

      <section class="work-gallery-section">
        <div class="work-section-heading"><p class="eyebrow">{escaped(format_text(ui['galleryLabel'], count=len(gallery)))}</p><h2>{escaped(ui['details'])}</h2></div>
        <div class="work-gallery">
{render_gallery(work, language, ui)}
        </div>
      </section>

      <section class="work-sources">
        <p class="eyebrow">{escaped(ui['archive'])}</p><h2>{escaped(ui['publications'])}</h2>
        <div class="work-sources__links">
{render_sources(work, ui)}
        </div>
      </section>

      <section class="related-works">
        <div class="work-section-heading work-section-heading--row"><p class="eyebrow">{escaped(ui['relatedLabel'])}</p><h2>{escaped(ui['relatedTitle'])}</h2></div>
        <div class="related-grid">
{render_related(work, works, language, i18n, ui)}
        </div>
      </section>
    </main>

    <footer class="inner-footer">
      <span>© 2026 Lili Miller</span>
      <a href="https://t.me/lilimillerdoll" target="_blank" rel="noreferrer">{escaped(common['telegramChannel'])}</a>
      <a href="{page_path(language, 'catalog', i18n)}">{escaped(ui['allWorks'])}</a>
    </footer>
  </body>
</html>
'''


def render_sitemap(works: list[dict], last_modified: str, i18n: dict) -> str:
    groups: list[tuple[str, str | None, str, dict[str, str]]] = [
        (
            "home",
            None,
            f"{SITE_ORIGIN}/assets/images/telegram-web/lilimillerdoll/232.webp",
            {language: i18n[language]["home"]["heroImageAlt"] for language in i18n["languages"]},
        ),
        (
            "catalog",
            None,
            SOCIAL_IMAGE,
            {language: i18n[language]["seo"]["catalogTitle"] for language in i18n["languages"]},
        ),
    ]
    for work in works:
        groups.append(
            (
                "work",
                work["slug"],
                f"{SITE_ORIGIN}{root_path(work['hero'])}",
                {
                    language: format_text(
                        i18n[language]["work"]["imageAlt"],
                        title=localized(work["title"], language),
                    )
                    for language in i18n["languages"]
                },
            )
        )

    entries = []
    for page, slug, image_url, captions in groups:
        variants = {
            language: page_url(language, page, i18n, slug)
            for language in i18n["languages"]
        }
        alternate_markup = "\n".join(
            f'    <xhtml:link rel="alternate" hreflang="{config["hreflang"]}" href="{html.escape(variants[language], quote=True)}" />'
            for language, config in i18n["languages"].items()
        )
        alternate_markup += (
            f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{html.escape(variants["ru"], quote=True)}" />'
        )
        for language, location in variants.items():
            entries.append(
                f'''  <url>
    <loc>{html.escape(location)}</loc>
{alternate_markup}
    <lastmod>{html.escape(last_modified)}</lastmod>
    <image:image>
      <image:loc>{html.escape(image_url)}</image:loc>
      <image:caption>{html.escape(captions[language])}</image:caption>
    </image:image>
  </url>'''
            )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )


def output_root(language: str, i18n: dict) -> Path:
    prefix = language_prefix(language, i18n).lstrip("/")
    return ROOT / prefix if prefix else ROOT


def clear_stale_work_pages(directory: Path, expected: set[Path]) -> None:
    if not directory.exists():
        return
    for target_dir in directory.iterdir():
        if target_dir.is_dir() and target_dir not in expected:
            generated_file = target_dir / "index.html"
            if generated_file.exists():
                generated_file.unlink()
            try:
                target_dir.rmdir()
            except OSError:
                pass


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    i18n = json.loads(I18N_PATH.read_text(encoding="utf-8"))
    works = data.get("works", [])
    last_modified = data.get("generatedAt", "2026-07-15")

    index_template = (ROOT / "index.html").read_text(encoding="utf-8")
    catalog_template = (ROOT / "catalog.html").read_text(encoding="utf-8")

    for language in i18n["languages"]:
        language_root = output_root(language, i18n)
        language_root.mkdir(parents=True, exist_ok=True)

        if language != "ru":
            (language_root / "index.html").write_text(
                localize_shell(index_template, language, "home", works, i18n),
                encoding="utf-8",
            )
            (language_root / "catalog.html").write_text(
                localize_shell(catalog_template, language, "catalog", works, i18n),
                encoding="utf-8",
            )

        works_dir = language_root / "works"
        works_dir.mkdir(exist_ok=True)
        expected = set()
        for work in works:
            target_dir = works_dir / work["slug"]
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "index.html").write_text(
                render_work_page(work, works, language, i18n),
                encoding="utf-8",
            )
            expected.add(target_dir)
        clear_stale_work_pages(works_dir, expected)

    (ROOT / "sitemap.xml").write_text(render_sitemap(works, last_modified, i18n), encoding="utf-8")
    (ROOT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_ORIGIN}/sitemap.xml\n",
        encoding="utf-8",
    )
    page_count = len(i18n["languages"]) * (len(works) + 2)
    print(f"Generated {page_count} localized pages, sitemap.xml and robots.txt")


if __name__ == "__main__":
    main()
