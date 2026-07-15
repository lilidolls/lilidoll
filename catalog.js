const catalogRoot = document.querySelector("[data-catalog-grid]");
const catalogStatus = document.querySelector("[data-catalog-status]");
const resultsSummary = document.querySelector("[data-results-summary]");
const catalogTotal = document.querySelector("[data-catalog-total]");
const filtersForm = document.querySelector("[data-catalog-filters]");
const filterChips = document.querySelector("[data-filter-chips]");
const resetButton = document.querySelector("[data-filter-reset]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const menu = document.querySelector("[data-menu]");

const LANGUAGE = document.documentElement.lang === "zh-Hans"
  ? "zh"
  : document.documentElement.lang.startsWith("en")
    ? "en"
    : "ru";
const LANGUAGE_PREFIX = LANGUAGE === "ru" ? "" : `/${LANGUAGE}`;
const LOCALE = LANGUAGE === "zh" ? "zh-Hans" : LANGUAGE;

let works = [];
let ui = null;
let searchGoalTimer = null;

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

function workPath(slug) {
  return `${LANGUAGE_PREFIX}/works/${encodeURIComponent(slug)}/`;
}

function statusLabel(status) {
  const key = `status${status.charAt(0).toUpperCase()}${status.slice(1)}`;
  return ui?.[key] || status;
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

function addOptions(select, items) {
  const fragment = document.createDocumentFragment();
  items.forEach(({ value, label }) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    fragment.append(option);
  });
  select.append(fragment);
}

function uniqueBy(items, key) {
  const map = new Map();
  items.forEach((item) => map.set(item[key], item));
  return [...map.values()];
}

function setupFilterOptions() {
  const directions = uniqueBy(
    works.map((work) => ({ direction: work.direction, label: localized(work.directionLabel) })),
    "direction"
  )
    .map((item) => ({ value: item.direction, label: item.label }))
    .sort((a, b) => a.label.localeCompare(b.label, LOCALE));

  const series = uniqueBy(
    works.map((work) => ({ series: work.series, label: localized(work.seriesLabel) })),
    "series"
  )
    .map((item) => ({ value: item.series, label: item.label }))
    .sort((a, b) => a.label.localeCompare(b.label, LOCALE));

  const years = [...new Set(works.map((work) => String(work.yearSort)))]
    .sort((a, b) => Number(b) - Number(a))
    .map((year) => ({ value: year, label: year }));

  addOptions(filtersForm.elements.direction, directions);
  addOptions(filtersForm.elements.series, series);
  addOptions(filtersForm.elements.year, years);
}

function restoreFiltersFromUrl() {
  const params = new URLSearchParams(window.location.search);
  ["q", "direction", "series", "year", "status", "sort"].forEach((name) => {
    const value = params.get(name);
    if (value && filtersForm.elements[name]) filtersForm.elements[name].value = value;
  });
}

function getState() {
  const data = new FormData(filtersForm);
  return {
    q: String(data.get("q") || "").trim(),
    direction: String(data.get("direction") || ""),
    series: String(data.get("series") || ""),
    year: String(data.get("year") || ""),
    status: String(data.get("status") || ""),
    sort: String(data.get("sort") || "curated"),
  };
}

function filterAndSort(state) {
  const query = state.q.toLocaleLowerCase(LOCALE);
  const filtered = works.filter((work) => {
    const searchable = [
      localized(work.title),
      localized(work.excerpt),
      localized(work.story),
      localized(work.seriesLabel),
      localized(work.directionLabel),
    ]
      .join(" ")
      .toLocaleLowerCase(LOCALE);

    return (
      (!query || searchable.includes(query)) &&
      (!state.direction || work.direction === state.direction) &&
      (!state.series || work.series === state.series) &&
      (!state.year || String(work.yearSort) === state.year) &&
      (!state.status || work.status === state.status)
    );
  });

  const sorters = {
    curated: (a, b) => a.sortOrder - b.sortOrder,
    newest: (a, b) => b.yearSort - a.yearSort || a.sortOrder - b.sortOrder,
    oldest: (a, b) => a.yearSort - b.yearSort || a.sortOrder - b.sortOrder,
    name: (a, b) => localized(a.title).localeCompare(localized(b.title), LOCALE),
  };
  return filtered.sort(sorters[state.sort] || sorters.curated);
}

function createCard(work, index) {
  const article = document.createElement("article");
  article.className = "catalog-card";

  const link = document.createElement("a");
  link.className = "catalog-card__link";
  link.href = workPath(work.slug);
  link.setAttribute("aria-label", format(ui.openWork, { title: localized(work.title) }));

  const imageWrap = document.createElement("div");
  imageWrap.className = "catalog-card__image image-shell";
  const image = document.createElement("img");
  image.src = rootPath(work.hero);
  image.alt = format(ui.imageAlt, { title: localized(work.title) });
  image.loading = "lazy";
  image.decoding = "async";
  imageWrap.append(image);

  const status = document.createElement("span");
  status.className = `catalog-card__status catalog-card__status--${work.status}`;
  status.textContent = statusLabel(work.status);
  imageWrap.append(status);

  const body = document.createElement("div");
  body.className = "catalog-card__body";
  const meta = document.createElement("div");
  meta.className = "catalog-card__meta";
  const number = document.createElement("span");
  number.textContent = String(index + 1).padStart(2, "0");
  const series = document.createElement("span");
  series.textContent = localized(work.seriesLabel);
  meta.append(number, series);

  const title = document.createElement("h3");
  title.textContent = localized(work.title);
  const excerpt = document.createElement("p");
  excerpt.textContent = localized(work.excerpt);
  const foot = document.createElement("div");
  foot.className = "catalog-card__foot";
  const year = document.createElement("span");
  year.textContent = work.year;
  const open = document.createElement("span");
  open.textContent = ui.view;
  foot.append(year, open);

  body.append(meta, title, excerpt, foot);
  link.append(imageWrap, body);
  article.append(link);
  return article;
}

function updateUrl(state) {
  const params = new URLSearchParams();
  Object.entries(state).forEach(([key, value]) => {
    if (value && !(key === "sort" && value === "curated")) params.set(key, value);
  });
  const query = params.toString();
  history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
}

function selectedLabel(name, value) {
  if (name === "q") return format(ui.searchChip, { value });
  const option = filtersForm.elements[name]?.selectedOptions?.[0];
  return option?.textContent || value;
}

function renderChips(state) {
  filterChips.replaceChildren();
  ["q", "direction", "series", "year", "status"].forEach((name) => {
    const value = state[name];
    if (!value) return;
    const label = selectedLabel(name, value);
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.clearFilter = name;
    button.textContent = `${label} ×`;
    button.setAttribute("aria-label", format(ui.clearFilter, { label }));
    filterChips.append(button);
  });
}

function countNoun(count) {
  if (LANGUAGE !== "ru") return count === 1 ? ui.nounOne : ui.nounMany;
  if (count % 10 === 1 && count % 100 !== 11) return ui.nounOne;
  if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) return ui.nounFew;
  return ui.nounMany;
}

function render() {
  const state = getState();
  const filtered = filterAndSort(state);
  const fragment = document.createDocumentFragment();
  filtered.forEach((work, index) => fragment.append(createCard(work, index)));
  catalogRoot.replaceChildren(fragment);

  resultsSummary.textContent = format(ui.found, {
    count: filtered.length,
    noun: countNoun(filtered.length),
  });
  catalogStatus.textContent = filtered.length ? "" : ui.noResults;
  catalogStatus.hidden = Boolean(filtered.length);
  renderChips(state);
  updateUrl(state);
}

function trackGoal(target, params = {}) {
  window.liliAnalytics?.reachGoal(target, params);
}

function scheduleSearchGoal() {
  window.clearTimeout(searchGoalTimer);
  const state = getState();
  if (!state.q) return;

  searchGoalTimer = window.setTimeout(() => {
    trackGoal("catalog_search", {
      query_length: state.q.length,
      results_count: filterAndSort(state).length,
    });
  }, 700);
}

filtersForm?.addEventListener("input", (event) => {
  if (event.target.name !== "q") return;
  render();
  scheduleSearchGoal();
});
filtersForm?.addEventListener("change", (event) => {
  if (event.target.name === "q") return;
  render();

  const name = event.target.name;
  const value = event.target.value || "all";
  if (name === "sort") {
    trackGoal("catalog_sort", { sort: value });
  } else {
    trackGoal("catalog_filter", { action: "change", filter: name, value });
  }
});
resetButton?.addEventListener("click", () => {
  window.clearTimeout(searchGoalTimer);
  filtersForm.reset();
  render();
  trackGoal("catalog_reset", { source: "reset_button" });
});
filterChips?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-clear-filter]");
  if (!button) return;
  const filter = button.dataset.clearFilter;
  if (filter === "q") window.clearTimeout(searchGoalTimer);
  filtersForm.elements[filter].value = "";
  render();
  trackGoal("catalog_filter", { action: "remove", filter });
});

async function loadCatalog() {
  try {
    const [worksResponse, i18nResponse] = await Promise.all([
      fetch("/data/works.json"),
      fetch("/data/i18n.json"),
    ]);
    if (!worksResponse.ok) throw new Error(`Works HTTP ${worksResponse.status}`);
    if (!i18nResponse.ok) throw new Error(`I18n HTTP ${i18nResponse.status}`);
    const [worksData, i18n] = await Promise.all([worksResponse.json(), i18nResponse.json()]);
    works = worksData.works || [];
    ui = i18n[LANGUAGE].catalog;
    catalogTotal.textContent = String(works.length).padStart(2, "0");
    setupFilterOptions();
    restoreFiltersFromUrl();
    render();
  } catch (error) {
    const fallback = ui || {
      loadError: "Не удалось загрузить каталог. Обновите страницу или попробуйте позже.",
      temporarilyUnavailable: "Каталог временно недоступен",
    };
    catalogStatus.hidden = false;
    catalogStatus.textContent = fallback.loadError;
    resultsSummary.textContent = fallback.temporarilyUnavailable;
    console.error("Catalog loading error", error);
  }
}

loadCatalog();
