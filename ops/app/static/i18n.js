"use strict";

const DEFINITION_TEMPLATE_KO = `# 워크샵 정의 (저장소 루트의 workshop.yaml 과 같은 형식)
about:
  summary: ""
  audience: ""
  duration: 60m
  level: beginner
requirements:
  # 점검 유형: operator, clusterVersion, gpuNodes, resource, http, capacity
  # severity: required(실패 시 ❌, 기본) | recommended(실패 시 ⚠️)
  - name: OpenShift AI 3.5 이상
    check: { type: operator, package: rhods-operator, minVersion: "3.5" }
    fix: OperatorHub 에서 Red Hat OpenShift AI 를 설치하세요
checkpoints: []
`;

const DEFINITION_TEMPLATE_EN = `# Workshop definition (same format as workshop.yaml at the repository root)
about:
  summary: ""
  audience: ""
  duration: 60m
  level: beginner
requirements:
  # check types: operator, clusterVersion, gpuNodes, resource, http, capacity
  # severity: required (fails with ❌, default) | recommended (warns with ⚠️)
  - name: OpenShift AI 3.5 or later
    check: { type: operator, package: rhods-operator, minVersion: "3.5" }
    fix: Install Red Hat OpenShift AI from OperatorHub
checkpoints: []
`;

const MESSAGES = {
  ko: {
    "switch.kicker": "콘텐츠 구성·배포",
    "brand.sub": "워크샵 운영 허브 · 사전 점검 · 갤러리 · 진행 현황",
    "cluster.label": "클러스터",
    "nav.preflight": "사전 점검",
    "nav.gallery": "갤러리",
    "nav.progress": "진행 현황",
    "nav.soon": "준비 중",
    "gallery.heading": "콘텐츠 갤러리",
    "gallery.desc": "Showroom Editor 카탈로그의 콘텐츠를 워크샵 정의(소개·요구 사항·체크포인트)와 함께 보여 줍니다.",
    "gallery.filterAll": "전체",
    "gallery.filterLive": "배포 중 워크샵",
    "gallery.empty": "카탈로그에 콘텐츠가 없습니다. Showroom Editor 에서 먼저 등록하세요.",
    "gallery.noDefinition": "워크샵 정의가 없습니다. 사전 점검 화면의 '워크샵 정의'에서 추가하면 소개와 요구 사항이 표시됩니다.",
    "gallery.requirements": "요구 사항 {count}",
    "gallery.requiredRecommended": "필수 {required} · 권장 {recommended}",
    "gallery.checkpoints": "체크포인트 {count}",
    "gallery.modules": "모듈 {list}",
    "gallery.usedIn": "포함된 워크샵",
    "gallery.notUsed": "아직 어느 워크샵에도 없음",
    "gallery.details": "요구 사항 · 체크포인트 보기",
    "gallery.required": "필수",
    "gallery.recommended": "권장",
    "gallery.readiness.ready": "이 클러스터 준비됨",
    "gallery.readiness.caution": "확인 필요",
    "gallery.readiness.blocked": "준비 안 됨",
    "gallery.readiness.none": "점검 전",
    "gallery.readinessAt": "{workshop} 사전 점검 · {when}",
    "gallery.level.beginner": "입문",
    "gallery.level.intermediate": "중급",
    "gallery.level.advanced": "고급",
    "gallery.loading": "불러오는 중…",

    "progress.heading": "진행 현황",
    "progress.desc": "사용자마다 워크샵 정의의 체크포인트(실습 결과물)를 클러스터에서 확인합니다. 클러스터는 읽기만 합니다.",
    "progress.workshop": "워크샵",
    "progress.auto": "1분마다 자동 확인",
    "progress.run": "지금 확인",
    "progress.running": "확인 중…",
    "progress.never": "아직 확인하지 않았습니다. '지금 확인'을 누르세요.",
    "progress.at": "{when} 기준",
    "progress.users": "사용자",
    "progress.showroomReady": "Showroom 준비",
    "progress.overall": "전체 진행률",
    "progress.done": "완료",
    "progress.noCheckpoints": "{names}: 체크포인트가 없습니다. 사전 점검 화면의 '워크샵 정의'에 checkpoints 를 추가하면 여기에 열이 생깁니다.",
    "progress.user": "사용자",
    "progress.total": "완료",
    "progress.module": "모듈 {module}",
    "progress.legend": "✓ 완료 · · 아직 · ? 확인 실패 (칸에 마우스를 올리면 관찰 값)",
    "progress.showroom.ready": "Showroom 준비됨",
    "progress.showroom.starting": "Showroom 시작 중",
    "progress.showroom.missing": "Showroom 없음",
    "progress.showroom.unknown": "Showroom 상태 알 수 없음",
    "progress.notDeployed": "이 워크샵은 지금 배포되어 있지 않습니다. 결과는 참고용입니다.",
    "progress.pick": "워크샵을 고르세요.",
    "progress.columnFailed": "{name}: 모든 사용자에서 확인하지 못했습니다 — {reason}",

    "ws.heading": "워크샵",
    "ws.desc": "Showroom Editor 에 저장된 워크샵입니다.",
    "ws.empty": "Showroom Editor 에 저장된 워크샵이 없습니다. 에디터에서 먼저 워크샵을 만드세요.",
    "ws.live": "배포 중",
    "ws.users": "user{start}~{end} · 콘텐츠 {count}개",
    "ws.lastRun": "마지막 점검 {when}",

    "def.heading": "워크샵 정의",
    "def.desc": "콘텐츠별 요구 사항. 저장소의 workshop.yaml 을 읽고, 여기서 덮어쓸 수 있습니다.",
    "def.source.repo": "저장소",
    "def.source.override": "덮어씀",
    "def.source.none": "정의 없음",
    "def.source.error": "오류",
    "def.edit": "편집",
    "def.save": "저장",
    "def.reset": "덮어쓰기 삭제",
    "def.close": "닫기",
    "def.editing": "{name} 정의 편집",
    "def.template": DEFINITION_TEMPLATE_KO,
    "confirm.reset": "저장소 정의로 되돌릴까요? 다시 클릭",

    "run.heading": "사전 점검",
    "run.desc": "행사 전에 이 클러스터에서 워크샵을 진행할 수 있는지 확인합니다. 클러스터는 읽기만 합니다.",
    "run.pick": "왼쪽에서 워크샵을 고르세요.",
    "run.button": "지금 점검",
    "run.running": "점검 중…",
    "run.report": "보고서 내려받기 (.md)",
    "run.never": "아직 점검하지 않았습니다. ‘지금 점검’을 누르세요.",
    "run.at": "{when} 점검",
    "verdict.ready": "준비 완료: 모든 필수 항목을 통과했습니다.",
    "verdict.caution": "진행 가능: 확인이 필요한 항목이 {count}개 있습니다.",
    "verdict.blocked": "준비 안 됨: 필수 항목 {count}개가 실패했습니다.",
    "group.common": "공통",
    "status.pass": "통과",
    "status.warn": "경고",
    "status.fail": "실패",
    "status.error": "점검 불가",
    "fix.label": "조치",
    "noDefinition": "정의가 없어 요구 사항을 점검하지 않았습니다: {names}",

    "toast.saved": "정의를 저장했습니다",
    "toast.reset": "저장소 정의로 되돌렸습니다",
    "err.request": "요청 실패 ({status})",
  },
  en: {
    "switch.kicker": "Compose & deploy",
    "brand.sub": "Workshop operations hub · pre-flight · gallery · progress",
    "cluster.label": "Cluster",
    "nav.preflight": "Pre-flight",
    "nav.gallery": "Gallery",
    "nav.progress": "Progress",
    "nav.soon": "Soon",
    "gallery.heading": "Content gallery",
    "gallery.desc": "Content in the Showroom Editor catalog, with its workshop definition (about, requirements, checkpoints).",
    "gallery.filterAll": "All",
    "gallery.filterLive": "In the live workshop",
    "gallery.empty": "The catalog is empty. Register content in Showroom Editor first.",
    "gallery.noDefinition": "No workshop definition. Add one under 'Workshop definitions' on the Pre-flight page to show the summary and requirements.",
    "gallery.requirements": "{count} requirements",
    "gallery.requiredRecommended": "{required} required · {recommended} recommended",
    "gallery.checkpoints": "{count} checkpoints",
    "gallery.modules": "modules {list}",
    "gallery.usedIn": "Used in",
    "gallery.notUsed": "Not used in any workshop yet",
    "gallery.details": "Show requirements · checkpoints",
    "gallery.required": "required",
    "gallery.recommended": "recommended",
    "gallery.readiness.ready": "Ready on this cluster",
    "gallery.readiness.caution": "Needs attention",
    "gallery.readiness.blocked": "Not ready",
    "gallery.readiness.none": "Not checked",
    "gallery.readinessAt": "{workshop} pre-flight · {when}",
    "gallery.level.beginner": "Beginner",
    "gallery.level.intermediate": "Intermediate",
    "gallery.level.advanced": "Advanced",
    "gallery.loading": "Loading…",

    "progress.heading": "Progress",
    "progress.desc": "Checks each user's lab results (checkpoints from the workshop definition) on the cluster. The cluster is only read.",
    "progress.workshop": "Workshop",
    "progress.auto": "Refresh every minute",
    "progress.run": "Check now",
    "progress.running": "Checking…",
    "progress.never": "Not checked yet. Click 'Check now'.",
    "progress.at": "as of {when}",
    "progress.users": "Users",
    "progress.showroomReady": "Showroom ready",
    "progress.overall": "Overall progress",
    "progress.done": "done",
    "progress.noCheckpoints": "{names}: no checkpoints. Add checkpoints to the workshop definition on the Pre-flight page to get columns here.",
    "progress.user": "User",
    "progress.total": "Done",
    "progress.module": "Module {module}",
    "progress.legend": "✓ done · · not yet · ? check failed (hover a cell for the observed value)",
    "progress.showroom.ready": "Showroom ready",
    "progress.showroom.starting": "Showroom starting",
    "progress.showroom.missing": "No Showroom",
    "progress.showroom.unknown": "Showroom status unknown",
    "progress.notDeployed": "This workshop is not deployed right now. Results are for reference only.",
    "progress.pick": "Pick a workshop.",
    "progress.columnFailed": "{name}: could not be checked for any user — {reason}",

    "ws.heading": "Workshops",
    "ws.desc": "Workshops saved in Showroom Editor.",
    "ws.empty": "No workshops in Showroom Editor yet. Create one in the editor first.",
    "ws.live": "Deployed",
    "ws.users": "user{start}–{end} · {count} contents",
    "ws.lastRun": "Last check {when}",

    "def.heading": "Workshop definitions",
    "def.desc": "Requirements per content. Read from workshop.yaml in each repository; you can override them here.",
    "def.source.repo": "Repository",
    "def.source.override": "Overridden",
    "def.source.none": "No definition",
    "def.source.error": "Error",
    "def.edit": "Edit",
    "def.save": "Save",
    "def.reset": "Remove override",
    "def.close": "Close",
    "def.editing": "Editing {name}",
    "def.template": DEFINITION_TEMPLATE_EN,
    "confirm.reset": "Revert to the repository definition? Click again",

    "run.heading": "Pre-flight check",
    "run.desc": "Before the event, confirm this cluster can run the workshop. The cluster is only read.",
    "run.pick": "Pick a workshop on the left.",
    "run.button": "Run check",
    "run.running": "Checking…",
    "run.report": "Download report (.md)",
    "run.never": "Not checked yet. Click ‘Run check’.",
    "run.at": "Checked {when}",
    "verdict.ready": "Ready: every required item passed.",
    "verdict.caution": "Can proceed: {count} items need attention.",
    "verdict.blocked": "Not ready: {count} required items failed.",
    "group.common": "Common",
    "status.pass": "Pass",
    "status.warn": "Warning",
    "status.fail": "Fail",
    "status.error": "Could not check",
    "fix.label": "Fix",
    "noDefinition": "No definition, requirements not checked: {names}",

    "toast.saved": "Definition saved",
    "toast.reset": "Reverted to the repository definition",
    "err.request": "Request failed ({status})",
  },
};

const LANG_KEY = "workshop-ops-lang";
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

function applyStaticText() {
  document.documentElement.lang = i18n.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-lang]").forEach((el) => {
    el.setAttribute("aria-pressed", String(el.dataset.lang === i18n.lang));
  });
}
