"use strict";

/** 콘텐츠 갤러리. app.js 의 h, api, t, toast, $, formatTime, viewHooks 를 사용한다. */
const gallery = { cards: null, filter: "all", loading: false };

async function loadGallery() {
  if (gallery.loading) return;
  gallery.loading = true;
  if (!gallery.cards) $("gallery-grid").replaceChildren(h("p", { class: "placeholder-card" }, t("gallery.loading")));
  try {
    gallery.cards = (await api("GET", "/api/gallery")).cards;
    renderGallery();
  } catch (error) {
    toast(error.message, true);
  } finally {
    gallery.loading = false;
  }
}

function repoLabel(url) {
  return url.replace(/^https:\/\/(www\.)?github\.com\//, "").replace(/\.git$/, "");
}

function readinessBadge(readiness) {
  const verdict = readiness?.verdict || "none";
  const title = readiness ? t("gallery.readinessAt", { workshop: readiness.workshop, when: formatTime(readiness.at) }) : "";
  return h("span", { class: "readiness", "data-v": verdict, title }, t(`gallery.readiness.${verdict}`));
}

function aboutMeta(about) {
  // 정해진 난이도(beginner 등)는 번역하고, 그 밖의 값은 그대로 보여 준다
  const levelKey = `gallery.level.${about.level}`;
  const level = MESSAGES.ko[levelKey] ? t(levelKey) : about.level;
  const items = [["⏱", about.duration], ["◆", level], ["👥", about.audience]].filter(([, text]) => text);
  return h("ul", { class: "card-meta" }, items.map(([icon, text]) => h("li", {}, h("span", { "aria-hidden": "true" }, icon), text)));
}

function cardStats(card) {
  const required = card.requirements.filter((r) => r.severity === "required").length;
  const modules = [...new Set(card.checkpoints.map((c) => c.module))];
  return h("dl", { class: "card-stats" },
    h("div", {}, h("dt", {}, t("gallery.requirements", { count: card.requirements.length })),
      h("dd", {}, t("gallery.requiredRecommended", { required, recommended: card.requirements.length - required }))),
    h("div", {}, h("dt", {}, t("gallery.checkpoints", { count: card.checkpoints.length })),
      h("dd", {}, modules.length ? t("gallery.modules", { list: modules.join(", ") }) : "—")));
}

function cardDetails(card) {
  if (!card.requirements.length && !card.checkpoints.length) return null;
  return h("details", { class: "card-details" },
    h("summary", {}, t("gallery.details")),
    card.requirements.length ? h("ul", { class: "req-list" }, card.requirements.map((r) =>
      h("li", { "data-severity": r.severity }, h("span", { class: "sev" }, t(`gallery.${r.severity}`)), r.name))) : null,
    card.checkpoints.length ? h("ol", { class: "cp-list" }, card.checkpoints.map((c) =>
      h("li", {}, h("span", { class: "mod" }, `M${c.module}`), c.name))) : null);
}

function galleryCard(card) {
  const live = card.workshops.some((w) => w.deployed);
  return h("article", { class: `g-card${live ? " is-live" : ""}`, "aria-labelledby": `g-${card.name}` },
    h("header", { class: "g-card-head" },
      h("span", { class: "g-name" }, card.name),
      h("span", { class: "source", "data-source": card.error ? "error" : card.source, title: card.error || "" },
        t(`def.source.${card.error ? "error" : card.source}`)),
      readinessBadge(card.readiness)),
    h("h3", { id: `g-${card.name}`, class: "g-title" }, card.title),
    card.about?.summary ? h("p", { class: "g-summary" }, card.about.summary)
      : h("p", { class: "g-summary muted" }, t("gallery.noDefinition")),
    card.about ? aboutMeta(card.about) : null,
    card.about ? cardStats(card) : null,
    h("div", { class: "g-workshops" },
      h("span", { class: "label" }, t("gallery.usedIn")),
      card.workshops.length ? card.workshops.map((w) => h("span", { class: `chip${w.deployed ? " live" : ""}` },
        w.deployed ? `● ${w.title}` : w.title)) : h("span", { class: "muted" }, t("gallery.notUsed"))),
    cardDetails(card),
    h("footer", { class: "g-foot" },
      h("a", { href: card.repoUrl.replace(/\.git$/, ""), target: "_blank", rel: "noopener" }, `${repoLabel(card.repoUrl)} ↗`),
      h("code", {}, `@${card.repoRef}${card.commit ? ` · ${card.commit.slice(0, 7)}` : ""}`)));
}

function renderGallery() {
  if (!gallery.cards) return;
  document.querySelectorAll("[data-gallery-filter]").forEach((button) =>
    button.setAttribute("aria-pressed", String(button.dataset.galleryFilter === gallery.filter)));
  const cards = gallery.cards.filter((card) => gallery.filter === "all" || card.workshops.some((w) => w.deployed));
  // 카드가 3개 이상일 때만 배포 중인 첫 카드를 넓게 보여 준다
  $("gallery-grid").classList.toggle("has-feature", cards.length >= 3);
  $("gallery-grid").replaceChildren(...(cards.length ? cards.map(galleryCard)
    : [h("p", { class: "placeholder-card" }, t("gallery.empty"))]));
}

document.querySelectorAll("[data-gallery-filter]").forEach((button) =>
  button.addEventListener("click", () => { gallery.filter = button.dataset.galleryFilter; renderGallery(); }));

viewHooks.push({ view: "gallery", onShow: loadGallery, onLang: renderGallery });
