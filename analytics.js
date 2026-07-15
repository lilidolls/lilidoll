(() => {
  const COUNTER_ID = 110756646;

  function reachGoal(target, params = {}) {
    if (!target || typeof window.ym !== "function") return false;

    window.ym(COUNTER_ID, "reachGoal", target, {
      language: document.documentElement.lang,
      page_path: window.location.pathname,
      ...params,
    });
    return true;
  }

  function linkSource(link) {
    if (link.closest(".site-header")) return "header";
    if (link.closest(".inner-footer, .site-footer")) return "footer";
    if (link.closest(".catalog-card")) return "catalog";
    if (link.closest(".related-card")) return "related";
    if (link.closest(".work-sources")) return "work_sources";
    if (link.closest(".contact")) return "contact";
    return "content";
  }

  function inferredLinkGoal(link) {
    const source = linkSource(link);
    const languageLink = link.closest(".language-toggle a");
    if (languageLink) {
      return {
        target: "language_change",
        params: {
          source,
          target_language: languageLink.getAttribute("lang") || "",
        },
      };
    }

    let url;
    try {
      url = new URL(link.href, window.location.href);
    } catch {
      return null;
    }

    if (url.hostname === "t.me") {
      const path = url.pathname.replace(/^\/+|\/+$/g, "");
      if (path === "lilimiller") {
        return { target: "contact_telegram", params: { source } };
      }
      if (/^lilimillerdoll\/\d+$/.test(path)) {
        return {
          target: "source_post",
          params: { source, post_id: path.split("/").pop() },
        };
      }
      if (path === "lilimillerdoll") {
        return { target: "telegram_channel", params: { source } };
      }
    }

    if (url.origin !== window.location.origin) return null;

    if (/\/catalog\.html$/.test(url.pathname) && url.pathname !== window.location.pathname) {
      return { target: "catalog_open", params: { source } };
    }

    const workMatch = url.pathname.match(/\/works\/([^/]+)\/?$/);
    if (workMatch && url.pathname !== window.location.pathname) {
      return {
        target: "work_open",
        params: { source, work_slug: workMatch[1] },
      };
    }

    return null;
  }

  document.addEventListener(
    "click",
    (event) => {
      if (!(event.target instanceof Element)) return;

      const marked = event.target.closest("[data-ym-goal]");
      if (marked) {
        reachGoal(marked.dataset.ymGoal, {
          source: marked.dataset.ymSource || "content",
          label: marked.dataset.ymLabel || "",
        });
        return;
      }

      const link = event.target.closest("a[href]");
      if (!link) return;
      const eventData = inferredLinkGoal(link);
      if (eventData) reachGoal(eventData.target, eventData.params);
    },
    { capture: true },
  );

  window.liliAnalytics = Object.freeze({
    counterId: COUNTER_ID,
    reachGoal,
  });
})();
