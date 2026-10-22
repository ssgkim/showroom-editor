"use strict";

/**
 * 페이지 편집 대화상자. 두 가지 모드를 쓴다.
 * - page: 콘텐츠의 .adoc 페이지를 행사별로 덮어쓴다 (원본 저장소는 그대로).
 * - home: Showroom 첫 화면 전체를 편집해 워크샵 구성(homePage)에 저장한다 (home.js).
 * app.js 의 app, h, api, t, toast, busy, confirmClick, $ 를 사용한다.
 */
const ASCIIDOCTOR_URL = "https://cdn.jsdelivr.net/npm/@asciidoctor/core@3.0.4/dist/browser/asciidoctor.min.js";
const RENDER_DELAY_MS = 300;

const pageEditor = {
  mode: "page", wid: null, content: null, pages: [], path: null, file: null,
  dirty: false, armedPath: null, actions: null,
};

/** "content/modules/ROOT/pages/kr/a.adoc" → ["kr/", "a.adoc"]. 모듈이 ROOT 가 아니면 모듈 이름을 앞에 둔다. */
function splitPagePath(path) {
  const rest = path.replace(/^.*?modules\//, "").replace(/^ROOT\//, "").replace(/(^|\/)pages\//, "$1");
  const cut = rest.lastIndexOf("/") + 1;
  return [rest.slice(0, cut), rest.slice(cut)];
}

/** 대화상자를 연다. actions: { save(text), revert() } — 모드마다 저장 방법이 다르다. */
function showPageDialog({ mode, title, desc, actions }) {
  Object.assign(pageEditor, { mode, pages: [], path: null, file: null, dirty: false, armedPath: null, actions });
  const dialog = $("page-dialog");
  dialog.classList.toggle("single", mode === "home");
  $("page-dialog-title").textContent = title;
  $("page-dialog-desc").textContent = desc;
  $("page-compare-label").textContent = t(mode === "home" ? "home.compare" : "pages.compare");
  $("btn-page-revert").textContent = t(mode === "home" ? "home.revert" : "pages.revert");
  $("page-note").hidden = mode !== "home";
  renderPageList();
  renderPageFile();
  dialog.showModal();
}

async function openPageEditor(content) {
  const wid = app.draft.id;
  Object.assign(pageEditor, { wid, content });
  showPageDialog({
    mode: "page",
    title: t("pages.title", { name: app.data.catalog[content]?.title || content }),
    desc: t("pages.desc"),
    actions: {
      save: (text) => api("PUT", `/api/workshops/${wid}/pages/${content}/file`, { path: pageEditor.path, text }),
      revert: () => api("DELETE", `/api/workshops/${wid}/pages/${content}/file?${new URLSearchParams({ path: pageEditor.path })}`),
      saved: "pages.saved",
      reverted: "pages.reverted",
      reload: reloadContentPage,
    },
  });
  $("page-commit").textContent = t("pages.loading");
  await loadPageList();
}

async function reloadContentPage() {
  await Promise.all([loadPageList(), loadState()]);
  await selectPage(pageEditor.path, true);
}

async function loadPageList() {
  try {
    const result = await api("GET", `/api/workshops/${pageEditor.wid}/pages/${pageEditor.content}`);
    pageEditor.pages = result.pages;
    $("page-commit").textContent = t("pages.commit", { commit: result.commit });
  } catch (error) {
    $("page-commit").textContent = "";
    toast(error.message, true);
  }
  renderPageList();
}

function renderPageList() {
  const items = pageEditor.pages.map((page) => {
    const [dir, name] = splitPagePath(page.path);
    return h("li", {},
      h("button", {
        type: "button", class: "page-pick", "aria-current": String(page.path === pageEditor.path),
        title: page.path, onclick: () => selectPage(page.path),
      },
      h("span", { class: "page-name" }, h("span", { class: "page-dir" }, dir), name),
      page.stale ? h("span", { class: "page-flag stale", title: t("pages.staleShort") }, "⚠")
        : page.edited ? h("span", { class: "page-flag", title: t("pages.editedShort") }, "●") : null));
  });
  $("page-list").replaceChildren(...(items.length ? items : [h("li", {}, h("p", { class: "empty" }, t("pages.loading")))]));
}

/** 저장하지 않은 수정이 있으면 한 번은 막고 알린다. force 는 저장 직후 다시 읽을 때 쓴다. */
async function selectPage(path, force = false) {
  if (!force && pageEditor.dirty && pageEditor.armedPath !== path) {
    pageEditor.armedPath = path;
    toast(t("pages.unsaved"), true);
    return;
  }
  pageEditor.armedPath = null;
  try {
    const query = new URLSearchParams({ path });
    pageEditor.file = await api("GET", `/api/workshops/${pageEditor.wid}/pages/${pageEditor.content}/file?${query}`);
    pageEditor.path = path;
    pageEditor.dirty = false;
  } catch (error) {
    toast(error.message, true);
  }
  renderPageList();
  renderPageFile();
}

/** home 모드처럼 목록 없이 파일 하나를 바로 연다. */
function showSingleFile(file) {
  pageEditor.file = file;
  pageEditor.path = file.path;
  pageEditor.dirty = false;
  renderPageFile();
}

function renderPageFile() {
  const { file } = pageEditor;
  $("page-empty").hidden = Boolean(file);
  $("page-work").hidden = !file;
  if (!file) return;
  $("page-path").textContent = file.label || file.path;
  $("page-state").textContent = file.edited !== null
    ? (file.updatedAt
      ? t("pages.editedAt", { when: new Date(file.updatedAt).toLocaleString(i18n.lang === "ko" ? "ko-KR" : "en-US") })
      : t("home.pageCustom"))
    : t("pages.original");
  $("page-stale").hidden = !file.stale;
  $("page-original").textContent = file.original ?? t("pages.missing");
  $("page-text").value = file.edited ?? file.original ?? "";
  $("btn-page-revert").hidden = file.edited === null;
  scheduleRender();
}

// ── 렌더링 미리보기 (asciidoctor.js 를 처음 쓸 때 불러온다) ──────────────
let asciidoctorLoading = null;
let renderTimer = null;

function loadAsciidoctor() {
  asciidoctorLoading ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = ASCIIDOCTOR_URL;
    script.onload = () => resolve(window.Asciidoctor());
    script.onerror = () => { asciidoctorLoading = null; reject(new Error(ASCIIDOCTOR_URL)); };
    document.head.append(script);
  });
  return asciidoctorLoading;
}

const RENDER_STYLE = `body{font:15px/1.6 "Red Hat Text","Noto Sans KR",system-ui,sans-serif;color:#151515;margin:1rem 1.25rem}
h1,h2,h3{font-family:"Red Hat Display","Noto Sans KR",system-ui,sans-serif;line-height:1.25}h1{font-size:1.6rem}
code,pre{font-family:"Red Hat Mono",ui-monospace,monospace;font-size:.85em}pre{background:#f2f2f2;padding:.75rem;overflow:auto;border-radius:4px}
code{background:#f2f2f2;padding:0 .2em;border-radius:3px}a{color:#0066cc}table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:.3rem .5rem}
.admonitionblock{border-left:4px solid #0066cc;background:#eef5fc;padding:.25rem .75rem;margin:1rem 0}.admonitionblock td.icon{display:none}
.admonitionblock td{border:none}.admonitionblock .title{font-weight:700}img{max-width:100%}`;

function scheduleRender() {
  clearTimeout(renderTimer);
  if (!$("page-render").checked) return;
  renderTimer = setTimeout(renderPreview, RENDER_DELAY_MS);
}

async function renderPreview() {
  const frame = $("page-render-frame");
  try {
    const asciidoctor = await loadAsciidoctor();
    const user = `user${app.draft.userStart || 1}`;
    const html = asciidoctor.convert($("page-text").value, {
      safe: "secure", standalone: false,
      attributes: { user, guid: user, showtitle: true, "allow-uri-read": false },
    });
    // sandbox="" 인 iframe 에 넣어 스크립트와 외부 동작을 막는다
    frame.srcdoc = `<!doctype html><meta charset="utf-8"><style>${RENDER_STYLE}</style>${html}`;
  } catch (error) {
    frame.srcdoc = `<p style="font:14px system-ui;color:#c9190b">${t("pages.renderFailed", { error: error.message })
      .replace(/[<>&]/g, (ch) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" })[ch])}</p>`;
  }
}

// ── 저장 · 되돌리기 · 닫기 ──────────────────────────────────────────
async function savePage() {
  const { actions } = pageEditor;
  await actions.save($("page-text").value);
  pageEditor.dirty = false;
  toast(t(actions.saved));
  await actions.reload();
}

async function revertPage() {
  const { actions } = pageEditor;
  await actions.revert();
  pageEditor.dirty = false;
  toast(t(actions.reverted));
  await actions.reload();
}

function closePageEditor(event) {
  if (pageEditor.dirty && pageEditor.armedPath !== "__close") {
    event?.preventDefault();
    pageEditor.armedPath = "__close";
    toast(t("pages.unsavedClose"), true);
    return;
  }
  pageEditor.dirty = false;
  pageEditor.armedPath = null;
  $("page-dialog").close();
}

function updatePaneLayout() {
  const work = $("page-work");
  work.classList.toggle("comparing", $("page-compare").checked);
  work.classList.toggle("rendering", $("page-render").checked);
  scheduleRender();
}

function bindPageEditor() {
  $("page-text").addEventListener("input", () => {
    pageEditor.dirty = true;
    pageEditor.armedPath = null;
    scheduleRender();
  });
  $("page-work").addEventListener("submit", (event) => {
    event.preventDefault();
    busy(event.submitter || $("btn-page-save"), savePage);
  });
  $("btn-page-revert").addEventListener("click", (event) => confirmClick(event.currentTarget, revertPage));
  $("btn-page-close").addEventListener("click", () => closePageEditor());
  $("page-dialog").addEventListener("cancel", (event) => closePageEditor(event));
  $("page-compare").addEventListener("change", updatePaneLayout);
  $("page-render").addEventListener("change", updatePaneLayout);
}

bindPageEditor();
