from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable


class ValidationError(ValueError):
    """Raised when business input does not match the agreed data contract."""


def require_text(value: object, field_name: str) -> str:
    if not isinstance(field_name, str) or not field_name.strip():
        raise ValueError("field_name must be non-empty text")
    if value is None:
        raise ValidationError(f"{field_name}不能为空")
    if not isinstance(value, str):
        value = str(value)
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{field_name}不能为空")
    assert cleaned
    return cleaned


def parse_non_negative_int(value: object, field_name: str) -> int:
    text = require_text(value, field_name)
    try:
        result = int(text.replace(",", ""))
    except ValueError as exc:
        raise ValidationError(f"{field_name}必须是整数") from exc
    if result < 0:
        raise ValidationError(f"{field_name}不能小于0")
    assert result >= 0
    return result


def parse_non_negative_decimal(value: object, field_name: str) -> Decimal:
    text = require_text(value, field_name).replace(",", "")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name}必须是数字") from exc
    if result < Decimal("0"):
        raise ValidationError(f"{field_name}不能小于0")
    assert result >= Decimal("0")
    return result


def require_choice(value: object, field_name: str, allowed_values: Iterable[str]) -> str:
    text = require_text(value, field_name)
    allowed = tuple(allowed_values)
    if text not in allowed:
        raise ValidationError(f"{field_name}只能填写：{', '.join(allowed)}")
    assert text in allowed
    return text


def ensure_runtime_dirs(paths: Iterable[Path]) -> None:
    for path_value in paths:
        if not isinstance(path_value, Path):
            raise TypeError("runtime path must be pathlib.Path")
        path_value.mkdir(parents=True, exist_ok=True)
        if not path_value.exists():
            raise AssertionError(f"failed to create {path_value}")


@dataclass(frozen=True)
class ProcessingResult:
    module: str
    output_rows: list[dict[str, str]]
    summary: dict[str, str]
    warnings: list[str]

    def __post_init__(self) -> None:
        if not self.module.strip():
            raise ValueError("module must not be empty")
        if not isinstance(self.output_rows, list):
            raise TypeError("output_rows must be list")
        if not isinstance(self.summary, dict):
            raise TypeError("summary must be dict")
        if not isinstance(self.warnings, list):
            raise TypeError("warnings must be list")


@dataclass(frozen=True)
class Scenario:
    key: str
    name: str
    priority: str
    brand: str
    business_type: str
    description: str
    required_fields: tuple[str, ...]
    template_path: Path

    def __post_init__(self) -> None:
        for field_name, value in (
            ("key", self.key),
            ("name", self.name),
            ("priority", self.priority),
            ("brand", self.brand),
            ("business_type", self.business_type),
            ("description", self.description),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be non-empty text")
        if not self.required_fields:
            raise ValueError("required_fields must not be empty")
        if not isinstance(self.template_path, Path):
            raise TypeError("template_path must be pathlib.Path")

