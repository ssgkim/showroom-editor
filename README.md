# RHOAI 워크샵 Showroom

여러 워크샵 콘텐츠(Showroom/Antora 저장소)를 **하나의 Antora 사이트로 합쳐** 사용자마다 같은 Showroom을 배포한다.
인스트럭터는 **Showroom Editor** 화면에서 콘텐츠를 고르고, 미리보고, 배포한다. 화면은 한국어/영어로 전환할 수 있다(오른쪽 위).

- 사용자별 주소: `https://showroom-showroom-<user>.<cluster domain>` (네임스페이스 `showroom-<user>`)
- 시작 페이지: 포함된 워크샵 목록(home). 각 워크샵은 `/<콘텐츠 이름>/main/...` 경로에 들어간다.

## Showroom Editor (인스트럭터용)

```text
01 콘텐츠 카탈로그   git 주소 등록 → 저장소가 Showroom(Antora) 형식인지 검사
02 워크샵 구성       행사별로 포함할 콘텐츠와 순서, 사용자 범위(user1~N) 결정
03 미리보기 · 배포   미리보기(showroom-preview1)로 확인 → user 범위 전체에 배포, 상태·로그 확인
```

### 설치 (클러스터마다 1회, cluster-admin)

```bash
oc login <API 주소>
./editor/deploy.sh
```

- 주소: `https://showroom-editor-showroom-editor.<cluster domain>` (OpenShift 계정으로 로그인)
- 접근 허용: `showroom-editor` 네임스페이스의 services 를 볼 수 있는 사용자. cluster-admin 은 기본 허용이고, 인스트럭터 그룹은 다음과 같이 추가한다.

  ```bash
  oc adm policy add-role-to-group view <인스트럭터 그룹> -n showroom-editor
  ```

### 사용

1. **카탈로그**: 이름(URL 경로가 됨)과 git 주소를 넣고 "검사 후 등록". 필요하면 탭(`이름 | URL`)과 Antora 속성(`이름 = 값`)을 추가한다. 값에는 `{{ .domain }}`, `{{ .user }}`, `{{ .apiUrl }}` 만 쓸 수 있다.
2. **워크샵 구성**: 제목, ID, 사용자 범위를 정하고 오른쪽 목록에서 콘텐츠를 추가하고 ↑↓ 로 순서를 바꾼다.
3. **저장 후 미리보기**: `showroom-showroom-preview1` 에 1~2분 안에 빌드된다.
4. **저장 후 배포**: 버튼을 두 번 눌러 확정한다. 범위를 줄이면 범위 밖 사용자 Showroom은 삭제된다.
5. 실패한 사용자는 상태 칩을 누르면 빌드 로그(clone, build)를 볼 수 있다.
6. 콘텐츠 저장소 본문만 바뀐 경우 "전체 재시작"으로 다시 빌드한다.

## 구조

```text
Chart.yaml, values.yaml, templates/, files/   통합 Antora Showroom 차트 (사용자별 리소스 생성)
editor/                                       Showroom Editor
  app/          FastAPI 백엔드 + 정적 화면
  deploy/       에디터 배포 매니페스트 (oauth-proxy, RBAC, BuildConfig)
  deploy.sh     빌드·배포 스크립트
  tests/        pytest
bootstrap/, scripts/                          Argo CD 로 운영할 때 쓰는 대안 (아래 참고)
```

사용자 Showroom Pod 하나의 동작:

```text
init clone  (quay.io/rhpds/git-cloner)  등록된 콘텐츠 저장소 clone, home 컴포넌트 준비
init build  (quay.io/rhpds/antora)      저장소마다 컴포넌트 이름을 콘텐츠 이름으로 바꾸고 속성 주입 → 통합 빌드
content     (quay.io/rhpds/showroom-content)  nookbag 화면(가이드 + 탭)으로 서비스
```

- 콘텐츠 저장소의 `antora.yml` 이름(예: `modules`)이 같아도 빌드할 때 바뀌므로 **콘텐츠 저장소는 수정하지 않는다.**
- 에디터는 이 차트를 이미지에 포함해 `helm template` 으로 렌더링하고 `oc apply` 한다. 상태(카탈로그, 워크샵 구성)는 `showroom-editor/showroom-editor-state` ConfigMap 에 저장된다.

## 개발

```bash
cd editor
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest httpx
.venv/bin/python -m pytest -q tests      # helm 이 있으면 렌더링 테스트도 실행
```

## 대안: Argo CD 로 운영

에디터 없이 GitOps 로 운영하려면 `bootstrap/root-application.yaml` 의 `cluster.domain`, `cluster.apiUrl` 을 대상 클러스터 값으로 바꿔 적용한 뒤,
`scripts/showroom-content.sh add <이름> <git 주소>` 로 Application values 에 콘텐츠를 등록한다.
에디터와 Argo CD 를 **같은 클러스터에서 함께 쓰지 않는다** (같은 네임스페이스를 서로 덮어쓴다).

## 참고

- 사용자별 비밀번호는 저장하지 않는다(`password` 속성은 안내 문구).
- 통합 사이트는 UI 확장(supplemental UI)을 하나만 쓸 수 있으므로 콘텐츠 저장소별 `supplemental-ui`(예: agentops 의 `lab-vars.js`)는 적용되지 않는다. 필요한 값은 카탈로그의 속성으로 넣는다.
- OpenShift Console 은 `X-Frame-Options: DENY` 를 보내므로 탭은 새 창(`external: true`)으로 연다.
