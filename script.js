const header = document.querySelector("[data-header]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const menu = document.querySelector("[data-menu]");
const dialog = document.querySelector("[data-dialog]");

const LANGUAGE = document.documentElement.lang === "zh-Hans"
  ? "zh"
  : document.documentElement.lang.startsWith("en")
    ? "en"
    : "ru";

const imagePositions = {
  otsuyu: "center top",
  "caterina-sforza": "center top",
};

function localized(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return value[LANGUAGE] || value.en || value.ru || "";
}

function rootPath(path) {
  if (!path || /^(?:https?:)?\/\//.test(path)) return path;
  return `/${path.replace(/^\/+/, "")}`;
}

function applyResponsiveImage(image, path, imageAssets, sizes) {
  const metadata = imageAssets.images?.[path];
  if (!metadata) return;
  image.width = metadata.width;
  image.height = metadata.height;
  image.srcset = metadata.variants
    .map((variant) => `${rootPath(variant.path)} ${variant.width}w`)
    .join(", ");
  image.sizes = sizes;
}

function updateHeader() {
  header?.classList.toggle("is-scrolled", window.scrollY > window.innerHeight * 0.72);
}

function closeMenu() {
  menu?.classList.remove("is-open");
  menuToggle?.setAttribute("aria-expanded", "false");
  document.body.classList.remove("is-menu-open");
}

menuToggle?.addEventListener("click", () => {
  const nextState = menuToggle.getAttribute("aria-expanded") !== "true";
  menuToggle.setAttribute("aria-expanded", String(nextState));
  menu?.classList.toggle("is-open", nextState);
  document.body.classList.toggle("is-menu-open", nextState);
});

menu?.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));
window.addEventListener("scroll", updateHeader, { passive: true });
updateHeader();

const revealObserver = new IntersectionObserver(
  (entries) => entries.forEach((entry) => entry.isIntersecting && entry.target.classList.add("is-visible")),
  { threshold: 0.12 }
);
document.querySelectorAll(".reveal").forEach((element) => revealObserver.observe(element));

const pageData = Promise.all([
  fetch("/data/works.json").then((response) => {
    if (!response.ok) throw new Error(`Works HTTP ${response.status}`);
    return response.json();
  }),
  fetch("/data/i18n.json").then((response) => {
    if (!response.ok) throw new Error(`I18n HTTP ${response.status}`);
    return response.json();
  }),
  fetch("/data/image-assets.json").then((response) => {
    if (!response.ok) throw new Error(`Image assets HTTP ${response.status}`);
    return response.json();
  }),
]).then(([worksData, i18n, imageAssets]) => ({
  works: new Map((worksData.works || []).map((work) => [work.slug, work])),
  labels: i18n[LANGUAGE],
  imageAssets,
}));

function fillDialog(work, labels, imageAssets) {
  const dialogImage = dialog.querySelector("[data-dialog-image]");
  dialogImage.src = rootPath(work.hero);
  applyResponsiveImage(dialogImage, work.hero, imageAssets, "(max-width: 760px) 100vw, 45vw");
  dialogImage.alt = labels.work.imageAlt.replace("{title}", localized(work.title));
  dialogImage.style.objectPosition = imagePositions[work.slug] || "center";
  dialog.querySelector("[data-dialog-series]").textContent = localized(work.seriesLabel);
  dialog.querySelector("[data-dialog-title]").textContent = localized(work.title);
  dialog.querySelector("[data-dialog-lead]").textContent = localized(work.excerpt);
  dialog.querySelector("[data-dialog-story]").textContent = localized(work.story);
  dialog.querySelector("[data-dialog-year]").textContent = work.year;
  dialog.querySelector("[data-dialog-material]").textContent = localized(work.material);
  dialog.querySelector("[data-dialog-status]").textContent = labels.catalog[
    `status${work.status.charAt(0).toUpperCase()}${work.status.slice(1)}`
  ] || work.status;
}

document.querySelectorAll("[data-work]").forEach((card) => {
  card.querySelector(".work-card__open")?.addEventListener("click", async () => {
    try {
      const { works, labels, imageAssets } = await pageData;
      const work = works.get(card.dataset.work);
      if (!work) return;
      fillDialog(work, labels, imageAssets);
      dialog.showModal();
      window.liliAnalytics?.reachGoal("work_preview", {
        source: "homepage",
        work_slug: work.slug,
      });
    } catch (error) {
      console.error("Work dialog loading error", error);
    }
  });
});

dialog?.querySelector("[data-dialog-close]")?.addEventListener("click", () => dialog.close());
dialog?.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
});
