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
