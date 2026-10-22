"""API 요청 스키마."""
import re

from pydantic import BaseModel, Field, field_validator

NAME_PATTERN = r"^[a-z0-9][a-z0-9-]{0,40}$"
RESERVED_NAMES = {"home"}

# 탭 URL·속성 값은 Helm tpl 로 렌더링되므로 허용한 자리표시자만 쓸 수 있게 한다
TEMPLATE_EXPR = re.compile(r"\{\{.*?\}\}")
ALLOWED_PLACEHOLDERS = {"{{ .domain }}", "{{ .user }}", "{{ .apiUrl }}"}


def check_placeholders(value: str) -> str:
    unknown = [expr for expr in TEMPLATE_EXPR.findall(value) if expr not in ALLOWED_PLACEHOLDERS]
    if unknown or "{{" in TEMPLATE_EXPR.sub("", value):
        raise ValueError(f"사용할 수 있는 자리표시자는 {', '.join(sorted(ALLOWED_PLACEHOLDERS))} 뿐입니다")
    return value


class Tab(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    url: str = Field(pattern=r"^https://[^\s{}]*(\{\{ \.[a-zA-Z]+ \}\}[^\s{}]*)*$", max_length=500)
    external: bool = True

    @field_validator("url")
    @classmethod
    def allowed_placeholders(cls, value: str) -> str:
        return check_placeholders(value)


class CatalogIn(BaseModel):
    name: str = Field(pattern=NAME_PATTERN)
    repoUrl: str = Field(pattern=r"^https://\S+$", max_length=500)
    repoRef: str = Field(default="main", pattern=r"^[A-Za-z0-9._/-]{1,100}$")
    startPath: str = Field(default="content", pattern=r"^[A-Za-z0-9._/-]{1,100}$")
    title: str | None = Field(default=None, max_length=120)
    tabs: list[Tab] = Field(default_factory=list, max_length=10)
    attributes: dict[str, str] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def not_reserved(cls, value: str) -> str:
        if value in RESERVED_NAMES:
            raise ValueError("'home' 은 예약된 이름입니다")
        return value

    @field_validator("attributes")
    @classmethod
    def valid_attribute_keys(cls, value: dict[str, str]) -> dict[str, str]:
        for key, attr in value.items():
            if not key or not all(ch.isalnum() or ch in "-_" for ch in key):
                raise ValueError(f"속성 이름이 올바르지 않습니다: {key!r}")
            check_placeholders(attr)
        return value


# 목차 항목 이름은 AsciiDoc 링크 대괄호 안에 들어가므로 ] 와 줄바꿈을 막는다
LABEL_PATTERN = r"^[^\]\r\n]+$"


def _label(value: str) -> str:
    value = value.strip()
    if value and not re.fullmatch(LABEL_PATTERN, value):
        raise ValueError("이름에는 ] 와 줄바꿈을 쓸 수 없습니다")
    if len(value) > 60:
        raise ValueError("이름은 60자 이하여야 합니다")
    return value


class NavLink(BaseModel):
    name: str = Field(min_length=1, max_length=60, pattern=LABEL_PATTERN)
    url: str = Field(pattern=r"^https://[^\s\[\]]+$", max_length=500)


class WorkshopIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    contents: list[str] = Field(min_length=1, max_length=20)
    userStart: int = Field(default=1, ge=1, le=1000)
    userCount: int = Field(default=20, ge=1, le=200)
    # Showroom 첫 화면. 비우면 워크샵 제목과 기본 환영 문구를 쓴다.
    homeTitle: str = Field(default="", max_length=120)
    # 첫 화면 전체(AsciiDoc). 비우면 제목·환영 문구·콘텐츠 목록을 자동으로 만든다
    homePage: str = Field(default="", max_length=50_000)
    homeLabel: str = Field(default="", max_length=60)
    # 목차·첫 화면에 표시할 콘텐츠 이름 {콘텐츠: 이름}. 없으면 카탈로그 제목
    contentLabels: dict[str, str] = Field(default_factory=dict)
    navLinks: list[NavLink] = Field(default_factory=list, max_length=10)

    @field_validator("homeLabel")
    @classmethod
    def valid_home_label(cls, value: str) -> str:
        return _label(value)

    @field_validator("contentLabels")
    @classmethod
    def valid_content_labels(cls, value: dict[str, str]) -> dict[str, str]:
        return {name: label for name, label in ((n, _label(v)) for n, v in value.items()) if label}

    @field_validator("homeTitle")
    @classmethod
    def single_line(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("목차 제목은 한 줄이어야 합니다")
        return value.strip()


class PageIn(BaseModel):
    """행사별 페이지 수정. 경로 검사는 콘텐츠 경로를 알아야 하므로 API 에서 한다."""
    path: str = Field(min_length=1, max_length=300)
    text: str = Field(max_length=200_000)
