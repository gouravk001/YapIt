from __future__ import annotations

from app.resolvers.people import resolve_person


def test_resolve_single_person():
    assert resolve_person("  ravi kumar  ") == "Ravi Kumar"
    assert resolve_person("priya") == "Priya"
    assert resolve_person("") is None
    assert resolve_person(None) is None


def test_resolve_people_list():
    raw_list = ["ravi", "priya sharma", "  RAVI ", "amit"]
    res = resolve_person(raw_list)
    assert res == ["Ravi", "Priya Sharma", "Amit"]


def test_speaker_is_never_a_person():
    assert resolve_person("I") is None
    assert resolve_person(" me ") is None
    assert resolve_person(["Rohit", "I", "myself"]) == ["Rohit"]
