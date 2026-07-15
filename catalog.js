const catalogRoot = document.querySelector("[data-catalog-grid]");
const catalogStatus = document.querySelector("[data-catalog-status]");
const resultsSummary = document.querySelector("[data-results-summary]");
const catalogTotal = document.querySelector("[data-catalog-total]");
const filtersForm = document.querySelector("[data-catalog-filters]");
const filterChips = document.querySelector("[data-filter-chips]");
const resetButton = document.querySelector("[data-filter-reset]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const menu = document.querySelector("[data-menu]");

const statusLabels = {
  exhibition: "На выставке",
  private: "Частная коллекция",
  archive: "Архив",
  available: "Доступна",
};

let works = [];

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

function localized(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return value.ru || value.en || "";
}

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
    .sort((a, b) => a.label.localeCompare(b.label, "ru"));

  const series = uniqueBy(
    works.map((work) => ({ series: work.series, label: localized(work.seriesLabel) })),
    "series"
  )
    .map((item) => ({ value: item.series, label: item.label }))
    .sort((a, b) => a.label.localeCompare(b.label, "ru"));

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
  const query = state.q.toLocaleLowerCase("ru");
  const filtered = works.filter((work) => {
    const searchable = [
      localized(work.title),
      localized(work.excerpt),
      localized(work.story),
      localized(work.seriesLabel),
      localized(work.directionLabel),
    ]
      .join(" ")
      .toLocaleLowerCase("ru");

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
    name: (a, b) => localized(a.title).localeCompare(localized(b.title), "ru"),
  };
  return filtered.sort(sorters[state.sort] || sorters.curated);
}

function createCard(work, index) {
  const article = document.createElement("article");
  article.className = "catalog-card";

  const link = document.createElement("a");
  link.className = "catalog-card__link";
  link.href = `work.html?slug=${encodeURIComponent(work.slug)}`;
  link.setAttribute("aria-label", `${localized(work.title)} — открыть работу`);

  const imageWrap = document.createElement("div");
  imageWrap.className = "catalog-card__image image-shell";
  const image = document.createElement("img");
  image.src = work.hero;
  image.alt = `${localized(work.title)} — авторская кукла Lili Miller`;
  image.loading = "lazy";
  image.decoding = "async";
  imageWrap.append(image);

  const status = document.createElement("span");
  status.className = `catalog-card__status catalog-card__status--${work.status}`;
  status.textContent = statusLabels[work.status] || work.status;
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
  open.textContent = "Смотреть ↗";
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
  if (name === "q") return `Поиск: ${value}`;
  const option = filtersForm.elements[name]?.selectedOptions?.[0];
  return option?.textContent || value;
}

function renderChips(state) {
  filterChips.replaceChildren();
  ["q", "direction", "series", "year", "status"].forEach((name) => {
    const value = state[name];
    if (!value) return;
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.clearFilter = name;
    button.textContent = `${selectedLabel(name, value)} ×`;
    button.setAttribute("aria-label", `Убрать фильтр: ${selectedLabel(name, value)}`);
    filterChips.append(button);
  });
}

function render() {
  const state = getState();
  const filtered = filterAndSort(state);
  const fragment = document.createDocumentFragment();
  filtered.forEach((work, index) => fragment.append(createCard(work, index)));
  catalogRoot.replaceChildren(fragment);

  const countLabel = filtered.length === 1 ? "работа" : filtered.length > 1 && filtered.length < 5 ? "работы" : "работ";
  resultsSummary.textContent = `Найдено: ${filtered.length} ${countLabel}`;
  catalogStatus.textContent = filtered.length ? "" : "По выбранным параметрам работ не найдено. Попробуйте изменить фильтры.";
  catalogStatus.hidden = Boolean(filtered.length);
  renderChips(state);
  updateUrl(state);
}

filtersForm?.addEventListener("input", render);
filtersForm?.addEventListener("change", render);
resetButton?.addEventListener("click", () => {
  filtersForm.reset();
  render();
});
filterChips?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-clear-filter]");
  if (!button) return;
  filtersForm.elements[button.dataset.clearFilter].value = "";
  render();
});

async function loadCatalog() {
  try {
    const response = await fetch("data/works.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    works = data.works || [];
    catalogTotal.textContent = String(works.length).padStart(2, "0");
    setupFilterOptions();
    restoreFiltersFromUrl();
    render();
  } catch (error) {
    catalogStatus.hidden = false;
    catalogStatus.textContent = "Не удалось загрузить каталог. Обновите страницу или попробуйте позже.";
    resultsSummary.textContent = "Каталог временно недоступен";
    console.error("Catalog loading error", error);
  }
}

loadCatalog();
