import datetime
from decimal import Decimal
from fractions import Fraction

import pytest
from mock import call

from pyairtable import formulas as F
from pyairtable.formulas import AND, EQ, GT, GTE, LT, LTE, NE, NOT, OR


def test_operators():
    lft = F.Formula("a")
    rgt = F.Formula("b")
    assert str(lft) == "a"
    assert str(lft & rgt) == "AND(a, b)"
    assert str(lft | rgt) == "OR(a, b)"
    assert str(~(lft & rgt)) == "NOT(AND(a, b))"
    assert repr(lft & rgt) == "AND(Formula('a'), Formula('b'))"
    assert repr(lft | rgt) == "OR(Formula('a'), Formula('b'))"
    assert repr(~F.Formula("a")) == "NOT(Formula('a'))"
    assert lft.flatten() is lft
    assert repr(lft ^ rgt) == "XOR(Formula('a'), Formula('b'))"
    assert str(lft ^ rgt) == "XOR(a, b)"


@pytest.mark.parametrize(
    "cmp,op",
    [
        (EQ, "="),
        (NE, "!="),
        (GT, ">"),
        (GTE, ">="),
        (LT, "<"),
        (LTE, "<="),
    ],
)
def test_comparisons(cmp, op):
    assert repr(cmp(1, 1)) == f"{cmp.__name__}(1, 1)"
    assert str(cmp(1, 1)) == f"1{op}1"
    assert str(cmp(F.Formula("Foo"), "Foo")) == f"Foo{op}'Foo'"


def test_compound():
    cmp = F.Compound("AND", [EQ("foo", 1), EQ("bar", 2)])
    assert repr(cmp) == "AND(EQ('foo', 1), EQ('bar', 2))"


@pytest.mark.parametrize("cmp", [AND, OR])
@pytest.mark.parametrize(
    "call_args",
    [
        # mix *components and and **fields
        call(EQ("foo", 1), bar=2),
        # multiple *components
        call(EQ("foo", 1), EQ(F.Field("bar"), 2)),
        # one item in *components that is also an iterable
        call([EQ("foo", 1), EQ(F.Field("bar"), 2)]),
        call((EQ("foo", 1), EQ(F.Field("bar"), 2))),
        lambda: call(iter([EQ("foo", 1), EQ(F.Field("bar"), 2)])),
        # test that we accept `str` and convert to formulas
        call(["'foo'=1", "{bar}=2"]),
    ],
)
def test_compound_constructors(cmp, call_args):
    if type(call_args) != type(call):
        call_args = call_args()
    compound = cmp(*call_args.args, **call_args.kwargs)
    expected = cmp(EQ("foo", 1), EQ(F.Field("bar"), 2))
    # compare final output expression, since the actual values will not be equal
    assert str(compound) == str(expected)


@pytest.mark.parametrize("cmp", ["AND", "OR", "NOT"])
def test_compound_without_parameters(cmp):
    with pytest.raises(
        ValueError,
        match=r"Compound\(\) requires at least one component",
    ):
        F.Compound(cmp, [])


def test_compound_flatten():
    a = EQ("a", "a")
    b = EQ("b", "b")
    c = EQ("c", "c")
    d = EQ("d", "d")
    e = EQ("e", "e")
    c = (a & b) & (c & (d | e))
    assert c == AND(
        AND(EQ("a", "a"), EQ("b", "b")),
        AND(EQ("c", "c"), OR(EQ("d", "d"), EQ("e", "e"))),
    )
    assert c.flatten() == AND(
        EQ("a", "a"),
        EQ("b", "b"),
        EQ("c", "c"),
        OR(EQ("d", "d"), EQ("e", "e")),
    )
    assert (~c).flatten() == NOT(
        AND(
            EQ("a", "a"),
            EQ("b", "b"),
            EQ("c", "c"),
            OR(EQ("d", "d"), EQ("e", "e")),
        )
    )
    assert str((~c).flatten()) == (
        "NOT(AND('a'='a', 'b'='b', 'c'='c', OR('d'='d', 'e'='e')))"
    )


def test_compound_flatten_circular_dependency():
    circular = NOT(F.Formula("x"))
    circular.components = [circular]
    with pytest.raises(F.CircularDependency):
        circular.flatten()


def test_not():
    assert NOT(EQ("foo", 1)) == NOT(EQ("foo", 1))
    assert NOT(foo=1) == NOT(EQ(F.Field("foo"), 1))

    with pytest.raises(TypeError):
        NOT(EQ("foo", 1), EQ("bar", 2))

    with pytest.raises(ValueError, match="requires exactly one condition; got 2"):
        NOT(EQ("foo", 1), bar=2)

    with pytest.raises(ValueError, match="requires exactly one condition; got 2"):
        NOT(foo=1, bar=2)

    with pytest.raises(ValueError, match="requires exactly one condition; got 0"):
        NOT()


@pytest.mark.parametrize(
    "input,expected",
    [
        (EQ(F.Formula("a"), "b"), "a='b'"),
        (True, "1"),
        (False, "0"),
        (3, "3"),
        (3.5, "3.5"),
        (Decimal("3.14159265"), "3.14159265"),
        (Fraction("4/19"), "4/19"),
        ("asdf", "'asdf'"),
        ("Jane's", "'Jane\\'s'"),
        (
            datetime.date(2023, 12, 1),
            "DATETIME_PARSE('2023-12-01')",
        ),
        (
            datetime.datetime(2023, 12, 1, 12, 34, 56),
            "DATETIME_PARSE('2023-12-01T12:34:56.000Z')",
        ),
    ],
)
def test_to_formula(input, expected):
    assert F.to_formula_str(input) == expected


def test_function_call():
    fc = F.FunctionCall("IF", 1, True, False)
    assert repr(fc) == "IF(1, True, False)"
    assert str(fc) == "IF(1, 1, 0)"


def test_field_name():
    assert F.field_name("First Name") == "{First Name}"
    assert F.field_name("Guest's Name") == "{Guest\\'s Name}"


def test_quoted():
    assert F.quoted("John") == "'John'"
    assert F.quoted("Guest's Name") == "'Guest\\'s Name'"
