#!/usr/bin/env bash
# Showroom Editor 를 현재 로그인한 OpenShift 클러스터에 배포한다 (cluster-admin 필요).
#
#   curl -sL https://raw.githubusercontent.com/ssgkim/showroom-editor/main/editor/deploy.sh | bash
#
#   다른 브랜치/태그:  ... | SHOWROOM_EDITOR_REF=v1.0 bash
#   포크한 저장소:     ... | SHOWROOM_EDITOR_REPO=myorg/showroom-editor bash
#   로컬 소스로 빌드:  ./editor/deploy.sh --local     (개발용, 저장소 안에서 실행)
#
# 클러스터가 GitHub 저장소를 직접 가져와 이미지를 빌드하므로 PC 에는 oc 만 있으면 된다.
set -euo pipefail

REPO="${SHOWROOM_EDITOR_REPO:-ssgkim/showroom-editor}"
REF="${SHOWROOM_EDITOR_REF:-main}"
NS="showroom-editor"
MODE="git"
[[ "${1:-}" == "--local" ]] && MODE="local"

fail() { echo "오류: $*" >&2; exit 1; }
step() { echo; echo "▶ $*"; }

random_hex() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 16
  else
    head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n'
  fi
}

command -v oc >/dev/null 2>&1 || fail "oc CLI 가 필요합니다"
oc whoami >/dev/null 2>&1 || fail "먼저 클러스터에 로그인하세요: oc login <API 주소>"
oc auth can-i create clusterrolebindings >/dev/null 2>&1 || fail "cluster-admin 권한이 필요합니다 (현재: $(oc whoami))"

if [[ "$MODE" == "local" ]]; then
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  [[ -f "$ROOT/editor/deploy/editor.yaml" ]] || fail "--local 은 저장소 안의 editor/deploy.sh 로 실행해야 합니다"
  MANIFEST="$ROOT/editor/deploy/editor.yaml"
else
  MANIFEST="https://raw.githubusercontent.com/$REPO/$REF/editor/deploy/editor.yaml"
fi

echo "클러스터: $(oc whoami --show-server)  사용자: $(oc whoami)"
echo "소스:     $([[ "$MODE" == local ]] && echo "로컬 $ROOT" || echo "github.com/$REPO @ $REF")"

step "매니페스트 적용"
oc apply -f "$MANIFEST"
oc patch buildconfig showroom-editor -n "$NS" --type merge \
  -p "{\"spec\":{\"source\":{\"git\":{\"uri\":\"https://github.com/$REPO.git\",\"ref\":\"$REF\"}}}}" >/dev/null

# oauth-proxy 세션 쿠키 암호화 키 (Git 에 두지 않는다)
if ! oc get secret showroom-editor-proxy -n "$NS" >/dev/null 2>&1; then
  oc create secret generic showroom-editor-proxy -n "$NS" --from-literal=session_secret="$(random_hex)"
fi

step "이미지 빌드 (3~5분)"
if [[ "$MODE" == "local" ]]; then
  oc start-build showroom-editor -n "$NS" --from-dir="$ROOT" --follow
else
  oc start-build showroom-editor -n "$NS" --follow
fi

step "배포"
oc rollout restart deployment/showroom-editor -n "$NS"
oc rollout status deployment/showroom-editor -n "$NS" --timeout=300s

echo
echo "✔ Showroom Editor: https://$(oc get route showroom-editor -n "$NS" -o jsonpath='{.spec.host}')"
echo "  인스트럭터 그룹 허용: oc adm policy add-role-to-group view <그룹> -n $NS"
