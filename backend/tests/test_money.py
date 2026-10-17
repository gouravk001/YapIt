from __future__ import annotations

from app.resolvers.money import resolve_money


def test_resolve_default_inr():
    res = resolve_money("five hundred")
    assert res == {"amount": 500.0, "currency": "INR"}

    res_num = resolve_money("500")
    assert res_num == {"amount": 500.0, "currency": "INR"}


def test_resolve_rupees():
    res = resolve_money("500 rupees")
    assert res == {"amount": 500.0, "currency": "INR"}

    res_symbol = resolve_money("₹1200")
    assert res_symbol == {"amount": 1200.0, "currency": "INR"}

    res_rs = resolve_money("rs 250")
    assert res_rs == {"amount": 250.0, "currency": "INR"}


def test_resolve_indian_units():
    # 1.5 lakh = 150,000
    res_lakh = resolve_money("1.5 lakh")
    assert res_lakh == {"amount": 150000.0, "currency": "INR"}

    res_two_lakh = resolve_money("two lakh rupees")
    assert res_two_lakh == {"amount": 200000.0, "currency": "INR"}

    # crore = 10,000,000
    res_crore = resolve_money("1 crore")
    assert res_crore == {"amount": 10000000.0, "currency": "INR"}

    # k = 1000
    res_k = resolve_money("5k")
    assert res_k == {"amount": 5000.0, "currency": "INR"}


def test_resolve_foreign_currencies():
    res_dollar = resolve_money("$45")
    assert res_dollar == {"amount": 45.0, "currency": "USD"}

    res_dollars = resolve_money("fifty dollars")
    assert res_dollars == {"amount": 50.0, "currency": "USD"}

    res_euro = resolve_money("100 euros")
    assert res_euro == {"amount": 100.0, "currency": "EUR"}

    res_pound = resolve_money("£25")
    assert res_pound == {"amount": 25.0, "currency": "GBP"}


def test_resolve_dict_input():
    res = resolve_money({"amount": "750", "currency": "INR"})
    assert res == {"amount": 750.0, "currency": "INR"}

    res_missing_curr = resolve_money({"amount": "300"})
    assert res_missing_curr == {"amount": 300.0, "currency": "INR"}

