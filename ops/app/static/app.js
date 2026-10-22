"use strict";

const CONFIRM_WINDOW_MS = 4000;
const STATUS_MARK = { pass: "✅", warn: "⚠️", fail: "❌", error: "❓" };

const app = { overview: null, selected: null, definitions: {}, report: null, editing: null, running: false };

// ── 공통 유틸 ──────────────────────────────────────────
const $ = (id) => document.getElementById(id);

function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
    else if (key === "class") el.className = value;
    else if (value !== undefined && value !== null && value !== false) el.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child !== null && child !== undefined) el.append(child);
  }
  return el;
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function api(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(payload.detail) ? payload.detail.map((d) => d.msg).join(", ") : payload.detail;
    throw new ApiError(detail || t("err.request", { status: response.status }), response.status);
  }
  return payload;
}

let toastTimer;
function toast(message, isError = false) {
  const el = $("toast");
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), isError ? 7000 : 3500);
}

function confirmClick(button, task) {
  if (button.dataset.armed) {
    delete button.dataset.armed;
    button.classList.remove("confirming");
    button.textContent = button.dataset.label;
    return task().catch((error) => toast(error.message, true));
  }
  button.dataset.label = button.textContent;
  button.dataset.armed = "1";
  button.classList.add("confirming");
  button.textContent = button.dataset.confirm;
  setTimeout(() => {
    if (!button.dataset.armed) return;
    delete button.dataset.armed;
    button.classList.remove("confirming");
    button.textContent = button.dataset.label;
  }, CONFIRM_WINDOW_MS);
  return null;
}

const formatTime = (iso) => new Date(iso).toLocaleString(i18n.lang === "ko" ? "ko-KR" : "en-US");

// ── 데이터 ──────────────────────────────────────────
async function loadOverview() {
  app.overview = await api("GET", "/api/overview");
  $("cluster-domain").textContent = app.overview.domain;
  const ids = Object.keys(app.overview.workshops);
  if (!app.selected || !ids.includes(app.selected)) {
    app.selected = ids.includes(app.overview.deployed) ? app.overview.deployed : ids[0] || null;
  }
  renderWorkshops();
  if (app.selected) await selectWorkshop(app.selected);
  else renderRunArea();
}

async function selectWorkshop(wid) {
  app.selected = wid;
  app.editing = null;
  $("def-editor").hidden = true;
  renderWorkshops();
  await Promise.all([loadDefinitions(), loadReport()]);
}

async function loadDefinitions() {
  const contents = app.overview.workshops[app.selected]?.contents || [];
  const entries = await Promise.all(contents.map((name) =>
    api("GET", `/api/definitions/${name}`).catch((error) => ({ name, source: "error", error: error.message, text: "" }))));
  app.definitions = Object.fromEntries(entries.map((d) => [d.name, d]));
  renderDefinitions();
}

async function loadReport() {
  try {
    app.report = await api("GET", `/api/preflight/${app.selected}`);
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) toast(error.message, true);
    app.report = null;
  }
  renderRunArea();
}

// ── 렌더링 ──────────────────────────────────────────
function renderWorkshops() {
  const { workshops, deployed, lastRuns } = app.overview;
  const items = Object.entries(workshops).map(([id, w]) => {
    const last = lastRuns[id];
    const end = Number(w.userStart) + Number(w.userCount) - 1;
    return h("li", {}, h("button", {
      type: "button", class: "pick", "aria-pressed": String(app.selected === id),
      onclick: () => selectWorkshop(id).catch((e) => toast(e.message, true)),
    },
    h("span", { class: "title" }, w.title, id === deployed ? h("span", { class: "badge-live" }, `● ${t("ws.live")}`) : null),
    h("span", { class: "meta" }, `${id} · ${t("ws.users", { start: w.userStart, end, count: w.contents.length })}`),
    last ? h("span", { class: "meta" }, ` · ${t("ws.lastRun", { when: formatTime(last.at) })}`) : null));
  });
  $("workshop-list").replaceChildren(...(items.length ? items : [h("li", {}, h("p", { class: "empty" }, t("ws.empty")))]));
}

function sourceOf(def) {
  return def.error ? "error" : def.source;
}

function renderDefinitions() {
  const rows = Object.values(app.definitions).map((def) => h("li", {},
    h("div", { class: "def-row" },
      h("span", { class: "label" }, def.name),
      h("span", { class: "source", "data-source": sourceOf(def), title: def.error || "" }, t(`def.source.${sourceOf(def)}`)),
      h("button", { type: "button", class: "btn btn-text", onclick: () => openEditor(def.name) }, t("def.edit")))));
  $("definition-list").replaceChildren(...rows);
}

function openEditor(name) {
  const def = app.definitions[name];
  app.editing = name;
  const form = $("def-editor");
  form.hidden = false;
  $("def-editor-title").textContent = t("def.editing", { name });
  form.elements.text.value = def.text || t("def.template");
  $("def-error").textContent = def.error || "";
  $("btn-def-reset").hidden = def.source !== "override";
  $("btn-def-reset").dataset.confirm = t("confirm.reset");
  form.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function verdictOf(summary) {
  if (summary.fail) return h("p", { class: "verdict", "data-v": "blocked" }, t("verdict.blocked", { count: summary.fail }));
  const attention = summary.warn + summary.error;
  if (attention) return h("p", { class: "verdict", "data-v": "caution" }, t("verdict.caution", { count: attention }));
  return h("p", { class: "verdict", "data-v": "ready" }, t("verdict.ready"));
}

function resultRow(r) {
  return h("li", { class: "result", "data-status": r.status },
    h("span", { class: "mark", title: t(`status.${r.status}`), "aria-label": t(`status.${r.status}`) }, STATUS_MARK[r.status]),
    h("span", { class: "name" }, r.name),
    h("span", { class: "observed" }, r.observed),
    r.status !== "pass" && r.fix ? h("span", { class: "fix" }, `${t("fix.label")}: ${r.fix}`) : null);
}

function renderRunArea() {
  const area = $("run-area");
  if (!app.selected) {
    area.replaceChildren(h("p", { class: "placeholder-card" }, t("run.pick")));
    return;
  }
  const runButton = h("button", {
    type: "button", class: "btn btn-red", disabled: app.running,
    onclick: () => runPreflight(),
  }, app.running ? t("run.running") : t("run.button"));
  const report = app.report;
  const bar = h("div", { class: "run-bar" },
    runButton,
    h("span", { class: "when" }, report ? t("run.at", { when: formatTime(report.at) }) : ""),
    h("span", { class: "spacer" }),
    report ? h("a", { class: "btn btn-ghost", href: `/api/preflight/${app.selected}/report.md`, download: "" }, t("run.report")) : null);
  if (!report) {
    area.replaceChildren(bar, h("p", { class: "placeholder-card" }, t("run.never")));
    return;
  }
  const s = report.summary;
  const summary = h("div", { class: "summary" },
    ...["pass", "warn", "fail", "error"].map((key) => h("span", { "data-s": key }, `${STATUS_MARK[key]} ${s[key]}`)));
  const scopes = ["common", ...report.contents];
  const groups = scopes.map((scope) => {
    const rows = report.results.filter((r) => r.scope === scope);
    if (!rows.length) return null;
    return h("div", { class: "result-group" },
      h("h3", {}, scope === "common" ? t("group.common") : scope),
      h("ul", { class: "result-list" }, rows.map(resultRow)));
  });
  const missing = report.definitions.filter((d) => d.source === "none").map((d) => d.name);
  const note = missing.length ? h("p", { class: "empty" }, t("noDefinition", { names: missing.join(", ") })) : null;
  // replaceChildren 은 null 을 "null" 글자로 넣으므로 걸러 낸다
  area.replaceChildren(...[bar, verdictOf(s), summary, h("div", { style: "height:1rem" }), ...groups, note].filter(Boolean));
}

// ── 동작 ──────────────────────────────────────────
async function runPreflight() {
  if (app.running) return;
  app.running = true;
  renderRunArea();
  try {
    app.report = await api("POST", `/api/preflight/${app.selected}`);
    app.overview.lastRuns[app.selected] = { at: app.report.at, summary: app.report.summary };
    renderWorkshops();
  } catch (error) {
    toast(error.message, true);
  } finally {
    app.running = false;
    renderRunArea();
  }
}

function bindEvents() {
  const form = $("def-editor");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = app.editing;
    try {
      await api("PUT", `/api/definitions/${name}`, { text: form.elements.text.value });
      $("def-error").textContent = "";
      toast(t("toast.saved"));
      await loadDefinitions();
      openEditor(name);
    } catch (error) {
      $("def-error").textContent = error.message;
    }
  });
  $("btn-def-reset").addEventListener("click", (event) => confirmClick(event.currentTarget, async () => {
    await api("DELETE", `/api/definitions/${app.editing}`);
    toast(t("toast.reset"));
    await loadDefinitions();
    form.hidden = true;
  }));
  $("btn-def-close").addEventListener("click", () => { form.hidden = true; app.editing = null; });
  document.querySelectorAll("[data-lang]").forEach((button) =>
    button.addEventListener("click", () => {
      setLang(button.dataset.lang);
      if (!app.overview) return;
      renderWorkshops();
      renderDefinitions();
      renderRunArea();
      if (app.editing) $("def-editor-title").textContent = t("def.editing", { name: app.editing });
    }));
}

// ── 다른 앱으로 전환 (설치되어 있을 때만 링크를 보인다) ─────────────
async function loadAppSwitch() {
  const links = await api("GET", "/api/links").catch(() => ({}));
  if (!links.editor) return;
  const link = $("app-switch");
  link.href = links.editor;
  link.hidden = false;
}

applyStaticText();
bindEvents();
loadOverview().catch((error) => toast(error.message, true));
loadAppSwitch();
