"use strict";

const POLL_INTERVAL_MS = 4000;
const CONFIRM_WINDOW_MS = 4000;
const NEW_WORKSHOP = "__new";
const app = { data: null, status: null, selected: NEW_WORKSHOP, draft: emptyDraft() };

function emptyDraft() {
  return { id: "", title: "", contents: [], userStart: 1, userCount: 20, isNew: true };
}

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

async function api(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((d) => d.msg).join(", ")
      : payload.detail;
    throw new Error(detail || t("err.request", { status: response.status }));
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

async function busy(button, task) {
  button.disabled = true;
  try {
    return await task();
  } catch (error) {
    toast(error.message, true);
    return null;
  } finally {
    button.disabled = false;
  }
}

/** 위험한 동작은 버튼을 두 번 눌러야 실행된다. */
function confirmClick(button, task) {
  if (button.dataset.armed) {
    delete button.dataset.armed;
    button.classList.remove("confirming");
    button.textContent = button.dataset.label;
    return busy(button, task);
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

function parseLines(text, separator) {
  return text.split("\n").map((line) => line.trim()).filter(Boolean).map((line) => {
    const index = line.indexOf(separator);
    if (index < 0) throw new Error(t("err.badLine", { line }));
    return [line.slice(0, index).trim(), line.slice(index + separator.length).trim()];
  });
}

// ── 데이터 로드 ──────────────────────────────────────────
async function loadState() {
  app.data = await api("GET", "/api/state");
  if (app.selected !== NEW_WORKSHOP && !app.data.workshops[app.selected]) selectWorkshop(NEW_WORKSHOP);
  renderAll();
}

function selectWorkshop(id) {
  app.selected = id;
  const saved = app.data?.workshops[id];
  app.draft = saved ? { ...saved, contents: [...saved.contents], id, isNew: false } : emptyDraft();
}

// ── 렌더링 ──────────────────────────────────────────
function renderAll() {
  renderHeader();
  renderCatalog();
  renderWorkshopTabs();
  renderComposer();
  renderRunMeta();
}

function renderHeader() {
  $("cluster-domain").textContent = app.data.cluster?.domain || "—";
  const deployed = app.data.deploy;
  const badge = $("deployed-badge");
  badge.textContent = deployed ? `${deployed.title} (${deployed.workshop})` : t("deployed.none");
  badge.classList.toggle("live", Boolean(deployed));
}

function renderCatalog() {
  const entries = Object.entries(app.data.catalog);
  const list = $("catalog-list");
  list.replaceChildren(...(entries.length ? entries.map(([name, item]) => {
    const remove = h("button", { type: "button", class: "btn btn-text danger", "data-confirm": t("confirm.delete") }, t("btn.delete"));
    remove.addEventListener("click", () => confirmClick(remove, async () => {
      await api("DELETE", `/api/catalog/${name}`);
      toast(t("toast.catalogDeleted", { name }));
      await loadState();
    }));
    return h("li", { class: "catalog-item" },
      h("header", {}, h("span", { class: "name" }, name), remove),
      h("p", { class: "title" }, item.title),
      h("p", { class: "repo" }, `${item.repoUrl} @ ${item.repoRef} · ${item.commit}`));
  }) : [h("li", {}, h("p", { class: "empty" }, t("catalog.empty")))]));
}

function renderWorkshopTabs() {
  const deployedId = app.data.deploy?.workshop;
  const tabs = Object.entries(app.data.workshops).map(([id, w]) =>
    h("button", {
      type: "button", class: "workshop-tab", role: "tab",
      "aria-selected": String(app.selected === id),
      onclick: () => { selectWorkshop(id); renderAll(); },
    }, w.title, id === deployedId ? h("span", { class: "live-dot", title: t("composer.live") }) : null));
  tabs.push(h("button", {
    type: "button", class: "workshop-tab new", role: "tab",
    "aria-selected": String(app.selected === NEW_WORKSHOP),
    onclick: () => { selectWorkshop(NEW_WORKSHOP); renderAll(); },
  }, t("composer.new")));
  $("workshop-tabs").replaceChildren(...tabs);
}

function renderComposer() {
  // form.title / form.id 는 폼 자체 속성이므로 elements 로 접근한다
  const fields = $("workshop-form").elements;
  const { draft } = app;
  fields.title.value = draft.title;
  fields.id.value = draft.id;
  fields.id.disabled = !draft.isNew;
  fields.userStart.value = draft.userStart;
  fields.userCount.value = draft.userCount;
  $("btn-delete-workshop").hidden = draft.isNew;
  renderUserRange();
  renderContentLists();
}

function renderUserRange() {
  const { userStart, userCount } = app.draft;
  const last = Number(userStart) + Number(userCount) - 1;
  $("user-range").textContent = `→ user${userStart} ~ user${last} · showroom-showroom-userN.${app.data.cluster?.domain || ""}`;
}

function moveContent(index, offset) {
  const contents = [...app.draft.contents];
  const [item] = contents.splice(index, 1);
  contents.splice(index + offset, 0, item);
  app.draft = { ...app.draft, contents };
  renderContentLists();
}

function renderContentLists() {
  const { catalog } = app.data;
  const { contents } = app.draft;
  $("selected-count").textContent = contents.length;
  $("selected-list").replaceChildren(...(contents.length ? contents.map((name, index) =>
    h("li", {},
      h("span", { class: "label" }, catalog[name]?.title || name, h("small", {}, name)),
      h("button", { type: "button", class: "icon-btn", title: t("action.up"), disabled: index === 0, onclick: () => moveContent(index, -1) }, "↑"),
      h("button", { type: "button", class: "icon-btn", title: t("action.down"), disabled: index === contents.length - 1, onclick: () => moveContent(index, 1) }, "↓"),
      h("button", {
        type: "button", class: "icon-btn", title: t("action.remove"),
        onclick: () => { app.draft = { ...app.draft, contents: contents.filter((c) => c !== name) }; renderContentLists(); },
      }, "✕"))
  ) : [h("li", { class: "empty-row" }, h("p", { class: "empty" }, t("ws.selectedEmpty")))]));

  const available = Object.keys(catalog).filter((name) => !contents.includes(name));
  $("available-list").replaceChildren(...(available.length ? available.map((name) =>
    h("li", {},
      h("span", { class: "label" }, catalog[name].title, h("small", {}, name)),
      h("button", {
        type: "button", class: "icon-btn", title: t("action.add"),
        onclick: () => { app.draft = { ...app.draft, contents: [...contents, name] }; renderContentLists(); },
      }, "+"))
  ) : [h("li", { class: "empty-row" }, h("p", { class: "empty" }, t("ws.availableEmpty")))]));
}

function renderRunMeta() {
  const describe = (record) => record
    ? `${record.title} · ${record.contents.join(", ")} · ${new Date(record.at).toLocaleString(i18n.lang === "ko" ? "ko-KR" : "en-US")}`
    : null;
  $("preview-meta").textContent = describe(app.data.preview) || t("preview.none");
  $("deploy-meta").textContent = describe(app.data.deploy) || t("deploy.none");
}

function statusItem(item) {
  const label = item.url ? h("a", { href: item.url, target: "_blank", rel: "noopener" }, item.user) : h("span", {}, item.user);
  const failed = item.phase === "failed";
  const chip = h("button", {
    type: "button", class: "chip", "data-phase": item.phase,
    title: failed && item.step ? t(`stepFailed.${item.step}`) : undefined,
    onclick: failed ? () => showLogs(item.namespace) : undefined,
  }, item.phase === "building" && item.step ? t(`step.${item.step}`) : t(`phase.${item.phase}`));
  return h("li", { class: "status-item" }, label, chip);
}

function renderStatus(status) {
  app.status = status;
  $("preview-status").replaceChildren(...status.preview.map(statusItem));
  $("deploy-status").replaceChildren(...status.deploy.map(statusItem));
  const ready = status.deploy.filter((s) => s.phase === "ready").length;
  const failed = status.deploy.filter((s) => s.phase === "failed").length;
  $("deploy-tally").textContent = status.deploy.length
    ? t("tally", { ready, total: status.deploy.length }) + (failed ? t("tally.failed", { failed }) : "")
    : "";
}

async function showLogs(namespace) {
  try {
    const logs = await api("GET", `/api/logs/${namespace}`);
    $("log-title").textContent = t("log.titleFor", { ns: namespace });
    $("log-body").textContent = Object.entries(logs).map(([step, text]) => `── ${step} ──\n${text}`).join("\n\n");
    $("log-card").hidden = false;
    $("log-card").scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    toast(error.message, true);
  }
}

async function pollStatus() {
  try {
    renderStatus(await api("GET", "/api/status"));
  } catch (error) {
    console.warn("status polling failed", error);
  } finally {
    setTimeout(pollStatus, POLL_INTERVAL_MS);
  }
}

// ── 동작 ──────────────────────────────────────────
async function saveDraft() {
  const form = $("workshop-form");
  if (!form.reportValidity()) throw new Error(t("err.invalid"));
  if (!app.draft.contents.length) throw new Error(t("err.needContent"));
  const { id, title, contents, userStart, userCount } = app.draft;
  await api("PUT", `/api/workshops/${id}`, { title, contents, userStart: Number(userStart), userCount: Number(userCount) });
  app.selected = id;
  await loadState();
  return id;
}

function bindEvents() {
  const form = $("workshop-form");
  form.addEventListener("input", (event) => {
    const { name, value } = event.target;
    if (["title", "id", "userStart", "userCount"].includes(name)) {
      app.draft = { ...app.draft, [name]: value };
      if (name.startsWith("user")) renderUserRange();
    }
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    busy(form.querySelector("[type=submit]"), async () => { await saveDraft(); toast(t("toast.saved")); });
  });
  $("btn-preview").addEventListener("click", (event) => busy(event.currentTarget, async () => {
    const id = await saveDraft();
    await api("POST", `/api/workshops/${id}/preview`);
    toast(t("toast.previewStarted"));
    await loadState();
  }));
  $("btn-deploy").addEventListener("click", (event) => confirmClick(event.currentTarget, async () => {
    const id = await saveDraft();
    const result = await api("POST", `/api/workshops/${id}/deploy`);
    toast(t("toast.deployed", { count: result.namespaces.length })
      + (result.removed.length ? t("toast.cleaned", { count: result.removed.length }) : ""));
    await loadState();
  }));
  $("btn-delete-workshop").addEventListener("click", (event) => confirmClick(event.currentTarget, async () => {
    await api("DELETE", `/api/workshops/${app.draft.id}`);
    toast(t("toast.workshopDeleted"));
    selectWorkshop(NEW_WORKSHOP);
    await loadState();
  }));
  document.querySelectorAll("[data-role-remove]").forEach((button) =>
    button.addEventListener("click", () => confirmClick(button, async () => {
      const result = await api("DELETE", `/api/roles/${button.dataset.roleRemove}`);
      toast(t("toast.removed", { count: result.removed.length }));
      await loadState();
    })));
  document.querySelectorAll("[data-role-restart]").forEach((button) =>
    button.addEventListener("click", () => confirmClick(button, async () => {
      const result = await api("POST", `/api/roles/${button.dataset.roleRestart}/restart`);
      toast(t("toast.restarted", { count: result.restarted.length }));
    })));
  $("btn-close-log").addEventListener("click", () => { $("log-card").hidden = true; });
  document.querySelectorAll("[data-lang]").forEach((button) =>
    button.addEventListener("click", () => {
      setLang(button.dataset.lang);
      if (app.data) renderAll();
      if (app.status) renderStatus(app.status);
    }));

  const catalogForm = $("catalog-form");
  catalogForm.addEventListener("submit", (event) => {
    event.preventDefault();
    busy(catalogForm.querySelector("[type=submit]"), async () => {
      const f = catalogForm.elements;
      const body = {
        name: f.name.value.trim(),
        repoUrl: f.repoUrl.value.trim(),
        repoRef: f.repoRef.value.trim(),
        startPath: f.startPath.value.trim(),
        title: f.title.value.trim() || null,
        tabs: parseLines(f.tabs.value, "|").map(([name, url]) => ({ name, url, external: true })),
        attributes: Object.fromEntries(parseLines(f.attributes.value, "=")),
      };
      toast(t("toast.checking"));
      const result = await api("POST", "/api/catalog", body);
      toast(t("toast.registered", { title: result.title, commit: result.commit }));
      catalogForm.reset();
      await loadState();
    });
  });
}

// ── 다른 앱으로 전환 (설치되어 있을 때만 링크를 보인다) ─────────────
async function loadAppSwitch() {
  const links = await api("GET", "/api/links").catch(() => ({}));
  if (!links.opsHub) return;
  const link = $("app-switch");
  link.href = links.opsHub;
  link.hidden = false;
}

applyStaticText();
bindEvents();
loadState().catch((error) => toast(error.message, true));
pollStatus();
loadAppSwitch();
