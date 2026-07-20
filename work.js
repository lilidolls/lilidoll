const root = document.querySelector("[data-work-root]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const menu = document.querySelector("[data-menu]");
const SITE_ORIGIN = "https://lilidoll.ru";

const LANGUAGE = document.documentElement.lang === "zh-Hans"
  ? "zh"
  : document.documentElement.lang.startsWith("en")
    ? "en"
    : "ru";
const LANGUAGE_PREFIX = LANGUAGE === "ru" ? "" : `/${LANGUAGE}`;

let ui = null;
let imageAssets = { images: {} };

function format(template, values) {
  return Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );
}

function localized(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return value[LANGUAGE] || value.en || value.ru || "";
}

function rootPath(path) {
  if (!path || /^(?:https?:)?\/\//.test(path)) return path;
  return `/${path.replace(/^\/+/, "")}`;
}

function homePath() {
  return `${LANGUAGE_PREFIX}/` || "/";
}

function catalogPath() {
  return `${LANGUAGE_PREFIX}/catalog.html`;
}

function workPath(slug) {
  return `${LANGUAGE_PREFIX}/works/${encodeURIComponent(slug)}/`;
}

function updateLanguageLinks(slug) {
  const prefixes = { ru: "", en: "/en", zh: "/zh" };
  document.querySelectorAll("[data-language-code]").forEach((link) => {
    const prefix = prefixes[link.dataset.languageCode];
    if (prefix == null) return;
    link.href = slug ? `${prefix}/works/${encodeURIComponent(slug)}/` : `${prefix}/` || "/";
  });
}

function applyResponsiveImage(image, path, sizes) {
  const metadata = imageAssets.images?.[path];
  if (!metadata) return;
  image.width = metadata.width;
  image.height = metadata.height;
  image.srcset = metadata.variants
    .map((variant) => `${rootPath(variant.path)} ${variant.width}w`)
    .join(", ");
  image.sizes = sizes;
}

function inquiryUrl(work) {
  const message = format(ui.inquiryMessage, {
    title: localized(work.title),
    year: work.year,
  });
  const url = new URL("https://t.me/lilimiller");
  url.searchParams.set("text", message);
  return url.toString();
}

function setMetaContent(selector, content) {
  document.querySelector(selector)?.setAttribute("content", content);
}

function statusLabel(status) {
  const key = `status${status.charAt(0).toUpperCase()}${status.slice(1)}`;
  return ui?.[key] || status;
}

function updateMetadata(work) {
  const title = `${localized(work.title)} ${ui.titleSuffix}`;
  const description = `${localized(work.excerpt)} ${format(ui.descriptionSuffix, { year: work.year })}`;
  const url = `${SITE_ORIGIN}${workPath(work.slug)}`;

  document.title = title;
  document.querySelector("[data-description]")?.setAttribute("content", description);
  setMetaContent('meta[property="og:title"]', title);
  setMetaContent('meta[property="og:description"]', description);
  setMetaContent('meta[property="og:url"]', url);
  setMetaContent('meta[name="twitter:title"]', title);
  setMetaContent('meta[name="twitter:description"]', description);

  let canonical = document.querySelector('link[rel="canonical"]');
  if (!canonical) {
    canonical = document.createElement("link");
    canonical.rel = "canonical";
    document.head.append(canonical);
  }
  canonical.href = url;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function closeMenu() {
  menu?.classList.remove("is-open");
  menuToggle?.setAttribute("aria-expanded", "false");
  document.body.classList.remove("is-menu-open");
}

menuToggle?.addEventListener("click", () => {
  const isOpen = menuToggle.getAttribute("aria-expanded") !== "true";
  menuToggle.setAttribute("aria-expanded", String(isOpen));
  menu?.classList.toggle("is-open", isOpen);
  document.body.classList.toggle("is-menu-open", isOpen);
});
menu?.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));

function fact(label, value) {
  const item = element("div", "work-facts__item");
  item.append(element("dt", "", label), element("dd", "", value || ui.unknown));
  return item;
}

function createRelatedCard(work) {
  const article = element("article", "related-card");
  const link = element("a", "related-card__link");
  link.href = workPath(work.slug);
  const image = element("img");
  image.src = rootPath(work.hero);
  applyResponsiveImage(image, work.hero, "(max-width: 760px) 100vw, 33vw");
  image.alt = format(ui.imageAlt, { title: localized(work.title) });
  image.loading = "lazy";
  image.decoding = "async";
  const meta = element("div", "related-card__meta");
  meta.append(element("span", "", localized(work.seriesLabel)), element("span", "", work.year));
  const title = element("h3", "", localized(work.title));
  link.append(image, meta, title);
  article.append(link);
  return article;
}

function renderWork(work, works) {
  updateMetadata(work);

  const breadcrumbs = element("nav", "work-breadcrumbs");
  breadcrumbs.setAttribute("aria-label", ui.breadcrumbs);
  const homeLink = element("a", "", "Lili Miller");
  homeLink.href = homePath();
  const catalogLink = element("a", "", ui.catalog);
  catalogLink.href = catalogPath();
  breadcrumbs.append(
    homeLink,
    element("span", "", "/"),
    catalogLink,
    element("span", "", "/"),
    element("span", "", localized(work.title))
  );

  const hero = element("section", "work-hero");
  hero.setAttribute("aria-labelledby", "work-title");
  const heroFigure = element("figure", "work-hero__figure image-shell");
  const heroImage = element("img");
  heroImage.src = rootPath(work.hero);
  applyResponsiveImage(heroImage, work.hero, "(max-width: 760px) 100vw, 50vw");
  heroImage.alt = format(ui.imageAlt, { title: localized(work.title) });
  heroImage.decoding = "async";
  heroFigure.append(heroImage);

  const content = element("div", "work-hero__content");
  const top = element("div", "work-hero__top");
  const status = element("span", `work-status work-status--${work.status}`, statusLabel(work.status));
  top.append(status, element("span", "", work.year));
  const series = element("p", "eyebrow", localized(work.seriesLabel));
  const title = element("h1", "", localized(work.title));
  title.id = "work-title";
  const excerpt = element("p", "work-hero__lead", localized(work.excerpt));
  const facts = element("dl", "work-facts");
  facts.append(
    fact(ui.material, localized(work.material)),
    fact(ui.year, work.year),
    fact(ui.status, statusLabel(work.status)),
    fact(ui.edition, localized(work.edition)),
    fact(ui.size, localized(work.dimensions))
  );
  const inquiry = element("a", "work-inquiry", ui.inquiry);
  inquiry.href = inquiryUrl(work);
  inquiry.target = "_blank";
  inquiry.rel = "noreferrer";
  inquiry.dataset.ymGoal = "inquiry_start";
  inquiry.dataset.ymSource = "work_hero";
  inquiry.dataset.ymWork = work.slug;
  content.append(top, series, title, excerpt, facts, inquiry);
  hero.append(heroFigure, content);

  const inquirySection = element("section", "work-inquiry-panel");
  inquirySection.setAttribute("aria-labelledby", "work-inquiry-title");
  const inquiryHeading = element("div");
  inquiryHeading.append(
    element("p", "eyebrow", ui.inquiryEyebrow),
    element("h2", "", ui.inquiryTitle)
  );
  inquiryHeading.querySelector("h2").id = "work-inquiry-title";
  const inquiryContent = element("div", "work-inquiry-panel__content");
  const inquiryButton = element("a", "contact__button", ui.inquiryButton);
  inquiryButton.href = inquiryUrl(work);
  inquiryButton.target = "_blank";
  inquiryButton.rel = "noreferrer";
  inquiryButton.dataset.ymGoal = "inquiry_start";
  inquiryButton.dataset.ymSource = "work_inquiry";
  inquiryButton.dataset.ymWork = work.slug;
  const inquiryArrow = element("span", "", "↗");
  inquiryArrow.setAttribute("aria-hidden", "true");
  inquiryButton.append(inquiryArrow);
  inquiryContent.append(
    element("p", "", ui.inquiryText),
    inquiryButton,
    element("small", "", ui.inquiryNote)
  );
  inquirySection.append(inquiryHeading, inquiryContent);

  const story = element("section", "work-story");
  const storyIndex = element("div", "work-story__index", ui.storyIndex);
  const storyContent = element("div", "work-story__content");
  storyContent.append(
    element("p", "eyebrow", localized(work.directionLabel)),
    element("h2", "", ui.storyTitle),
    element("p", "work-story__text", localized(work.story))
  );
  story.append(storyIndex, storyContent);

  const gallerySection = element("section", "work-gallery-section");
  const galleryHeading = element("div", "work-section-heading");
  galleryHeading.append(
    element("p", "eyebrow", format(ui.galleryLabel, { count: work.gallery.length })),
    element("h2", "", ui.details)
  );
  const gallery = element("div", "work-gallery");
  work.gallery.forEach((src, index) => {
    const figure = element("figure", "work-gallery__item image-shell");
    const image = element("img");
    image.src = rootPath(src);
    applyResponsiveImage(image, src, "(max-width: 760px) 100vw, 50vw");
    image.alt = format(ui.detailAlt, { title: localized(work.title), index: index + 1 });
    image.loading = index < 2 ? "eager" : "lazy";
    image.decoding = "async";
    figure.append(image);
    gallery.append(figure);
  });
  gallerySection.append(galleryHeading, gallery);

  const sourceSection = element("section", "work-sources");
  sourceSection.append(element("p", "eyebrow", ui.archive));
  sourceSection.append(element("h2", "", ui.publications));
  const sourceLinks = element("div", "work-sources__links");
  work.sourcePosts.forEach((url, index) => {
    const label = format(ui.originalPost, { index: String(index + 1).padStart(2, "0") });
    const link = element("a", "", label);
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
    sourceLinks.append(link);
  });
  sourceSection.append(sourceLinks);

  const related = works
    .filter((item) => item.slug !== work.slug && (item.series === work.series || item.direction === work.direction))
    .sort((a, b) => (a.series === work.series ? -1 : 1) - (b.series === work.series ? -1 : 1) || a.sortOrder - b.sortOrder)
    .slice(0, 3);
  const relatedSection = element("section", "related-works");
  const relatedHeading = element("div", "work-section-heading work-section-heading--row");
  relatedHeading.append(element("p", "eyebrow", ui.relatedLabel), element("h2", "", ui.relatedTitle));
  const relatedGrid = element("div", "related-grid");
  related.forEach((item) => relatedGrid.append(createRelatedCard(item)));
  relatedSection.append(relatedHeading, relatedGrid);

  root.replaceChildren(breadcrumbs, hero, inquirySection, story, gallerySection, sourceSection, relatedSection);
}

function renderError(message) {
  const section = element("section", "work-error");
  section.append(element("p", "eyebrow", ui.catalog), element("h1", "", message));
  const link = element("a", "text-link", ui.returnCatalog);
  link.href = catalogPath();
  section.append(link);
  root.replaceChildren(section);
}

async function loadWork() {
  const slug = root?.dataset.workSlug || new URLSearchParams(window.location.search).get("slug");
  updateLanguageLinks(slug);

  try {
    const [worksResponse, i18nResponse, imageAssetsResponse] = await Promise.all([
      fetch("/data/works.json"),
      fetch("/data/i18n.json"),
      fetch("/data/image-assets.json"),
    ]);
    if (!worksResponse.ok) throw new Error(`Works HTTP ${worksResponse.status}`);
    if (!i18nResponse.ok) throw new Error(`I18n HTTP ${i18nResponse.status}`);
    if (!imageAssetsResponse.ok) throw new Error(`Image assets HTTP ${imageAssetsResponse.status}`);
    const [data, i18n, loadedImageAssets] = await Promise.all([
      worksResponse.json(),
      i18nResponse.json(),
      imageAssetsResponse.json(),
    ]);
    ui = i18n[LANGUAGE].work;
    imageAssets = loadedImageAssets;

    if (!slug) {
      renderError(ui.notSelected);
      return;
    }
    const work = data.works.find((item) => item.slug === slug);
    if (!work) {
      renderError(ui.notFound);
      return;
    }
    renderWork(work, data.works);
  } catch (error) {
    ui ||= {
      catalog: "Каталог",
      loadError: "Не удалось загрузить работу",
      returnCatalog: "Вернуться ко всем работам →",
    };
    renderError(ui.loadError);
    console.error("Work loading error", error);
  }
}

if (root && !root.dataset.workSlug) loadWork();
