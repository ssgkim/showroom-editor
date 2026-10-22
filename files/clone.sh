#!/bin/sh
# init 1 (git-cloner 이미지): 모듈 저장소 clone + home 컴포넌트/통합 playbook 준비
set -eu
export HOME=/tmp
# emptyDir subPath 디렉터리는 소유자가 컨테이너 UID와 달라 git 이 거부한다
git config --global --add safe.directory '*'

SOURCES=/showroom/sources
REPO=/showroom/repo

mkdir -p "$SOURCES" "$REPO/home/modules/ROOT/pages"

while read -r key url ref path; do
  [ -n "$key" ] || continue
  echo "[clone] $key <- $url ($ref)"
  rm -rf "${SOURCES:?}/$key"
  git clone --quiet --depth 1 --branch "$ref" "$url" "$SOURCES/$key"
done < /config/modules.txt

# 행사별 페이지 수정(Showroom Editor). 원본 저장소는 바꾸지 않고 clone 한 파일만 덮어쓴다.
while read -r key idx path; do
  [ -n "$key" ] || continue
  case "$path" in
    /*|*..*) echo "[overlay] 오류: 잘못된 경로 $path" >&2; exit 1 ;;
  esac
  echo "[overlay] $key: $path"
  cp "/config/overlay-$key-$idx.adoc" "$SOURCES/$key/$path"
done < /config/overlays.txt

cp /config/site.yml "$REPO/site.yml"
cp /config/home-antora.yml "$REPO/home/antora.yml"
cp /config/home-index.adoc "$REPO/home/modules/ROOT/pages/index.adoc"
cp /config/home-nav.adoc "$REPO/home/modules/ROOT/nav.adoc"

# Antora 로컬 source 는 git 저장소여야 한다
cd "$REPO"
rm -rf .git
git init --quiet
git add -A
git -c user.name=showroom -c user.email=showroom@localhost commit --quiet -m "home"
echo "[clone] done"
