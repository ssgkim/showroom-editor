# Showroom Editor 사용 매뉴얼

인스트럭터가 워크샵 콘텐츠를 골라 **사용자마다 같은 Showroom**을 배포하는 도구입니다.
여러 워크샵 저장소(Showroom/Antora 형식)를 하나의 사이트로 합쳐 줍니다.

```text
01 콘텐츠 카탈로그  →  02 워크샵 구성  →  03 미리보기 · 배포
   git 주소 등록         행사별 콘텐츠·순서·      미리보기로 확인 후
   (형식 자동 검사)      사용자 범위 결정         user1~N 에 배포
```

---

## 1. 설치

### 준비 사항

| 항목 | 내용 |
|---|---|
| PC | `oc` CLI |
| 계정 | 대상 클러스터의 cluster-admin |
| 클러스터 | OpenShift 4.x, 내부 이미지 레지스트리 사용 가능, 외부 인터넷 접속 가능 (GitHub, quay.io, registry.access.redhat.com, get.helm.sh) |

### 설치 명령 (클러스터마다 1회)

```bash
oc login https://api.<클러스터>:6443 -u <cluster-admin 계정>
curl -sL https://raw.githubusercontent.com/ssgkim/showroom-editor/main/editor/deploy.sh | bash
```

- 클러스터가 GitHub 저장소를 직접 가져와 이미지를 빌드합니다. 3~5분 걸립니다.
- 끝나면 접속 주소가 출력됩니다: `https://showroom-editor-showroom-editor.<클러스터 도메인>`
- 클러스터 도메인과 API 주소는 에디터가 자동으로 읽습니다. 따로 설정할 것이 없습니다.

| 옵션 | 사용법 |
|---|---|
| 특정 브랜치/태그 | `... \| SHOWROOM_EDITOR_REF=v1.0 bash` |
| 포크한 저장소 | `... \| SHOWROOM_EDITOR_REPO=myorg/showroom-editor bash` |
| 로컬 코드로 빌드 (개발용) | 저장소 안에서 `./editor/deploy.sh --local` |

### 업데이트

설치 명령을 그대로 다시 실행합니다. 등록한 카탈로그와 워크샵 구성은 유지됩니다.

> GitHub 에 push 한 직후에는 raw 주소가 몇 분간 캐시되어 이전 스크립트가 내려올 수 있습니다. 몇 분 뒤에 실행하세요.

### 삭제

1. 에디터에서 **배포 해제**와 미리보기 **삭제**를 먼저 실행합니다(사용자 Showroom 정리).
2. 에디터를 삭제합니다. 카탈로그와 워크샵 구성도 함께 삭제됩니다.

   ```bash
   oc delete -f https://raw.githubusercontent.com/ssgkim/showroom-editor/main/editor/deploy/editor.yaml
   ```

---

## 2. 접속과 권한

- 에디터 주소로 접속하면 **OpenShift 로그인** 화면이 나옵니다. 클러스터 계정으로 로그인합니다.
- 처음 로그인하면 "사용자 정보와 권한 확인을 허용하겠습니까?" 화면이 한 번 나옵니다. **허용**을 누릅니다.
- 사용할 수 있는 사람: `showroom-editor` 네임스페이스를 볼 수 있는 사용자
  - cluster-admin 은 기본으로 사용할 수 있습니다.
  - 인스트럭터 그룹을 추가하려면:

    ```bash
    oc adm policy add-role-to-group view <인스트럭터 그룹> -n showroom-editor
    ```

---

## 3. 화면 구성

```text
┌ Showroom Editor ─────────────────── 클러스터: apps.xxx │ 배포 중: … │ [한국어|English] ┐
│ 01 콘텐츠 카탈로그   │ 02 워크샵 구성               │ 03 미리보기 · 배포 상태          │
│  등록된 콘텐츠 목록   │  워크샵 탭 (+ 새 워크샵)      │  미리보기 카드 (상태, 주소)       │
│  새 콘텐츠 등록 폼    │  제목·ID·사용자 범위          │  배포 카드 (사용자별 상태)        │
│                      │  포함된 콘텐츠 / 추가 가능     │  빌드 로그                        │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

- **언어 전환**: 오른쪽 위 `한국어 | English`. 선택은 브라우저에 기억됩니다.
- **위험한 동작**(배포, 배포 해제, 삭제, 전체 재시작)은 버튼을 **두 번** 눌러야 실행됩니다. 첫 클릭에서 버튼이 빨간 확인 문구로 바뀌고, 4초 안에 다시 누르면 실행됩니다.

---

## 4. 콘텐츠 등록 (01 콘텐츠 카탈로그)

워크샵 저장소를 카탈로그에 등록합니다. 등록할 때 저장소를 실제로 clone 해서 형식을 검사합니다.

| 항목 | 필수 | 설명 |
|---|---|---|
| 이름 | ✔ | 소문자, 숫자, `-` (최대 41자). **사이트 안의 URL 경로**가 됩니다(`/<이름>/main/...`). `home` 은 사용할 수 없습니다. |
| git 주소 | ✔ | `https://` 로 시작하는 **공개** 저장소 주소 |
| 브랜치/태그 | | 기본 `main` |
| 콘텐츠 경로 | | `antora.yml` 이 있는 폴더. 기본 `content` |
| 제목 | | 홈 화면 목록에 표시. 비우면 저장소 `antora.yml` 의 `title` |
| 추가 탭 | | 이 콘텐츠를 넣었을 때 오른쪽에 추가할 탭 |
| Antora 속성 | | 이 콘텐츠 페이지에만 넣을 값 |

### 콘텐츠 저장소 요건

- RHDP Showroom 템플릿 형식: `<콘텐츠 경로>/antora.yml` 과 `modules/` 가 있어야 합니다.
- 저장소의 `antora.yml` 컴포넌트 이름이 무엇이든(예: `modules`) 빌드할 때 등록한 **이름**으로 바뀌므로, 저장소를 고칠 필요가 없습니다.

### 탭과 속성 입력 형식 (「탭 · 속성 (선택)」을 펼침)

```text
추가 탭 (한 줄에 하나:  이름 | URL)
MLflow Console | https://mlflow-server.{{ .domain }}/

Antora 속성 (한 줄에 하나:  이름 = 값)
demo-ns = demo-{{ .user }}
llm_api_key = <MaaS API 키>
```

값에 쓸 수 있는 자리표시자는 세 가지뿐입니다. 사용자마다 다른 값으로 바뀝니다.

| 자리표시자 | 바뀌는 값 (예) |
|---|---|
| `{{ .domain }}` | `apps.ocp.xxxx.opentlc.com` |
| `{{ .user }}` | `user7` |
| `{{ .apiUrl }}` | `https://api.ocp.xxxx.opentlc.com:6443` |

모든 콘텐츠에 공통으로 들어가는 속성(직접 넣지 않아도 됨): `user`, `guid`, `openshift_cluster_ingress_domain`, `openshift_api_url`, `openshift_cluster_console_url`, `rhoai_dashboard_url`, `login_command`. 모든 Showroom 에 공통으로 들어가는 탭: **OpenShift AI Dashboard**, **OpenShift Console**.

### 수정과 삭제

- **수정**: 같은 이름으로 다시 등록하면 덮어씁니다(다시 검사함).
- **삭제**: 카드의 **삭제**. 워크샵에서 쓰고 있는 콘텐츠는 삭제할 수 없습니다. 먼저 워크샵에서 빼세요.

---

## 5. 워크샵 구성 (02 워크샵 구성)

행사(차수)마다 워크샵을 하나씩 만듭니다. 여러 개를 저장해 두고 골라 쓸 수 있습니다.

1. **+ 새 워크샵** 탭을 누릅니다. 저장된 워크샵을 고치려면 해당 탭을 누릅니다.
2. 입력합니다.

   | 항목 | 설명 |
   |---|---|
   | 워크샵 제목 | 사이트 제목과 홈 화면 제목이 됩니다. |
   | ID | 소문자, 숫자, `-`. 처음 저장한 뒤에는 바꿀 수 없습니다. |
   | 시작 사용자 / 사용자 수 | 예: 1 / 20 → `user1 ~ user20`. 아래에 실제 범위와 주소가 표시됩니다. |

3. **추가할 수 있는 콘텐츠**에서 `+` 를 눌러 넣고, **포함된 콘텐츠**에서 `↑ ↓` 로 순서를, `✕` 로 빼기를 합니다. 순서가 홈 화면 목록 순서입니다.
4. **저장**을 누릅니다. (미리보기·배포 버튼도 먼저 저장합니다.)

- 워크샵 삭제: **워크샵 삭제**. 현재 배포 중인 워크샵은 삭제할 수 없습니다. 먼저 배포를 해제하세요.

### 행사별 페이지 수정

원본 저장소를 고치지 않고 **이 워크샵에서만** 페이지 내용을 바꿉니다. 예: 행사 일정 안내 추가, 사내 환경에 맞춘 문구·주의 사항 수정.
참가자 로그인과 행사 공지는 RHDP 워크샵 페이지(`catalog.demo.redhat.com/workshop/...`)가 제공하므로 여기서는 콘텐츠 본문만 다룹니다.

1. 워크샵을 **저장**한 뒤, 포함된 콘텐츠 줄의 **✎** 를 누릅니다. (수정한 파일 수가 빨간 숫자로 표시됩니다.)
2. 왼쪽 목록에서 페이지(`.adoc`)를 골라 고칩니다. **원본과 나란히 보기**로 원본과 비교할 수 있습니다.
3. **저장**합니다. 이 단계에서는 Showroom 이 바뀌지 않습니다.
4. **저장 후 미리보기**로 확인하고, **저장 후 배포**(이미 배포 중이면 **전체 재시작**)로 반영합니다.

- 목록 표시: `●` 수정함, `⚠` 수정한 뒤 원본 저장소의 같은 파일이 바뀜 → 원본과 비교해 다시 저장하거나 되돌리세요. 수정한 파일이 그대로 원본을 덮어쓰므로 원본의 새 내용은 반영되지 않습니다.
- **원본으로 되돌리기**: 수정을 지웁니다(두 번 눌러 확정).
- 수정할 수 있는 파일: 콘텐츠 경로 아래의 기존 `.adoc` 파일(페이지, `nav.adoc`, partials). 새 파일 추가와 이미지 교체는 지원하지 않습니다.
- 수정 내용은 ConfigMap `showroom-editor-overlays` 에 저장되며 전체 900KB 까지입니다. 워크샵을 삭제하면 함께 지워집니다.

---

## 6. 미리보기

**저장 후 미리보기**를 누르면 미리보기 전용 Showroom 하나를 만듭니다.

- 주소: `https://showroom-showroom-preview1.<클러스터 도메인>` (미리보기 카드에 링크 표시)
- 1~2분 뒤 상태가 **준비됨**이 되면 링크를 눌러 확인합니다.
- 다른 워크샵으로 미리보기를 하면 같은 미리보기 Showroom 이 그 워크샵으로 바뀝니다.
- 다 봤으면 미리보기 카드의 **삭제**로 지울 수 있습니다.

---

## 7. 배포

**저장 후 배포**를 두 번 누르면 워크샵의 사용자 범위 전체에 Showroom 을 만듭니다.

- 사용자 주소: `https://showroom-showroom-user<N>.<클러스터 도메인>` (네임스페이스 `showroom-user<N>`)
- 상단의 **배포 중**에 현재 배포된 워크샵이 표시되고, 워크샵 탭에 빨간 점이 붙습니다.
- 클러스터당 배포는 **한 번에 한 워크샵**입니다. 다른 워크샵을 배포하면 같은 사용자 Showroom 이 그 워크샵으로 바뀝니다.

| 하고 싶은 일 | 방법 |
|---|---|
| 사용자 추가 | 사용자 수를 늘리고 다시 배포 |
| 사용자 축소 | 범위를 줄이고 다시 배포 → **범위 밖 사용자 Showroom 은 삭제됨** |
| 콘텐츠 추가·제거·순서 변경 | 구성을 바꾸고 다시 배포 → 모든 사용자 Showroom 이 다시 빌드됨 |
| 콘텐츠 저장소의 본문 수정 반영 | 배포 카드의 **전체 재시작** (설정이 그대로면 자동으로 다시 빌드되지 않음) |
| 모두 정리 | **배포 해제** → 모든 사용자 Showroom 네임스페이스 삭제 |

> 다시 빌드되는 동안(1~2분) 수강생 화면이 잠시 접속되지 않습니다. 수업 중에는 주의하세요.

---

## 8. 상태 확인과 빌드 로그

미리보기·배포 카드에 사용자별 상태가 4초마다 갱신됩니다. 사용자 이름을 누르면 그 사용자의 Showroom 이 열립니다.

| 상태 | 의미 |
|---|---|
| 대기 | Pod 생성 대기 |
| 저장소 가져오는 중 | 콘텐츠 저장소 clone 중 |
| Antora 빌드 중 | 사이트 빌드 중 |
| 시작 중 | 화면 서버 시작 중 |
| 준비됨 | 접속 가능 |
| 실패 | **눌러서 빌드 로그 확인** (clone, build 각각 마지막 80줄) |
| 삭제 중 | 정리 중 |

배포 카드 위에 `준비됨 18 / 20 · 실패 2` 처럼 집계가 표시됩니다.

---

## 9. 수강생에게 보이는 화면

- 왼쪽: 가이드. 첫 화면은 **워크샵 목록(home)** 이고, 누르면 각 워크샵으로 들어갑니다. 새로고침해도 보던 페이지가 유지됩니다.
- 오른쪽: 탭 (OpenShift AI Dashboard, OpenShift Console, 콘텐츠별 추가 탭).
- 페이지 안의 사용자 이름, 클러스터 주소, 로그인 명령 등은 수강생별 값으로 채워져 있습니다.
- 비밀번호는 저장하지 않으므로 페이지에는 `<안내받은 비밀번호>` 로 표시됩니다. 비밀번호는 별도로 안내하세요.

---

## 10. 문제 해결

| 증상 | 원인 / 조치 |
|---|---|
| 설치 중 "먼저 클러스터에 로그인하세요" | `oc login` 후 다시 실행 |
| 설치 중 "cluster-admin 권한이 필요합니다" | cluster-admin 계정으로 로그인 |
| 에디터 접속 시 로그인 후 403 | 접근 권한 없음 → `oc adm policy add-role-to-group view <그룹> -n showroom-editor` |
| 카탈로그 등록: "antora.yml 이 없습니다" | Showroom 형식이 아니거나 **콘텐츠 경로**가 다름 |
| 카탈로그 등록: git 오류 | 주소·브랜치 확인. 비공개 저장소는 지원하지 않음 |
| 탭/속성 등록 오류 | 형식(`이름 \| URL`, `이름 = 값`)과 자리표시자 3종만 쓰는지 확인 |
| 사용자 상태가 **실패** | 상태를 눌러 로그 확인. clone 실패는 저장소 접근, build 실패는 콘텐츠의 Antora 오류 |
| 콘텐츠를 고쳤는데 반영 안 됨 | 배포 카드의 **전체 재시작** |

---

## 11. 제약 사항

- 클러스터당 배포되는 워크샵은 하나입니다(사용자 Showroom 이 하나이므로).
- 콘텐츠 저장소는 공개(public) https 저장소만 지원합니다.
- 합친 사이트는 UI 확장(supplemental UI)을 하나만 쓸 수 있어, 저장소별 UI 확장(예: agentops 의 `lab-vars.js` 입력 폼)은 동작하지 않습니다. 필요한 값은 카탈로그 **Antora 속성**으로 넣으세요.
- 서버가 보내는 오류 문구는 한국어로만 표시됩니다.

---

## 12. 데이터 백업과 복원

카탈로그와 워크샵 구성은 `showroom-editor` 네임스페이스의 ConfigMap `showroom-editor-state` 에 저장됩니다.

```bash
# 백업
oc get configmap showroom-editor-state -n showroom-editor \
  -o jsonpath='{.data.state\.json}' > showroom-editor-backup.json

# 복원 (다른 클러스터로 옮길 때도 동일, 에디터 재시작 불필요)
oc create configmap showroom-editor-state -n showroom-editor \
  --from-file=state.json=showroom-editor-backup.json --dry-run=client -o yaml | oc apply -f -
```

행사별 페이지 수정은 ConfigMap `showroom-editor-overlays` 에 따로 저장됩니다.

```bash
oc get configmap showroom-editor-overlays -n showroom-editor \
  -o jsonpath='{.data.overlays\.json}' > showroom-editor-overlays.json
oc create configmap showroom-editor-overlays -n showroom-editor \
  --from-file=overlays.json=showroom-editor-overlays.json --dry-run=client -o yaml | oc apply -f -
```

> 백업 파일의 미리보기·배포 기록은 원래 클러스터 기준입니다. 다른 클러스터에서는 워크샵을 다시 미리보기·배포하세요.

---

## 13. Workshop Ops Hub: 사전 점검

행사 전에 **이 클러스터에서 워크샵을 진행할 수 있는지** 자동으로 확인하는 별도 사이트입니다.
Showroom Editor 에 저장된 워크샵을 그대로 읽고, 클러스터는 **읽기만** 합니다.

### 설치

```bash
curl -sL https://raw.githubusercontent.com/ssgkim/showroom-editor/main/ops/deploy.sh | bash
```

- 주소: `https://workshop-ops-workshop-ops.<클러스터 도메인>`
- 접근 권한은 Showroom Editor 와 같습니다(`showroom-editor` 네임스페이스 view 권한).
- Showroom Editor 가 먼저 설치되어 있어야 합니다.

### 사용

1. 왼쪽 **워크샵**에서 점검할 워크샵을 고릅니다(배포 중인 워크샵이 기본 선택).
2. **워크샵 정의**에서 콘텐츠별 정의 상태를 확인합니다.

   | 표시 | 의미 |
   |---|---|
   | 저장소 | 콘텐츠 저장소 루트의 `workshop.yaml` 을 사용 |
   | 덮어씀 | Ops Hub 에서 편집한 정의를 사용 (저장소 파일보다 우선) |
   | 정의 없음 | 요구 사항 점검을 건너뜀. **편집**을 누르면 예시가 채워진 편집기가 열림 |
   | 오류 | 정의 파일 형식 오류. 편집기에서 내용 확인 |

3. **지금 점검** → 결과가 공통 / 콘텐츠별로 표시됩니다. 실패·경고 항목에는 **조치** 안내가 붙습니다.
4. **보고서 내려받기 (.md)** 로 행사 준비 체크리스트를 저장합니다.

| 판정 | 의미 |
|---|---|
| 준비 완료 (초록) | 모든 필수 항목 통과 |
| 진행 가능 (노랑) | 필수는 통과, 권장 항목 경고나 점검 불가 항목 있음 |
| 준비 안 됨 (빨강) | 필수 항목 실패 |

공통 점검(정의 없이 항상 실행): 사용자 계정(Keycloak, 없으면 OpenShift 사용자), Showroom 용 여유 자원(사용자당 CPU 100m · 메모리 256Mi), quay.io 접근, 콘텐츠 저장소 접근.

> 점검 결과는 Ops Hub 가 재시작되면 사라집니다(다시 점검). 덮어쓴 정의는 `workshop-ops` 네임스페이스의 ConfigMap `workshop-ops-overrides` 에 저장되어 유지됩니다.

### 워크샵 정의 (`workshop.yaml`) 작성법

콘텐츠 저장소 **루트**에 두거나 Ops Hub 편집기에 입력합니다.

```yaml
about:                        # 2차(갤러리)에서 사용
  summary: AI 앱을 배포하고 로그·트레이스·GPU 지표로 관찰합니다.
  audience: ML 엔지니어
  duration: 90m
  level: intermediate
requirements:                # 사전 점검 항목
  - name: OpenShift AI 3.5 이상
    check: { type: operator, package: rhods-operator, minVersion: "3.5" }
    fix: OperatorHub 에서 Red Hat OpenShift AI 를 설치하세요
  - name: GPU 노드
    check: { type: gpuNodes, min: 1 }
    severity: recommended     # 실패해도 경고(⚠️). 기본은 required(❌)
    fix: "GPU 워커 노드를 추가하세요"
checkpoints: []              # 3차(진행 현황)에서 사용
```

| check.type | 필드 | 확인 내용 |
|---|---|---|
| `operator` | `package`, `minVersion` | Operator 설치 완료(CSV Succeeded)와 버전. 설치가 멈춘 경우(예: BundleUnpackFailed) 원인을 표시 |
| `clusterVersion` | `min` | OpenShift 버전 |
| `gpuNodes` | `min`, `resource`(기본 `nvidia.com/gpu`) | GPU 를 할당할 수 있는 노드 수 |
| `resource` | `kind`, `name`, `namespace`, `labelSelector`, `ready` | 리소스 존재 / Ready 여부 |
| `http` | `url`, `expect`(기본 200·301·302·401·403) | 엔드포인트 응답 코드 (인증서 검증 안 함) |
| `capacity` | `users`, `cpuPerUser`, `memoryPerUser` | 워커 노드 여유 자원 |

- 값에 `{{ .domain }}` 을 쓸 수 있습니다(`checkpoints` 에서는 `{{ .user }}` 도).
- 정해진 점검 유형만 실행되며 임의 명령은 실행할 수 없습니다.
- YAML 값에 `: ` (콜론+공백)이 들어가면 따옴표로 감싸세요.
- API 서버 주소는 루트(`/`)가 404 인 경우가 많습니다. 상태 확인 경로를 쓰세요(예: MaaS `https://maas.{{ .domain }}/maas-api/health`, `expect: [200]`).
