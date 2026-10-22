#!/usr/bin/env bash
# Showroom Editor 를 현재 로그인한 클러스터에 빌드·배포한다 (cluster-admin 필요).
#   ./editor/deploy.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NS="showroom-editor"

oc apply -f "$ROOT/editor/deploy/editor.yaml"

# oauth-proxy 세션 쿠키 암호화 키 (Git 에 두지 않는다)
if ! oc get secret showroom-editor-proxy -n "$NS" >/dev/null 2>&1; then
  oc create secret generic showroom-editor-proxy -n "$NS" \
    --from-literal=session_secret="$(openssl rand -hex 16)"
fi

oc start-build showroom-editor -n "$NS" --from-dir="$ROOT" --follow
oc rollout restart deployment/showroom-editor -n "$NS"
oc rollout status deployment/showroom-editor -n "$NS" --timeout=300s

echo
echo "Showroom Editor: https://$(oc get route showroom-editor -n "$NS" -o jsonpath='{.spec.host}')"
echo "인스트럭터 그룹 허용: oc adm policy add-role-to-group view <그룹> -n $NS"
