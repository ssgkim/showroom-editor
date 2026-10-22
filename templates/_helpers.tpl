{{/*
클러스터에 등록된 콘텐츠 목록 (.Values.contents). order, key 순으로 정렬한다.
결과는 JSON {"items": [...]} 이며 호출 측에서 fromJson 으로 읽는다.
*/}}
{{- define "showroom.modules" -}}
{{- $byKey := dict }}
{{- $sortKeys := list }}
{{- range $key, $raw := .Values.contents | default dict }}
{{- if or (not (regexMatch "^[a-z0-9][a-z0-9-]*$" $key)) (eq $key "home") }}
{{- fail (printf "contents.%s: 이름은 소문자/숫자/- 만 쓸 수 있고 'home' 은 예약어입니다" $key) }}
{{- end }}
{{- if not (and (kindIs "map" $raw) $raw.repoUrl) }}
{{- fail (printf "contents.%s: repoUrl 이 없습니다" $key) }}
{{- end }}
{{- $m := merge (deepCopy $raw) (dict "key" $key "title" $key "repoRef" "main" "startPath" "content" "order" 100 "tabs" (list) "attributes" (dict)) }}
{{- $sortKey := printf "%06d-%s" (int $m.order) $key }}
{{- $_ := set $byKey $sortKey $m }}
{{- $sortKeys = append $sortKeys $sortKey }}
{{- end }}
{{- $items := list }}
{{- range sortAlpha $sortKeys }}
{{- $items = append $items (index $byKey .) }}
{{- end }}
{{- toJson (dict "items" $items) }}
{{- end -}}

{{/*
Antora 속성(YAML). common 위에 extra 를 덮어쓰고 각 값을 tpl 로 렌더링한다.
인자: dict "common" <map> "extra" <map> "ctx" <tpl 컨텍스트>
*/}}
{{- define "showroom.attributes" -}}
{{- $merged := merge (deepCopy (.extra | default dict)) (deepCopy .common) }}
{{- $rendered := dict }}
{{- range $k, $v := $merged }}
{{- $_ := set $rendered $k (tpl (toString $v) $.ctx) }}
{{- end }}
{{- toYaml $rendered }}
{{- end -}}

{{/*
nookbag ui-config. 공통 탭 뒤에 모듈 탭을 이름 중복 없이 붙인다.
인자: dict "root" $ "modules" <list> "ctx" <tpl 컨텍스트>
*/}}
{{- define "showroom.uiConfig" -}}
{{- $tabs := .root.Values.ui.tabs }}
{{- range .modules }}
{{- $tabs = concat $tabs .tabs }}
{{- end -}}
type: showroom
default_width: {{ .root.Values.ui.defaultWidth }}
persist_url_state: true
# 왼쪽 패널 경로 = ./<dir>/<name>/<p>.html
# showroom-content 가 만드는 www/www → www 심볼릭 링크를 이용해 name 을 사이트 루트로 둔다.
# 그래야 다른 컴포넌트로 이동해도 p 가 "agentops/main/index" 처럼 저장되어 새로고침이 유지된다.
# 시작 페이지는 modules 첫 항목(home 컴포넌트)이다.
antora:
  dir: www
  name: www
  modules:
    - name: home/main/index
tabs:
{{- $seen := dict }}
{{- range $tabs }}
{{- if not (hasKey $seen .name) }}
{{- $_ := set $seen .name true }}
  - name: {{ .name | quote }}
    url: {{ tpl .url $.ctx | quote }}
    {{- if .external }}
    external: true
    {{- end }}
{{- end }}
{{- end }}
{{- end -}}

{{/*
통합 Antora playbook. 첫 source 는 home 컴포넌트여야 한다
(showroom-content 가 sources[0].start_path 의 antora.yml 로 빌드 완료 여부를 판단한다).
*/}}
{{- define "showroom.site" -}}
site:
  title: {{ .root.Values.site.title | quote }}
  start_page: home::index.adoc
content:
  sources:
    - url: /showroom/repo
      branches: HEAD
      start_path: home
    {{- range .modules }}
    - url: /showroom/sources/{{ .key }}
      branches: HEAD
      start_path: {{ .startPath }}
    {{- end }}
ui:
  bundle:
    url: {{ .root.Values.site.uiBundleUrl }}
    snapshot: true
runtime:
  cache_dir: /tmp/.cache/antora
output:
  dir: /showroom/www
{{- end -}}

{{/*
사용자별 ConfigMap(showroom-site) data. 빌드 init 컨테이너가 /config 로 읽는다.
인자: dict "root" $ "modules" <list> "ctx" <tpl 컨텍스트>
*/}}
{{- define "showroom.siteData" -}}
modules.txt: |
  {{- range .modules }}
  {{ .key }} {{ .repoUrl }} {{ .repoRef }} {{ .startPath }}
  {{- end }}
{{- range .modules }}
attrs-{{ .key }}.yml: |
  {{- include "showroom.attributes" (dict "common" $.root.Values.commonAttributes "extra" .attributes "ctx" $.ctx) | nindent 2 }}
{{- end }}
site.yml: |
  {{- include "showroom.site" . | nindent 2 }}
home-antora.yml: |
  {{- include "showroom.homeAntora" . | nindent 2 }}
home-index.adoc: |
  {{- include "showroom.homeIndex" . | nindent 2 }}
home-nav.adoc: |
  {{- include "showroom.homeNav" . | nindent 2 }}
clone.sh: |
  {{- .root.Files.Get "files/clone.sh" | nindent 2 }}
build.sh: |
  {{- .root.Files.Get "files/build.sh" | nindent 2 }}
{{- end -}}

{{/*
home 컴포넌트: 등록된 워크샵 목록
*/}}
{{- define "showroom.homeAntora" -}}
name: home
title: {{ .root.Values.site.title | quote }}
version: main
nav:
  - modules/ROOT/nav.adoc
asciidoc:
  attributes:
    {{- include "showroom.attributes" (dict "common" .root.Values.commonAttributes "ctx" .ctx) | nindent 4 }}
{{- end -}}

{{- define "showroom.homeIndex" -}}
= {{ .root.Values.site.title }}

`{user}` 님, 환영합니다. 진행할 워크샵을 선택하세요.

{{ range .modules -}}
* xref:{{ .key }}::index.adoc[{{ .title }}]
{{ end }}
{{- end -}}

{{- define "showroom.homeNav" -}}
* xref:index.adoc[워크샵 홈]
{{ range .modules -}}
* xref:{{ .key }}::index.adoc[{{ .title }}]
{{ end }}
{{- end -}}
