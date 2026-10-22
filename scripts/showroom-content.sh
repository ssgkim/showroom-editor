#!/usr/bin/env bash
# 인스트럭터용: 클러스터에 워크샵 콘텐츠(git 주소)를 등록/해제한다. Git push 는 필요 없다.
#
#   ./scripts/showroom-content.sh list
#   ./scripts/showroom-content.sh add <이름> <git 주소> [브랜치] [제목]
#   ./scripts/showroom-content.sh remove <이름>
#   ./scripts/showroom-content.sh status
#
# 예) ./scripts/showroom-content.sh add agentops https://github.com/ssgkim/rhoai-basic-agentops-workshop.git main "Basic AgentOps on Red Hat AI"
#
# 등록 정보는 Application(showroom-gitops) 의 spec.source.helm.valuesObject.contents 에 저장되며,
# Argo CD 가 모든 사용자 Showroom 에 반영한다. 탭·속성 같은 상세 설정은 같은 위치를 oc edit 로 고친다.
set -euo pipefail

APP="${SHOWROOM_APP:-showroom-gitops}"
ARGO_NS="${SHOWROOM_ARGO_NS:-openshift-gitops}"

usage() {
  sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

json_escape() {
  local s="${1//\\/\\\\}"
  printf '%s' "${s//\"/\\\"}"
}

patch_contents() {
  oc patch application "$APP" -n "$ARGO_NS" --type merge \
    -p "{\"spec\":{\"source\":{\"helm\":{\"valuesObject\":{\"contents\":$1}}}}}" >/dev/null
}

cmd_list() {
  echo "이름 / git 주소 / 브랜치 / 제목"
  oc get application "$APP" -n "$ARGO_NS" -o go-template='
{{- with .spec.source.helm.valuesObject.contents }}{{ range $k, $v := . }}
{{- $k }}  {{ $v.repoUrl }}  {{ or $v.repoRef "main" }}  {{ or $v.title $k }}{{ "\n" }}
{{- end }}{{ else }}(등록된 콘텐츠 없음){{ "\n" }}{{ end }}'
}

cmd_add() {
  local name="${1:-}" url="${2:-}" ref="${3:-main}" title="${4:-}"
  [[ -n "$name" && -n "$url" ]] || usage
  if [[ ! "$name" =~ ^[a-z0-9][a-z0-9-]*$ || "$name" == "home" ]]; then
    echo "오류: 이름은 소문자/숫자/- 만 쓸 수 있고 'home' 은 사용할 수 없습니다." >&2
    exit 1
  fi
  if [[ ! "$url" =~ ^https://[^[:space:]\"]+$ ]]; then
    echo "오류: git 주소는 https:// 로 시작해야 합니다." >&2
    exit 1
  fi

  local body="\"repoUrl\":\"$(json_escape "$url")\",\"repoRef\":\"$(json_escape "$ref")\""
  [[ -z "$title" ]] || body+=",\"title\":\"$(json_escape "$title")\""
  patch_contents "{\"$name\":{$body}}"
  echo "등록: $name <- $url ($ref)"
  echo "모든 사용자 Showroom 이 다시 빌드됩니다. 진행 상황: $0 status"
}

cmd_remove() {
  local name="${1:-}"
  [[ -n "$name" ]] || usage
  patch_contents "{\"$name\":null}"
  echo "해제: $name"
}

cmd_status() {
  oc get application "$APP" -n "$ARGO_NS" \
    -o custom-columns='APP:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status'
  echo
  oc get pods -A -l app.kubernetes.io/name=showroom \
    -o custom-columns='NAMESPACE:.metadata.namespace,STATUS:.status.phase,READY:.status.containerStatuses[0].ready'
}

[[ $# -ge 1 ]] || usage
cmd="$1"; shift
case "$cmd" in
  list) cmd_list ;;
  add) cmd_add "$@" ;;
  remove) cmd_remove "$@" ;;
  status) cmd_status ;;
  *) usage ;;
esac
