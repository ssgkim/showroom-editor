"""워크샵 정의(workshop.yaml) 스키마.

점검 유형은 아래 CHECK_TYPES 로 정해 두고, 정의 파일에서 임의 스크립트를 실행하지 않는다.
"""
import re
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

CHECK_TYPES = ("operator", "clusterVersion", "gpuNodes", "resource", "http", "capacity")
TEMPLATE_EXPR = re.compile(r"\{\{.*?\}\}")
ALLOWED_PLACEHOLDERS = {"{{ .domain }}", "{{ .user }}"}


def _check_placeholders(value: Any) -> None:
    if isinstance(value, str):
        unknown = [e for e in TEMPLATE_EXPR.findall(value) if e not in ALLOWED_PLACEHOLDERS]
        if unknown:
            raise ValueError(f"허용되지 않는 자리표시자: {', '.join(unknown)} (사용 가능: {{{{ .domain }}}}, {{{{ .user }}}})")
    elif isinstance(value, dict):
        for item in value.values():
            _check_placeholders(item)
    elif isinstance(value, list):
        for item in value:
            _check_placeholders(item)


class Check(BaseModel):
    """type 에 따라 쓰는 필드가 다르다. 나머지 필드는 그대로 점검기에 전달된다."""

    model_config = {"extra": "allow"}
    type: Literal[CHECK_TYPES]

    @model_validator(mode="after")
    def placeholders(self) -> "Check":
        # 추가 필드(model_extra)까지 모두 검사한다
        _check_placeholders(self.model_dump())
        return self

    def params(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if k != "type"}


class About(BaseModel):
    summary: str = ""
    audience: str = ""
    duration: str = ""
    level: str = ""


class Requirement(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    check: Check
    # required: 실패 시 ❌, recommended: 실패 시 ⚠️
    severity: Literal["required", "recommended"] = "required"
    fix: str = ""


class Checkpoint(BaseModel):
    module: int | str
    name: str = Field(min_length=1, max_length=120)
    check: Check


class WorkshopDefinition(BaseModel):
    about: About = Field(default_factory=About)
    requirements: list[Requirement] = Field(default_factory=list, max_length=50)
    checkpoints: list[Checkpoint] = Field(default_factory=list, max_length=100)


class DefinitionError(Exception):
    pass


def parse_definition(text: str) -> WorkshopDefinition:
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise DefinitionError(f"YAML 오류: {exc}") from exc
    if not isinstance(data, dict):
        raise DefinitionError("최상위는 about / requirements / checkpoints 를 가진 객체여야 합니다")
    try:
        return WorkshopDefinition.model_validate(data)
    except ValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first["loc"])
        raise DefinitionError(f"{location}: {first['msg']}") from exc


class DefinitionIn(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
