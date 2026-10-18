from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class FieldDefinition(BaseModel):
    name: str
    field_type: Literal["text", "number", "money", "date", "person", "enum", "list"]
    required: bool
    description: str
    allowed_values: list[str] | None = None
    # Plain-language wording the LLM chooses between instead of the stored enum values, which
    # are easy for a small model to confuse (e.g. they_owe_me vs i_owe_them).
    value_labels: dict[str, str] | None = None
    item_type: str | None = None

    @model_validator(mode="after")
    def _labels_match_values(self) -> FieldDefinition:
        unknown = set(self.value_labels or {}) - set(self.allowed_values or [])
        if unknown:
            raise ValueError(f"value_labels has keys not in allowed_values: {sorted(unknown)}")
        return self

    def llm_choices(self) -> list[str]:
        labels = self.value_labels or {}
        return [labels.get(value, value) for value in self.allowed_values or []]

    def to_llm_value(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return (self.value_labels or {}).get(value, value)

    def from_llm_value(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        by_label = {label: stored for stored, label in (self.value_labels or {}).items()}
        return by_label.get(value, value)


class TypeExample(BaseModel):
    transcript: str
    expected_fields: dict[str, Any]


class TypeDefinition(BaseModel):
    name: str
    version: int
    description: str
    fields: list[FieldDefinition]
    examples: list[TypeExample] = Field(default_factory=list)
