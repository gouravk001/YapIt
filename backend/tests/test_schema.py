from __future__ import annotations

from app.config.loader import load_types
from app.pipeline.schema_builder import (
    build_classification_schema,
    build_extraction_schema,
    build_refine_schema,
)


def test_build_classification_schema():
    types = ["payment", "promise", "event", "info", "general"]
    schema = build_classification_schema(types)
    assert schema["type"] == "object"
    assert "type_name" in schema["properties"]
    assert schema["properties"]["type_name"]["enum"] == types
    assert schema["required"] == ["kind", "type_name"]
    assert schema["properties"]["kind"]["enum"][0] == "note"


def test_build_extraction_schema_from_types():
    types = load_types()
    payment_type = next(t for t in types if t.name == "payment")
    schema = build_extraction_schema(payment_type)

    assert schema["type"] == "object"
    assert "person" in schema["properties"]
    assert "direction" in schema["properties"]
    assert "amount" in schema["properties"]
    assert schema["properties"]["direction"]["enum"] == [
        "I will receive the money",
        "I will give the money",
    ]
    assert "person" in schema["required"]
    assert "amount" in schema["required"]


def test_build_refine_schema_requires_every_field_and_a_summary():
    payment_type = next(t for t in load_types() if t.name == "payment")
    schema = build_refine_schema(payment_type)

    assert schema["required"] == [
        "restatement",
        "person",
        "direction",
        "amount",
        "due_date",
        "note",
        "summary",
    ]


def test_enum_labels_are_offered_to_the_llm_and_mapped_back():
    from app.pipeline.resolve import resolve

    payment_type = next(t for t in load_types() if t.name == "payment")
    direction = next(f for f in payment_type.fields if f.name == "direction")

    schema = build_extraction_schema(payment_type)
    assert schema["properties"]["direction"]["enum"] == direction.llm_choices()

    resolved = resolve(
        {"direction": direction.value_labels["i_owe_them"]},
        payment_type,
        "Asia/Kolkata",
        "2026-10-17T10:00:00+05:30",
    )
    assert resolved["direction"] == "i_owe_them"


def test_value_labels_must_name_allowed_values():
    import pytest

    from app.config.types_config import FieldDefinition

    with pytest.raises(ValueError, match="not in allowed_values"):
        FieldDefinition(
            name="direction",
            field_type="enum",
            required=True,
            description="d",
            allowed_values=["a"],
            value_labels={"b": "label"},
        )
