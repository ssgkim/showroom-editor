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
