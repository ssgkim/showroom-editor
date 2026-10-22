"use strict";

/** 진행 현황. app.js 의 app, h, api, t, toast, $, formatTime, viewHooks 를 사용한다. */
const AUTO_REFRESH_MS = 60_000;
const CELL_MARK = { done: "✓", todo: "·", error: "?" };

const progress = { workshop: null, result: null, running: false, timer: null };

function progressWorkshops() {
  return app.overview ? Object.entries(app.overview.workshops) : [];
}

function renderProgressPicker() {
  const select = $("progress-workshop");
  const entries = progressWorkshops();
  if (!progress.workshop || !app.overview.workshops[progress.workshop]) {
    progress.workshop = app.overview?.deployed || entries[0]?.[0] || null;
  }
  select.replaceChildren(...entries.map(([id, w]) => h("option", { value: id },
    id === app.overview.deployed ? `● ${w.title} (${id})` : `${w.title} (${id})`)));
  select.value = progress.workshop || "";
}

async function showProgress() {
  if (!app.overview) await loadOverview().catch((error) => toast(error.message, true));
  renderProgressPicker();
  await loadLastProgress();
  scheduleAutoRefresh();
}

async function loadLastProgress() {
  if (!progress.workshop) return renderProgress();
  try {
    progress.result = await api("GET", `/api/progress/${progress.workshop}`);
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) toast(error.message, true);
    progress.result = null;
  }
  renderProgress();
}

async function runProgress() {
  if (progress.running || !progress.workshop) return;
  progress.running = true;
  renderRunButton();
  try {
    progress.result = await api("POST", `/api/progress/${progress.workshop}`);
  } catch (error) {
    toast(error.message, true);
  } finally {
    progress.running = false;
    renderRunButton();
    renderProgress();
  }
}

function scheduleAutoRefresh() {
  clearInterval(progress.timer);
  progress.timer = null;
  if ($("progress-auto").checked && currentView() === "progress") {
    progress.timer = setInterval(runProgress, AUTO_REFRESH_MS);
  }
}

function renderRunButton() {
  const button = $("btn-progress-run");
  button.disabled = progress.running || !progress.workshop;
  button.textContent = progress.running ? t("progress.running") : t("progress.run");
}

// ── 그리기 ──────────────────────────────────────────
function percent(part, whole) {
  return whole ? Math.round((part / whole) * 100) : 0;
}

function statTile(label, value, sub) {
  return h("div", { class: "stat" }, h("span", { class: "stat-label" }, label), h("strong", {}, value), sub ? h("span", { class: "stat-sub" }, sub) : null);
}

function summaryTiles(result) {
  const users = result.rows.length;
  const ready = result.rows.filter((row) => row.showroom === "ready").length;
  const cells = users * result.columns.length;
  const done = Object.values(result.totals).reduce((sum, n) => sum + n, 0);
  return h("div", { class: "stat-row" },
    statTile(t("progress.users"), String(users)),
    statTile(t("progress.showroomReady"), `${ready}/${users}`),
    statTile(t("progress.overall"), `${percent(done, cells)}%`, `${done}/${cells}`),
    h("div", { class: "overall-bar", role: "img", "aria-label": `${percent(done, cells)}%` },
      h("span", { style: `transform: scaleX(${cells ? done / cells : 0})` })));
}

function columnBars(result) {
  const users = result.rows.length;
  return h("ol", { class: "cp-bars" }, result.columns.map((column) => {
    const done = result.totals[column.id];
    return h("li", {},
      h("span", { class: "cp-label" }, h("span", { class: "mod" }, `${column.content} · M${column.module}`), column.name),
      h("span", { class: "bar" }, h("span", { style: `transform: scaleX(${users ? done / users : 0})` })),
      h("span", { class: "cp-count" }, `${done}/${users}`));
  }));
}

function showroomDot(row, domain) {
  return h("a", {
    class: "sr-dot", "data-s": row.showroom, title: t(`progress.showroom.${row.showroom}`),
    href: `https://showroom-showroom-${row.user}.${domain}`, target: "_blank", rel: "noopener",
  }, row.user);
}

function matrix(result) {
  const groups = [];
  result.columns.forEach((column) => {
    const last = groups[groups.length - 1];
    if (last?.content === column.content) last.span += 1;
    else groups.push({ content: column.content, span: 1 });
  });
  const titles = Object.fromEntries(result.definitions.map((d) => [d.name, d.title]));
  const head = h("thead", {},
    h("tr", { class: "group-row" }, h("th", { rowspan: "2", scope: "col" }, t("progress.user")),
      groups.map((g) => h("th", { colspan: String(g.span), scope: "colgroup" }, titles[g.content] || g.content)),
      h("th", { rowspan: "2", scope: "col" }, t("progress.total"))),
    h("tr", {}, result.columns.map((column) => h("th", { scope: "col", title: column.name },
      h("span", { class: "mod" }, `M${column.module}`), h("span", { class: "cp-name" }, column.name)))));
  const body = h("tbody", {}, result.rows.map((row) => h("tr", {},
    h("th", { scope: "row" }, showroomDot(row, result.domain)),
    result.columns.map((column) => {
      const cell = row.cells[column.id];
      return h("td", { class: "cell", "data-s": cell.s, title: `${column.name}: ${cell.o}` }, CELL_MARK[cell.s]);
    }),
    h("td", { class: "row-total" }, `${row.done}/${result.columns.length}`))));
  return h("div", { class: "matrix-wrap" }, h("table", { class: "matrix" }, head, body));
}

function renderProgress() {
  renderRunButton();
  const area = $("progress-area");
  if (!progress.workshop) return area.replaceChildren(h("p", { class: "placeholder-card" }, t("progress.pick")));
  const result = progress.result;
  if (!result || result.workshop !== progress.workshop) {
    return area.replaceChildren(h("p", { class: "placeholder-card" }, t("progress.never")));
  }
  const missing = result.definitions.filter((d) => !d.checkpoints).map((d) => d.name);
  area.replaceChildren(...[
    h("p", { class: "when" }, t("progress.at", { when: formatTime(result.at) })),
    result.deployed ? null : h("p", { class: "verdict", "data-v": "caution" }, t("progress.notDeployed")),
    summaryTiles(result),
    result.columns.length ? columnBars(result) : null,
    missing.length ? h("p", { class: "empty" }, t("progress.noCheckpoints", { names: missing.join(", ") })) : null,
    result.columns.length ? matrix(result) : null,
    result.columns.length ? h("p", { class: "legend" }, t("progress.legend")) : null,
  ].filter(Boolean));
}

$("progress-workshop").addEventListener("change", (event) => {
  progress.workshop = event.target.value;
  loadLastProgress();
});
$("btn-progress-run").addEventListener("click", runProgress);
$("progress-auto").addEventListener("change", () => {
  scheduleAutoRefresh();
  if ($("progress-auto").checked) runProgress();
});

viewHooks.push({
  view: "progress",
  onShow: showProgress,
  onHide: scheduleAutoRefresh,
  onLang: () => { if (app.overview) renderProgressPicker(); renderProgress(); },
});
