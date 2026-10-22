#!/bin/bash
# init 2 (antora 이미지): 모듈별 컴포넌트 이름/속성 주입 후 통합 사이트 빌드
set -euo pipefail

while read -r key url ref path; do
  [ -n "$key" ] || continue
  descriptor="/showroom/sources/$key/$path/antora.yml"
  if [ ! -f "$descriptor" ]; then
    echo "[build] 오류: $key 모듈에 $path/antora.yml 이 없습니다 ($url)" >&2
    exit 1
  fi
  echo "[build] $key: name=$key, attributes <- attrs-$key.yml"
  # 저장소마다 컴포넌트 이름이 같아도(modules 등) 충돌하지 않도록 모듈 키로 바꾼다.
  # Antora 는 HEAD 브랜치의 worktree 를 읽으므로 커밋 없이 반영된다.
  yq -i ".name = \"$key\" | .asciidoc.attributes *= load(\"/config/attrs-$key.yml\")" "$descriptor"
done < /config/modules.txt

antora --stacktrace /showroom/repo/site.yml
echo "[build] done"
