"use strict";

/** 화면 문구. 키는 index.html 의 data-i18n* 속성과 app.js 의 t() 호출에서 쓴다. */
const MESSAGES = {
  ko: {
    "brand.sub": "워크샵 콘텐츠 구성 · 미리보기 · 배포",
    "cluster.label": "클러스터",
    "deployed.label": "배포 중",
    "deployed.none": "없음",

    "catalog.heading": "콘텐츠 카탈로그",
    "catalog.desc": "Showroom(Antora) 형식 저장소를 등록합니다. 등록할 때 저장소를 검사합니다.",
    "catalog.empty": "등록된 콘텐츠가 없습니다. 아래에서 git 주소를 등록하세요.",
    "catalog.new": "새 콘텐츠 등록",
    "form.name": "이름",
    "form.nameHint": "URL 경로가 됩니다 (소문자, 숫자, -)",
    "form.repoUrl": "git 주소",
    "form.ref": "브랜치/태그",
    "form.startPath": "콘텐츠 경로",
    "form.title": "제목",
    "form.titleHint": "비우면 antora.yml 의 title",
    "form.advanced": "탭 · 속성 (선택)",
    "form.tabs": "추가 탭",
    "form.tabsHint": "한 줄에 하나: 이름 | URL · {{ .domain }} 사용 가능",
    "form.attrs": "Antora 속성",
    "form.attrsHint": "한 줄에 하나: 이름 = 값 · {{ .user }} 사용 가능",
    "form.submit": "검사 후 등록",
    "ph.name": "예: agentops",
    "ph.title": "예: Basic AgentOps on Red Hat AI",

    "composer.heading": "워크샵 구성",
    "composer.desc": "행사마다 포함할 콘텐츠와 순서를 정합니다. 사용자 Showroom 하나에 모두 합쳐집니다.",
    "composer.new": "+ 새 워크샵",
    "composer.live": "배포 중",
    "ws.title": "워크샵 제목",
    "ws.id": "ID",
    "ws.userStart": "시작 사용자",
    "ws.userCount": "사용자 수",
    "ws.selected": "포함된 콘텐츠",
    "ws.available": "추가할 수 있는 콘텐츠",
    "ws.selectedEmpty": "오른쪽에서 콘텐츠를 추가하세요.",
    "ws.availableEmpty": "추가할 콘텐츠가 없습니다.",
    "ph.wsTitle": "예: BC카드 RHOAI 핸즈온",
    "ph.wsId": "예: bccard-2026-11",
    "action.up": "위로",
    "action.down": "아래로",
    "action.remove": "빼기",
    "action.add": "추가",

    "btn.save": "저장",
    "btn.preview": "저장 후 미리보기",
    "btn.deploy": "저장 후 배포",
    "btn.deleteWorkshop": "워크샵 삭제",
    "btn.delete": "삭제",
    "btn.restartAll": "전체 재시작",
    "btn.undeploy": "배포 해제",
    "btn.close": "닫기",
    "confirm.deploy": "user 범위 전체에 배포할까요? 다시 클릭",
    "confirm.deleteWorkshop": "정말 삭제? 다시 클릭",
    "confirm.delete": "삭제? 다시 클릭",
    "confirm.removePreview": "미리보기 삭제? 다시 클릭",
    "confirm.restart": "전체 재시작? 다시 클릭",
    "confirm.undeploy": "모든 사용자 Showroom 삭제? 다시 클릭",

    "runs.heading": "미리보기 · 배포 상태",
    "preview.heading": "미리보기",
    "preview.none": "아직 미리보기가 없습니다.",
    "deploy.heading": "배포",
    "deploy.none": "배포된 워크샵이 없습니다.",
    "tally": "준비됨 {ready} / {total}",
    "tally.failed": " · 실패 {failed} (눌러서 로그 보기)",
    "log.title": "빌드 로그",
    "log.titleFor": "빌드 로그 · {ns}",

    "phase.ready": "준비됨",
    "phase.building": "빌드 중",
    "phase.starting": "시작 중",
    "phase.pending": "대기",
    "phase.failed": "실패",
    "phase.terminating": "삭제 중",
    "step.clone": "저장소 가져오는 중",
    "step.build": "Antora 빌드 중",
    "stepFailed.clone": "저장소 가져오기 실패",
    "stepFailed.build": "Antora 빌드 실패",

    "toast.saved": "저장했습니다",
    "toast.previewStarted": "미리보기를 빌드합니다. 1~2분 걸립니다",
    "toast.deployed": "{count}명에게 배포를 시작했습니다",
    "toast.cleaned": " · {count}개 정리",
    "toast.workshopDeleted": "워크샵을 삭제했습니다",
    "toast.catalogDeleted": "카탈로그에서 삭제: {name}",
    "toast.removed": "{count}개 네임스페이스를 삭제합니다",
    "toast.restarted": "{count}개 Showroom을 다시 빌드합니다",
    "toast.checking": "저장소를 검사하는 중입니다…",
    "toast.registered": "등록했습니다: {title} ({commit})",
    "err.invalid": "입력값을 확인하세요",
    "err.needContent": "콘텐츠를 하나 이상 포함하세요",
    "err.badLine": "형식이 맞지 않는 줄: {line}",
    "err.request": "요청 실패 ({status})",
  },
  en: {
    "brand.sub": "Compose · preview · deploy workshop content",
    "cluster.label": "Cluster",
    "deployed.label": "Deployed",
    "deployed.none": "None",

    "catalog.heading": "Content catalog",
    "catalog.desc": "Register Showroom (Antora) repositories. Each repository is checked when registered.",
    "catalog.empty": "No content yet. Register a git URL below.",
    "catalog.new": "Register content",
    "form.name": "Name",
    "form.nameHint": "Becomes the URL path (lowercase, digits, -)",
    "form.repoUrl": "Git URL",
    "form.ref": "Branch/tag",
    "form.startPath": "Content path",
    "form.title": "Title",
    "form.titleHint": "Defaults to the title in antora.yml",
    "form.advanced": "Tabs · attributes (optional)",
    "form.tabs": "Extra tabs",
    "form.tabsHint": "One per line: name | URL · {{ .domain }} allowed",
    "form.attrs": "Antora attributes",
    "form.attrsHint": "One per line: name = value · {{ .user }} allowed",
    "form.submit": "Check and register",
    "ph.name": "e.g. agentops",
    "ph.title": "e.g. Basic AgentOps on Red Hat AI",

    "composer.heading": "Workshop",
    "composer.desc": "Choose the content and order for each event. Everything is merged into one Showroom per user.",
    "composer.new": "+ New workshop",
    "composer.live": "Deployed",
    "ws.title": "Workshop title",
    "ws.id": "ID",
    "ws.userStart": "First user",
    "ws.userCount": "Number of users",
    "ws.selected": "Included content",
    "ws.available": "Available content",
    "ws.selectedEmpty": "Add content from the list on the right.",
    "ws.availableEmpty": "Nothing left to add.",
    "ph.wsTitle": "e.g. RHOAI hands-on day",
    "ph.wsId": "e.g. rhoai-2026-11",
    "action.up": "Move up",
    "action.down": "Move down",
    "action.remove": "Remove",
    "action.add": "Add",

    "btn.save": "Save",
    "btn.preview": "Save and preview",
    "btn.deploy": "Save and deploy",
    "btn.deleteWorkshop": "Delete workshop",
    "btn.delete": "Delete",
    "btn.restartAll": "Restart all",
    "btn.undeploy": "Undeploy",
    "btn.close": "Close",
    "confirm.deploy": "Deploy to the whole user range? Click again",
    "confirm.deleteWorkshop": "Really delete? Click again",
    "confirm.delete": "Delete? Click again",
    "confirm.removePreview": "Delete preview? Click again",
    "confirm.restart": "Restart all? Click again",
    "confirm.undeploy": "Delete every user Showroom? Click again",

    "runs.heading": "Preview · deployment",
    "preview.heading": "Preview",
    "preview.none": "No preview yet.",
    "deploy.heading": "Deployment",
    "deploy.none": "No workshop deployed.",
    "tally": "Ready {ready} / {total}",
    "tally.failed": " · failed {failed} (click to see logs)",
    "log.title": "Build log",
    "log.titleFor": "Build log · {ns}",

    "phase.ready": "Ready",
    "phase.building": "Building",
    "phase.starting": "Starting",
    "phase.pending": "Pending",
    "phase.failed": "Failed",
    "phase.terminating": "Deleting",
    "step.clone": "Cloning repositories",
    "step.build": "Building with Antora",
    "stepFailed.clone": "Clone failed",
    "stepFailed.build": "Antora build failed",

    "toast.saved": "Saved",
    "toast.previewStarted": "Building the preview. This takes 1–2 minutes",
    "toast.deployed": "Started deploying to {count} users",
    "toast.cleaned": " · removed {count}",
    "toast.workshopDeleted": "Workshop deleted",
    "toast.catalogDeleted": "Removed from catalog: {name}",
    "toast.removed": "Deleting {count} namespaces",
    "toast.restarted": "Rebuilding {count} Showrooms",
    "toast.checking": "Checking the repository…",
    "toast.registered": "Registered: {title} ({commit})",
    "err.invalid": "Check the highlighted fields",
    "err.needContent": "Include at least one piece of content",
    "err.badLine": "Line has the wrong format: {line}",
    "err.request": "Request failed ({status})",
  },
};

const LANG_KEY = "showroom-editor-lang";
const SUPPORTED_LANGS = Object.keys(MESSAGES);

function detectLang() {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    if (SUPPORTED_LANGS.includes(saved)) return saved;
  } catch (_error) {
    // 저장소를 쓸 수 없으면 브라우저 언어를 따른다
  }
  return (navigator.language || "").toLowerCase().startsWith("ko") ? "ko" : "en";
}

const i18n = { lang: detectLang() };

/** 키에 해당하는 문구. {name} 자리는 vars 로 채운다. */
function t(key, vars = {}) {
  const template = MESSAGES[i18n.lang][key] ?? MESSAGES.ko[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (match, name) => (name in vars ? String(vars[name]) : match));
}

function setLang(lang) {
  if (!SUPPORTED_LANGS.includes(lang)) return;
  i18n.lang = lang;
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch (_error) {
    // 기억하지 못해도 현재 화면에는 적용된다
  }
  applyStaticText();
}

/** index.html 의 data-i18n, data-i18n-placeholder, data-i18n-confirm 을 현재 언어로 채운다. */
function applyStaticText() {
  document.documentElement.lang = i18n.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  document.querySelectorAll("[data-i18n-confirm]").forEach((el) => { el.dataset.confirm = t(el.dataset.i18nConfirm); });
  document.querySelectorAll("[data-lang]").forEach((el) => {
    el.setAttribute("aria-pressed", String(el.dataset.lang === i18n.lang));
  });
}
