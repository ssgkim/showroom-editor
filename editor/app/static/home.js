"use strict";

/**
 * Showroom 첫 화면(home 컴포넌트 index.adoc) 편집. pages.js 의 대화상자를 home 모드로 쓰고,
 * 내용은 워크샵 구성의 homePage 로 저장한다. 비우면 자동으로 만든 화면을 쓴다.
 */
function openHomeEditor() {
  const reopen = () => showSingleFile(homeFile());
  showPageDialog({
    mode: "home",
    title: t("home.dialogTitle", { title: app.draft.title }),
    desc: t("home.dialogDesc"),
    actions: {
      save: async (text) => {
        // 자동 화면과 같으면 직접 편집하지 않은 것으로 본다
        app.draft = { ...app.draft, homePage: text.trim() === defaultHomePage().trim() ? "" : text };
        await saveDraft();
      },
      revert: async () => {
        app.draft = { ...app.draft, homePage: "" };
        await saveDraft();
      },
      saved: "home.saved",
      reverted: "home.reverted",
      reload: async () => reopen(),
    },
  });
  $("page-commit").textContent = "";
  reopen();
}

function homeFile() {
  const custom = app.draft.homePage.trim() ? app.draft.homePage : null;
  return { path: "index.adoc", label: t("home.path"), original: defaultHomePage(), edited: custom, stale: false };
}

$("btn-home-page").addEventListener("click", () => openHomeEditor());
