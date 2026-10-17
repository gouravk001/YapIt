from __future__ import annotations

from app.config.types_config import FieldDefinition, TypeDefinition
from app.pipeline.validate import validate


def _sample_payment_type() -> TypeDefinition:
    return TypeDefinition(
        name="payment",
        version=1,
        description="Payment between people",
        fields=[
            FieldDefinition(
                name="person",
                field_type="person",
                required=True,
                description="The other person",
            ),
            FieldDefinition(
                name="direction",
                field_type="enum",
                required=True,
                description="Direction of debt",
                allowed_values=["they_owe_me", "i_owe_them"],
            ),
            FieldDefinition(
                name="amount",
                field_type="money",
                required=True,
                description="Amount",
            ),
            FieldDefinition(
                name="due_date",
                field_type="date",
                required=False,
                description="Due date",
            ),
        ],
    )


def test_validate_complete_fields():
    type_def = _sample_payment_type()
    fields = {
        "person": "Ravi",
        "direction": "they_owe_me",
        "amount": {"amount": 500.0, "currency": "INR"},
        "due_date": {"spoken": "next Friday", "resolved": "2026-10-23"},
    }
    missing = validate(fields, type_def)
    assert missing == []


def test_validate_missing_required_field():
    type_def = _sample_payment_type()
    fields = {
        "direction": "they_owe_me",
        "amount": {"amount": 500.0, "currency": "INR"},
    }
    missing = validate(fields, type_def)
    assert missing == ["person"]


def test_validate_invalid_enum():
    type_def = _sample_payment_type()
    fields = {
        "person": "Ravi",
        "direction": "invalid_direction",
        "amount": {"amount": 500.0, "currency": "INR"},
    }
    missing = validate(fields, type_def)
    assert missing == ["direction"]

