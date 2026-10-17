from __future__ import annotations

from app.config.loader import load_types
from app.pipeline.schema_builder import build_classification_schema, build_extraction_schema


def test_build_classification_schema():
    types = ["payment", "promise", "event", "info", "general"]
    schema = build_classification_schema(types)
    assert schema["type"] == "object"
    assert "type_name" in schema["properties"]
    assert schema["properties"]["type_name"]["enum"] == types


def test_build_extraction_schema_from_types():
    types = load_types()
    payment_type = next(t for t in types if t.name == "payment")
    schema = build_extraction_schema(payment_type)

    assert schema["type"] == "object"
    assert "person" in schema["properties"]
    assert "direction" in schema["properties"]
    assert "amount" in schema["properties"]
    assert schema["properties"]["direction"]["enum"] == ["they_owe_me", "i_owe_them"]
    assert "person" in schema["required"]
    assert "amount" in schema["required"]

