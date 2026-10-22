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


class WorkshopIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    contents: list[str] = Field(min_length=1, max_length=20)
    userStart: int = Field(default=1, ge=1, le=1000)
    userCount: int = Field(default=20, ge=1, le=200)
