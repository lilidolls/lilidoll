const header = document.querySelector("[data-header]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const menu = document.querySelector("[data-menu]");
const languageToggle = document.querySelector("[data-language]");
const dialog = document.querySelector("[data-dialog]");

const works = {
  otsuyu: {
    title: "Оцую",
    series: "Мифы Японии",
    lead: "Девушка, которая стала мостом между живыми и теми, кого нельзя забывать.",
    story:
      "Оцую появилась осенью, окутанная туманом и ароматом красной паучьей лилии. Когда деревню охватило забвение, она рассыпалась на алые искры и вернула людям имена их предков.",
    year: "2025–2026",
    material: "Уточняется",
    status: "Выставочный маршрут",
    image: "assets/images/telegram-web/lilimillerdoll/232.webp",
    imagePosition: "center top",
  },
  lucrezia: {
    title: "Лукреция Борджиа",
    series: "Женщины Возрождения",
    lead: "Исторический образ, освобождённый от многовековых слухов и демонизации.",
    story:
      "В 2026 году Lili вернулась к кукле и приблизила её черты к портрету, который исследователи связывают с Лукрецией. Работа показывает персонажа не легендой, а живой женщиной своего времени.",
    year: "2023 / 2026",
    material: "Фарфор",
    status: "Требует уточнения",
    image: "assets/images/telegram-web/lilimillerdoll/221.webp",
  },
  caterina: {
    title: "Катерина Сфорца",
    series: "Женщины Возрождения",
    lead: "Львица Форли — умная, образованная и безжалостная героиня своей эпохи.",
    story:
      "Образ построен на столкновении придворной красоты и стального характера женщины, пережившей заговоры, плен и гибель близких.",
    year: "2023",
    material: "Фарфор",
    status: "Частная коллекция",
    image: "assets/images/telegram-web/lilimillerdoll/90.webp",
    imagePosition: "center top",
  },
  contessina: {
    title: "Контессина де Барди",
    series: "Женщины Возрождения",
    lead: "Флорентийская аристократка, меценат и хранительница влияния семьи Медичи.",
    story:
      "Не имея достоверного портрета, художник собирает образ из исторических свидетельств: интеллекта, элегантности и тихой политической силы Контессины.",
    year: "2023",
    material: "Фарфор",
    status: "Частная коллекция",
    image: "assets/images/telegram-web/lilimillerdoll/78.webp",
  },
};

const translations = {
  en: {
    navCatalog: "Catalogue", navWorks: "Works", navStories: "Stories", navArtist: "Artist", navExhibitions: "Exhibitions", navContact: "Contact",
    heroEyebrow: "Saint Petersburg · since 2017",
    heroStatement: "Porcelain art dolls.<br>Stories taking shape.",
    viewCollection: "View the collection <span aria-hidden='true'>↘</span>",
    manifesto: "Every work begins with an image — historical, mythological, or barely perceptible. Porcelain preserves its fragility and gives it a life longer than our own.",
    selectedLabel: "Selected · 2022–2026", selectedTitle: "Characters and their worlds",
    selectedIntro: "Not a catalogue of objects, but an archive of characters. Every doll keeps her story, even after entering a private collection.",
    mythsJapan: "Myths of Japan", renaissance: "Women of the Renaissance", porcelain2023: "Porcelain · 2023 / 2026",
    privateCollection: "Porcelain · private collection", allWorks: "Open full catalogue <span aria-hidden='true'>→</span>",
    storyLabel: "Featured story", storyTitle: "Soul of the red lily", storyLead: "Otsuyu became a bridge between the living and those who must not be forgotten.",
    storyBody: "On the autumn equinox, her body scattered into thousands of scarlet sparks. Red spider lilies grew wherever they touched the earth, and forgotten ancestral names returned to the people.",
    year: "Year", series: "Series", status: "Status", exhibitionRoute: "Exhibition route", readOriginal: "Read the original story <span aria-hidden='true'>↗</span>",
    materialLabel: "Material and process", materialTitle: "Strength<br>that holds light", materialBody: "Porcelain passes through fire at around 1300 °C. It remains fragile, yet gains whiteness, translucency and the ability to endure for centuries.",
    sculpture: "Sculpture", sculptureText: "The character is born in volume: from body proportions to the expression of each finger.",
    fire: "Fire", fireText: "Layered painting is fixed through repeated kiln firings.", character: "Character", characterText: "Costume, pose and gaze continue the character’s story.",
    artistLabel: "Artist", artistLead: "“I am a doll artist. I began mastering this profession in January 2017 and have been doing what I love ever since.”",
    artistTextOne: "Lili creates ball-jointed dolls, historical heroines and mythological characters. Her works are one of a kind and continue their lives in private collections.",
    artistTextTwo: "At the heart of her practice is the doll’s ability to hold memory, character and contradiction: strength and fragility, light and darkness, past and present.",
    requestCv: "Request CV <span aria-hidden='true'>→</span>", exhibitionsLabel: "Exhibitions and events", exhibitionsTitle: "From the studio into the world",
    event2026: "Doll Ball in Saint Petersburg", event2025: "Otsuyu exhibition route", route2025: "Moscow → Shanghai", event2023: "Historical collection premiere", premiere2023: "Doll Ball · Saint Petersburg",
    contactLabel: "For collectors and galleries", contactTitle: "Find your story", contactBody: "Ask the artist directly about available works, exhibitions and possible collaborations.", writeTelegram: "Write on Telegram", backTop: "Back to top ↑",
  },
};

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

function fillDialog(work) {
  const dialogImage = dialog.querySelector("[data-dialog-image]");
  dialogImage.src = work.image;
  dialogImage.alt = work.title;
  dialogImage.style.objectPosition = work.imagePosition || "center";
  dialog.querySelector("[data-dialog-series]").textContent = work.series;
  dialog.querySelector("[data-dialog-title]").textContent = work.title;
  dialog.querySelector("[data-dialog-lead]").textContent = work.lead;
  dialog.querySelector("[data-dialog-story]").textContent = work.story;
  dialog.querySelector("[data-dialog-year]").textContent = work.year;
  dialog.querySelector("[data-dialog-material]").textContent = work.material;
  dialog.querySelector("[data-dialog-status]").textContent = work.status;
}

document.querySelectorAll("[data-work]").forEach((card) => {
  card.querySelector(".work-card__open")?.addEventListener("click", () => {
    fillDialog(works[card.dataset.work]);
    dialog.showModal();
  });
});

dialog.querySelector("[data-dialog-close]")?.addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
});

let currentLanguage = "ru";
languageToggle?.addEventListener("click", () => {
  currentLanguage = currentLanguage === "ru" ? "en" : "ru";
  document.documentElement.lang = currentLanguage;
  const labels = languageToggle.querySelectorAll("span:not(:nth-child(2))");
  labels[0].classList.toggle("is-active", currentLanguage === "ru");
  labels[1].classList.toggle("is-active", currentLanguage === "en");

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    if (!element.dataset.ru) element.dataset.ru = element.innerHTML;
    const translated = translations[currentLanguage]?.[element.dataset.i18n];
    element.innerHTML = translated ?? element.dataset.ru;
  });
});
