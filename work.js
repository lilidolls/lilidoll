const root = document.querySelector("[data-work-root]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const menu = document.querySelector("[data-menu]");

const statusLabels = {
  exhibition: "На выставке",
  private: "Частная коллекция",
  archive: "Архив",
  available: "Доступна",
};

function localized(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return value.ru || value.en || "";
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
  item.append(element("dt", "", label), element("dd", "", value || "Уточняется"));
  return item;
}

function createRelatedCard(work) {
  const article = element("article", "related-card");
  const link = element("a", "related-card__link");
  link.href = `work.html?slug=${encodeURIComponent(work.slug)}`;
  const image = element("img");
  image.src = work.hero;
  image.alt = `${localized(work.title)} — авторская кукла Lili Miller`;
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
  document.title = `${localized(work.title)} — Lili Miller`;
  document.querySelector("[data-description]")?.setAttribute("content", localized(work.excerpt));

  const breadcrumbs = element("nav", "work-breadcrumbs");
  breadcrumbs.setAttribute("aria-label", "Хлебные крошки");
  const homeLink = element("a", "", "Lili Miller");
  homeLink.href = "index.html";
  const catalogLink = element("a", "", "Каталог");
  catalogLink.href = "catalog.html";
  breadcrumbs.append(homeLink, element("span", "", "/"), catalogLink, element("span", "", "/"), element("span", "", localized(work.title)));

  const hero = element("section", "work-hero");
  hero.setAttribute("aria-labelledby", "work-title");
  const heroFigure = element("figure", "work-hero__figure image-shell");
  const heroImage = element("img");
  heroImage.src = work.hero;
  heroImage.alt = `${localized(work.title)} — авторская кукла Lili Miller`;
  heroImage.decoding = "async";
  heroFigure.append(heroImage);

  const content = element("div", "work-hero__content");
  const top = element("div", "work-hero__top");
  const status = element("span", `work-status work-status--${work.status}`, statusLabels[work.status] || work.status);
  top.append(status, element("span", "", work.year));
  const series = element("p", "eyebrow", localized(work.seriesLabel));
  const title = element("h1", "", localized(work.title));
  title.id = "work-title";
  const excerpt = element("p", "work-hero__lead", localized(work.excerpt));
  const facts = element("dl", "work-facts");
  facts.append(
    fact("Материал", localized(work.material)),
    fact("Год", work.year),
    fact("Статус", statusLabels[work.status] || work.status),
    fact("Тираж", localized(work.edition)),
    fact("Размер", work.dimensions)
  );
  const inquiry = element("a", "work-inquiry", "Уточнить о работе в Telegram ↗");
  inquiry.href = "https://t.me/lilimiller";
  inquiry.target = "_blank";
  inquiry.rel = "noreferrer";
  content.append(top, series, title, excerpt, facts, inquiry);
  hero.append(heroFigure, content);

  const story = element("section", "work-story");
  const storyIndex = element("div", "work-story__index", "История / 01");
  const storyContent = element("div", "work-story__content");
  storyContent.append(element("p", "eyebrow", localized(work.directionLabel)), element("h2", "", "История персонажа"), element("p", "work-story__text", localized(work.story)));
  story.append(storyIndex, storyContent);

  const gallerySection = element("section", "work-gallery-section");
  const galleryHeading = element("div", "work-section-heading");
  galleryHeading.append(element("p", "eyebrow", `Галерея · ${work.gallery.length} кадров`), element("h2", "", "Детали образа"));
  const gallery = element("div", "work-gallery");
  work.gallery.forEach((src, index) => {
    const figure = element("figure", "work-gallery__item image-shell");
    const image = element("img");
    image.src = src;
    image.alt = `${localized(work.title)}, деталь ${index + 1}`;
    image.loading = index < 2 ? "eager" : "lazy";
    image.decoding = "async";
    figure.append(image);
    gallery.append(figure);
  });
  gallerySection.append(galleryHeading, gallery);

  const sourceSection = element("section", "work-sources");
  sourceSection.append(element("p", "eyebrow", "Архив художника"));
  const sourceTitle = element("h2", "", "Публикации о работе");
  sourceSection.append(sourceTitle);
  const sourceLinks = element("div", "work-sources__links");
  work.sourcePosts.forEach((url, index) => {
    const link = element("a", "", `Оригинальная публикация ${String(index + 1).padStart(2, "0")} ↗`);
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
  relatedHeading.append(element("p", "eyebrow", "Продолжить знакомство"), element("h2", "", "Другие работы"));
  const relatedGrid = element("div", "related-grid");
  related.forEach((item) => relatedGrid.append(createRelatedCard(item)));
  relatedSection.append(relatedHeading, relatedGrid);

  root.replaceChildren(breadcrumbs, hero, story, gallerySection, sourceSection, relatedSection);
}

function renderError(message) {
  const section = element("section", "work-error");
  section.append(element("p", "eyebrow", "Каталог"), element("h1", "", message));
  const link = element("a", "text-link", "Вернуться ко всем работам →");
  link.href = "catalog.html";
  section.append(link);
  root.replaceChildren(section);
}

async function loadWork() {
  const slug = new URLSearchParams(window.location.search).get("slug");
  if (!slug) {
    renderError("Работа не выбрана");
    return;
  }

  try {
    const response = await fetch("data/works.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const work = data.works.find((item) => item.slug === slug);
    if (!work) {
      renderError("Работа не найдена");
      return;
    }
    renderWork(work, data.works);
  } catch (error) {
    renderError("Не удалось загрузить работу");
    console.error("Work loading error", error);
  }
}

loadWork();
