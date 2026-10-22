"use strict";

/**
 * 행사별 페이지 수정. 원본 저장소는 그대로 두고, 저장한 파일을 빌드할 때 덮어쓴다.
 * app.js 의 app, h, api, t, toast, confirmClick, $ 를 사용한다.
 */
const pageEditor = { wid: null, content: null, pages: [], path: null, file: null, dirty: false, armedPath: null };

/** "content/modules/ROOT/pages/kr/a.adoc" → ["kr/", "a.adoc"]. 모듈이 ROOT 가 아니면 모듈 이름을 앞에 둔다. */
function splitPagePath(path) {
  const rest = path.replace(/^.*?modules\//, "").replace(/^ROOT\//, "").replace(/(^|\/)pages\//, "$1");
  const cut = rest.lastIndexOf("/") + 1;
  return [rest.slice(0, cut), rest.slice(cut)];
}

async function openPageEditor(content) {
  Object.assign(pageEditor, { wid: app.draft.id, content, pages: [], path: null, file: null, dirty: false });
  $("page-dialog-title").textContent = t("pages.title", { name: app.data.catalog[content]?.title || content });
  $("page-commit").textContent = t("pages.loading");
  renderPageList();
  renderPageFile();
  $("page-dialog").showModal();
  await loadPageList();
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
  const items = pageEditor.pages.map((page) => h("li", {},
    h("button", {
      type: "button", class: "page-pick", "aria-current": String(page.path === pageEditor.path),
      title: page.path, onclick: () => selectPage(page.path),
    },
    h("span", { class: "page-name" }, h("span", { class: "page-dir" }, splitPagePath(page.path)[0]), splitPagePath(page.path)[1]),
    page.stale ? h("span", { class: "page-flag stale", title: t("pages.staleShort") }, "⚠")
      : page.edited ? h("span", { class: "page-flag", title: t("pages.editedShort") }, "●") : null)));
  $("page-list").replaceChildren(...(items.length ? items : [h("li", {}, h("p", { class: "empty" }, t("pages.loading")))]));
}

async function selectPage(path) {
  if (pageEditor.dirty && pageEditor.armedPath !== path) {
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

function renderPageFile() {
  const { file } = pageEditor;
  const editor = $("page-text");
  $("page-empty").hidden = Boolean(file);
  $("page-work").hidden = !file;
  if (!file) return;
  $("page-path").textContent = file.path;
  $("page-state").textContent = file.edited !== null
    ? t("pages.editedAt", { when: new Date(file.updatedAt).toLocaleString(i18n.lang === "ko" ? "ko-KR" : "en-US") })
    : t("pages.original");
  $("page-stale").hidden = !file.stale;
  $("page-original").textContent = file.original ?? t("pages.missing");
  editor.value = file.edited ?? file.original ?? "";
  $("btn-page-revert").hidden = file.edited === null;
}

async function savePage() {
  const { wid, content, path } = pageEditor;
  await api("PUT", `/api/workshops/${wid}/pages/${content}/file`, { path, text: $("page-text").value });
  pageEditor.dirty = false;
  toast(t("pages.saved"));
  await Promise.all([loadPageList(), loadState()]);
  await selectPage(path);
}

async function revertPage() {
  const { wid, content, path } = pageEditor;
  await api("DELETE", `/api/workshops/${wid}/pages/${content}/file?${new URLSearchParams({ path })}`);
  pageEditor.dirty = false;
  toast(t("pages.reverted"));
  await Promise.all([loadPageList(), loadState()]);
  await selectPage(path);
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

function bindPageEditor() {
  $("page-text").addEventListener("input", () => {
    pageEditor.dirty = true;
    pageEditor.armedPath = null;
  });
  $("page-work").addEventListener("submit", (event) => {
    event.preventDefault();
    busy(event.submitter || $("btn-page-save"), savePage);
  });
  $("btn-page-revert").addEventListener("click", (event) => confirmClick(event.currentTarget, revertPage));
  $("btn-page-close").addEventListener("click", () => closePageEditor());
  $("page-dialog").addEventListener("cancel", (event) => closePageEditor(event));
  $("page-compare").addEventListener("change", (event) => {
    $("page-work").classList.toggle("comparing", event.target.checked);
  });
}

bindPageEditor();
