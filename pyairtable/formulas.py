"""
Utilities for constructing Airtable formulas.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction
from typing import Any, ClassVar, Iterable, Iterator, List, Optional, Set, Union

from typing_extensions import Self as SelfType

from pyairtable.api.types import Fields
from pyairtable.utils import date_to_iso_str, datetime_to_iso_str


class Formula:
    """
    Represents an Airtable formula that can be combined with other formulas
    or converted to a string.
    """

    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"

    def __and__(self, other: "Formula") -> "Compound":
        return AND(self, other)

    def __or__(self, other: "Formula") -> "Compound":
        return OR(self, other)

    def __xor__(self, other: "Formula") -> "Compound":
        return OR(AND(self, NOT(other)), AND(other, NOT(self)))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Formula):
            return False
        return other.value == self.value

    def __invert__(self) -> "Compound":
        return NOT(self)

    def flatten(self) -> SelfType:
        return self

    @classmethod
    def coerce(cls, value: Any) -> SelfType:
        if isinstance(value, cls):
            return value
        return cls(str(value))


class Field(Formula):
    """
    Represents a field name.
    """

    def __str__(self) -> str:
        return "{%s}" % escape_quotes(self.value)


class Comparison(Formula):
    """
    Represents a logical condition that compares two expressions.
    """

    operator: ClassVar[str] = ""

    def __init__(self, lval: Any, rval: Any):
        self.lval = lval
        self.rval = rval

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Comparison):
            return False
        return (self.lval, self.rval) == (other.lval, other.rval)

    def __str__(self) -> str:
        if not self.operator:
            raise NotImplementedError(
                f"{self.__class__.__name__}.operator is not defined"
            )
        lval, rval = (to_formula_str(v) for v in (self.lval, self.rval))
        return f"{lval}{self.operator}{rval}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.lval!r}, {self.rval!r})"


class EQ(Comparison):
    operator = "="


class NE(Comparison):
    operator = "!="


class GT(Comparison):
    operator = ">"


class GTE(Comparison):
    operator = ">="


class LT(Comparison):
    operator = "<"


class LTE(Comparison):
    operator = "<="


class Compound(Formula):
    """
    Represents a compound logical operator wrapping around one or more conditions.
    """

    operator: str
    components: List[Formula]

    def __init__(
        self,
        operator: str,
        components: Iterable[Formula],
    ) -> None:
        if not isinstance(components, list):
            components = list(components)
        if len(components) == 0:
            raise ValueError("Compound() requires at least one component")

        self.operator = operator
        self.components = components

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Compound):
            return False
        return (self.operator, self.components) == (other.operator, other.components)

    def __str__(self) -> str:
        joined_components = ", ".join(str(c) for c in self.components)
        return f"{self.operator}({joined_components})"

    def __repr__(self) -> str:
        return f"{self.operator}({repr(self.components)[1:-1]})"

    def __iter__(self) -> Iterator[Formula]:
        return iter(self.components)

    def flatten(self, /, memo: Optional[Set[int]] = None) -> "Compound":
        """
        Reduces the depth of nested AND, OR, and NOT statements.
        """
        memo = memo if memo else set()
        memo.add(id(self))
        flattened: List[Formula] = []
        for item in self.components:
            if id(item) in memo:
                raise CircularDependency(item)
            if isinstance(item, Compound) and item.operator == self.operator:
                flattened.extend(item.flatten(memo=memo).components)
            else:
                flattened.append(item.flatten())

        return Compound(self.operator, flattened)

    @classmethod
    def build(cls, operator: str, *components: Any, **fields: Any) -> SelfType:
        items = list(components)
        if len(items) == 1 and hasattr(first := items[0], "__iter__"):
            items = [first] if isinstance(first, str) else list(first)
        coerced = [Formula.coerce(item) for item in items]
        if fields:
            coerced.extend(EQ(Field(k), v) for (k, v) in fields.items())
        return cls(operator, coerced)


class CircularDependency(RecursionError):
    """
    We detected a circular dependency when flattening nested conditions.
    """


def AND(*components: Union[Formula, Iterable[Formula]], **fields: Any) -> Compound:
    """
    Joins one or more logical conditions into an AND compound condition.

    >>> AND(EQ("foo", 1), EQ("bar", 2), baz=3)
    AND(EQ('foo', 1), EQ('bar', 2), EQ(Field('baz'), 3))
    """
    return Compound.build("AND", *components, **fields)


def OR(*components: Union[Formula, Iterable[Formula]], **fields: Any) -> Compound:
    """
    Joins one or more logical conditions into an OR compound condition.

    >>> OR(EQ("foo", 1), EQ("bar", 2), baz=3)
    OR(EQ('foo', 1), EQ('bar', 2), EQ(Field('baz'), 3))
    """
    return Compound.build("OR", *components, **fields)


def NOT(component: Optional[Formula] = None, /, **fields: Any) -> Compound:
    """
    Wraps one logical condition in a negation compound.

    Can be called either explicitly or with kwargs, but not both.

    >>> NOT(EQ("foo", 1))
    NOT(EQ('foo', 1))

    >>> NOT(foo=1)
    NOT(EQ(Field('foo'), 1))

    If not called with exactly one condition, will throw an exception:

    >>> NOT(EQ("foo", 1), EQ("bar", 2))
    Traceback (most recent call last):
    TypeError: NOT() takes from 0 to 1 positional arguments but 2 were given

    >>> NOT(EQ("foo", 1), bar=2)
    Traceback (most recent call last):
    ValueError: NOT() requires exactly one condition; got 2

    >>> NOT(foo=1, bar=2)
    Traceback (most recent call last):
    ValueError: NOT() requires exactly one condition; got 2

    >>> NOT()
    Traceback (most recent call last):
    ValueError: NOT() requires exactly one condition; got 0
    """
    items: List[Formula] = [EQ(Field(k), v) for (k, v) in fields.items()]
    if component:
        items.append(component)
    if (count := len(items)) != 1:
        raise ValueError(f"NOT() requires exactly one condition; got {count}")
    return Compound.build("NOT", items)


def match(dict_values: Fields, *, match_any: bool = False) -> Optional[Formula]:
    r"""
    Creates one or more ``EQUAL()`` expressions for each provided value,
    treating keys as field names and values as values (not formula expressions).

    If more than one assertion is included, the expressions are
    grouped together into using ``AND()`` (all values must match).

    If ``match_any=True``, expressions are grouped with ``OR()``, record is return
    if any of the values match.

    If you need more advanced matching you can build similar expressions using lower
    level forumula primitives.


    Args:
        dict_values: dictionary containing column names and values

    Keyword Args:
        match_any (``bool``, default: ``False``):
            If ``True``, matches if **any** of the provided values match.
            Otherwise, all values must match.

    Usage:
        >>> match({"First Name": "John", "Age": 21})
        AND(EQ(Field('First Name'), 'John'),
            EQ(Field('Age'), 21))

        >>> match({"First Name": "John", "Age": 21}, match_any=True)
        OR(EQ(Field('First Name'), 'John'),
           EQ(Field('Age'), 21))

        >>> match({"First Name": "John"})
        EQ(Field('First Name'), 'John')

        >>> match({"Registered": True})
        EQ(Field('Registered'), True)
        >>> str(_)
        '{Registered}=1'

        >>> match({"Owner's Name": "Mike"})
        EQ(Field("Owner's Name"), 'Mike')
        >>> print(_)
        {Owner\'s Name}='Mike'
    """
    expressions = [EQ(Field(key), value) for key, value in dict_values.items()]

    if len(expressions) == 0:
        return None
    elif len(expressions) == 1:
        return expressions[0]
    if not match_any:
        return AND(*expressions)
    return OR(*expressions)


def to_formula_str(value: Any) -> str:
    """
    Converts the given value into a string representation that can be used
    in an Airtable formula expression.
    """
    if isinstance(value, Formula):
        return str(value)
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, (int, float, Decimal, Fraction)):
        return str(value)
    if isinstance(value, str):
        return "'{}'".format(escape_quotes(value))
    if isinstance(value, datetime):
        return str(DATETIME_PARSE(datetime_to_iso_str(value)))
    if isinstance(value, date):
        return str(DATETIME_PARSE(date_to_iso_str(value)))
    raise TypeError(type(value))


class FunctionCall(Formula):
    """
    Represents a function call in an Airtable formula.
    """

    def __init__(self, name: str, *args: List[Any]):
        self.name = name
        self.args = args

    def __str__(self) -> str:
        joined_args = ", ".join(to_formula_str(v) for v in self.args)
        return f"{self.name}({joined_args})"

    def __repr__(self) -> str:
        joined_args_repr = ", ".join(repr(v) for v in self.args)
        return f"{self.name}({joined_args_repr})"


# fmt: off
r"""[[[cog]]]

import re
from pathlib import Path

definitions = [
    line.strip()
    for line in Path(cog.inFile).with_suffix(".txt").read_text().splitlines()
    if line.strip()
    and not line.startswith("#")
]

cog.outl("\n")

for definition in definitions:
    name, argspec = definition.rstrip(")").split("(")
    if name in ("AND", "OR", "NOT"):
        continue

    args = [
        re.sub(
            "([a-z])([A-Z])",
            lambda m: m[1] + "_" + m[2].lower(),
            name.strip()
        )
        for name in argspec.split(",")
    ]

    required = [arg for arg in args if arg and not arg.startswith("[")]
    optional = [arg.strip("[]") for arg in args if arg.startswith("[") and arg.endswith("]")]
    signature = [f"{arg}: Any" for arg in required]
    params = [*required]
    splat = optional.pop().rstrip(".") if optional and optional[-1].endswith("...") else None

    if optional:
        signature += [f"{arg}: Optional[Any] = None" for arg in optional]
        params += ["*(v for v in [" + ", ".join(optional) + "] if v is not None)"]

    if required or optional:
        signature += ["/"]

    if splat:
        signature += [f"*{splat}: Any"]
        params += [f"*{splat}"]

    joined_signature = ", ".join(signature)
    joined_params = (", " + ", ".join(params)) if params else ""

    cog.outl(f"def {name}({joined_signature}) -> FunctionCall:")
    cog.outl(f"    return FunctionCall({name!r}{joined_params})")
    cog.outl("\n")

[[[out]]]"""


def CONCATENATE(text1: Any, /, *texts: Any) -> FunctionCall:
    return FunctionCall('CONCATENATE', text1, *texts)


def ENCODE_URL_COMPONENT(component_string: Any, /) -> FunctionCall:
    return FunctionCall('ENCODE_URL_COMPONENT', component_string)


def FIND(string_to_find: Any, where_to_search: Any, start_from_position: Optional[Any] = None, /) -> FunctionCall:
    return FunctionCall('FIND', string_to_find, where_to_search, *(v for v in [start_from_position] if v is not None))


def LEFT(string: Any, how_many: Any, /) -> FunctionCall:
    return FunctionCall('LEFT', string, how_many)


def LEN(string: Any, /) -> FunctionCall:
    return FunctionCall('LEN', string)


def LOWER(string: Any, /) -> FunctionCall:
    return FunctionCall('LOWER', string)


def MID(string: Any, where_to_start: Any, count: Any, /) -> FunctionCall:
    return FunctionCall('MID', string, where_to_start, count)


def REPLACE(string: Any, start_character: Any, number_of_characters: Any, replacement: Any, /) -> FunctionCall:
    return FunctionCall('REPLACE', string, start_character, number_of_characters, replacement)


def REPT(string: Any, number: Any, /) -> FunctionCall:
    return FunctionCall('REPT', string, number)


def RIGHT(string: Any, how_many: Any, /) -> FunctionCall:
    return FunctionCall('RIGHT', string, how_many)


def SEARCH(string_to_find: Any, where_to_search: Any, start_from_position: Optional[Any] = None, /) -> FunctionCall:
    return FunctionCall('SEARCH', string_to_find, where_to_search, *(v for v in [start_from_position] if v is not None))


def SUBSTITUTE(string: Any, old_text: Any, new_text: Any, index: Optional[Any] = None, /) -> FunctionCall:
    return FunctionCall('SUBSTITUTE', string, old_text, new_text, *(v for v in [index] if v is not None))


def T(value1: Any, /) -> FunctionCall:
    return FunctionCall('T', value1)


def TRIM(string: Any, /) -> FunctionCall:
    return FunctionCall('TRIM', string)


def UPPER(string: Any, /) -> FunctionCall:
    return FunctionCall('UPPER', string)


def BLANK() -> FunctionCall:
    return FunctionCall('BLANK')


def ERROR() -> FunctionCall:
    return FunctionCall('ERROR')


def FALSE() -> FunctionCall:
    return FunctionCall('FALSE')


def IF(expression: Any, value1: Any, value2: Any, /) -> FunctionCall:
    return FunctionCall('IF', expression, value1, value2)


def ISERROR(expr: Any, /) -> FunctionCall:
    return FunctionCall('ISERROR', expr)


def SWITCH(expression: Any, pattern: Any, result: Any, /, *pattern_results: Any) -> FunctionCall:
    return FunctionCall('SWITCH', expression, pattern, result, *pattern_results)


def TRUE() -> FunctionCall:
    return FunctionCall('TRUE')


def XOR(expression1: Any, /, *expressions: Any) -> FunctionCall:
    return FunctionCall('XOR', expression1, *expressions)


def ABS(value: Any, /) -> FunctionCall:
    return FunctionCall('ABS', value)


def AVERAGE(number1: Any, /, *numbers: Any) -> FunctionCall:
    return FunctionCall('AVERAGE', number1, *numbers)


def CEILING(value: Any, significance: Optional[Any] = None, /) -> FunctionCall:
    return FunctionCall('CEILING', value, *(v for v in [significance] if v is not None))


def COUNT(number1: Any, /, *numbers: Any) -> FunctionCall:
    return FunctionCall('COUNT', number1, *numbers)


def COUNTA(text_or_number1: Any, /, *numbers: Any) -> FunctionCall:
    return FunctionCall('COUNTA', text_or_number1, *numbers)


def COUNTALL(text_or_number1: Any, /, *numbers: Any) -> FunctionCall:
    return FunctionCall('COUNTALL', text_or_number1, *numbers)


def EVEN(value: Any, /) -> FunctionCall:
    return FunctionCall('EVEN', value)


def EXP(power: Any, /) -> FunctionCall:
    return FunctionCall('EXP', power)


def FLOOR(value: Any, significance: Optional[Any] = None, /) -> FunctionCall:
    return FunctionCall('FLOOR', value, *(v for v in [significance] if v is not None))


def INT(value: Any, /) -> FunctionCall:
    return FunctionCall('INT', value)


def LOG(number: Any, base: Optional[Any] = None, /) -> FunctionCall:
    return FunctionCall('LOG', number, *(v for v in [base] if v is not None))


def MAX(number1: Any, /, *numbers: Any) -> FunctionCall:
    return FunctionCall('MAX', number1, *numbers)


def MIN(number1: Any, /, *numbers: Any) -> FunctionCall:
    return FunctionCall('MIN', number1, *numbers)


def MOD(value1: Any, divisor: Any, /) -> FunctionCall:
    return FunctionCall('MOD', value1, divisor)


def ODD(value: Any, /) -> FunctionCall:
    return FunctionCall('ODD', value)


def POWER(base: Any, power: Any, /) -> FunctionCall:
    return FunctionCall('POWER', base, power)


def ROUND(value: Any, precision: Any, /) -> FunctionCall:
    return FunctionCall('ROUND', value, precision)


def ROUNDDOWN(value: Any, precision: Any, /) -> FunctionCall:
    return FunctionCall('ROUNDDOWN', value, precision)


def ROUNDUP(value: Any, precision: Any, /) -> FunctionCall:
    return FunctionCall('ROUNDUP', value, precision)


def SQRT(value: Any, /) -> FunctionCall:
    return FunctionCall('SQRT', value)


def SUM(number1: Any, /, *numbers: Any) -> FunctionCall:
    return FunctionCall('SUM', number1, *numbers)


def VALUE(text: Any, /) -> FunctionCall:
    return FunctionCall('VALUE', text)


def CREATED_TIME() -> FunctionCall:
    return FunctionCall('CREATED_TIME')


def DATEADD(date: Any, number: Any, units: Any, /) -> FunctionCall:
    return FunctionCall('DATEADD', date, number, units)


def DATESTR(date: Any, /) -> FunctionCall:
    return FunctionCall('DATESTR', date)


def DATETIME_DIFF(date1: Any, date2: Any, units: Any, /) -> FunctionCall:
    return FunctionCall('DATETIME_DIFF', date1, date2, units)


def DATETIME_FORMAT(date: Any, output_format: Optional[Any] = None, /) -> FunctionCall:
    return FunctionCall('DATETIME_FORMAT', date, *(v for v in [output_format] if v is not None))


def DATETIME_PARSE(date: Any, input_format: Optional[Any] = None, locale: Optional[Any] = None, /) -> FunctionCall:
    return FunctionCall('DATETIME_PARSE', date, *(v for v in [input_format, locale] if v is not None))


def DAY(date: Any, /) -> FunctionCall:
    return FunctionCall('DAY', date)


def HOUR(datetime: Any, /) -> FunctionCall:
    return FunctionCall('HOUR', datetime)


def IS_AFTER(date1: Any, date2: Any, /) -> FunctionCall:
    return FunctionCall('IS_AFTER', date1, date2)


def IS_BEFORE(date1: Any, date2: Any, /) -> FunctionCall:
    return FunctionCall('IS_BEFORE', date1, date2)


def IS_SAME(date1: Any, date2: Any, unit: Any, /) -> FunctionCall:
    return FunctionCall('IS_SAME', date1, date2, unit)


def LAST_MODIFIED_TIME(*fields: Any) -> FunctionCall:
    return FunctionCall('LAST_MODIFIED_TIME', *fields)


def MINUTE(datetime: Any, /) -> FunctionCall:
    return FunctionCall('MINUTE', datetime)


def MONTH(date: Any, /) -> FunctionCall:
    return FunctionCall('MONTH', date)


def NOW() -> FunctionCall:
    return FunctionCall('NOW')


def SECOND(datetime: Any, /) -> FunctionCall:
    return FunctionCall('SECOND', datetime)


def SET_LOCALE(date: Any, locale_modifier: Any, /) -> FunctionCall:
    return FunctionCall('SET_LOCALE', date, locale_modifier)


def SET_TIMEZONE(date: Any, tz_identifier: Any, /) -> FunctionCall:
    return FunctionCall('SET_TIMEZONE', date, tz_identifier)


def TIMESTR(timestamp: Any, /) -> FunctionCall:
    return FunctionCall('TIMESTR', timestamp)


def TONOW(date: Any, /) -> FunctionCall:
    return FunctionCall('TONOW', date)


def FROMNOW(date: Any, /) -> FunctionCall:
    return FunctionCall('FROMNOW', date)


def TODAY() -> FunctionCall:
    return FunctionCall('TODAY')


def WEEKDAY(date: Any, start_day_of_week: Optional[Any] = None, /) -> FunctionCall:
    return FunctionCall('WEEKDAY', date, *(v for v in [start_day_of_week] if v is not None))


def WEEKNUM(date: Any, start_day_of_week: Optional[Any] = None, /) -> FunctionCall:
    return FunctionCall('WEEKNUM', date, *(v for v in [start_day_of_week] if v is not None))


def WORKDAY(start_date: Any, num_days: Any, holidays: Optional[Any] = None, /) -> FunctionCall:
    return FunctionCall('WORKDAY', start_date, num_days, *(v for v in [holidays] if v is not None))


def WORKDAY_DIFF(start_date: Any, end_date: Any, holidays: Optional[Any] = None, /) -> FunctionCall:
    return FunctionCall('WORKDAY_DIFF', start_date, end_date, *(v for v in [holidays] if v is not None))


def YEAR(date: Any, /) -> FunctionCall:
    return FunctionCall('YEAR', date)


def RECORD_ID() -> FunctionCall:
    return FunctionCall('RECORD_ID')


def REGEX_MATCH(string: Any, regex: Any, /) -> FunctionCall:
    return FunctionCall('REGEX_MATCH', string, regex)


def REGEX_EXTRACT(string: Any, regex: Any, /) -> FunctionCall:
    return FunctionCall('REGEX_EXTRACT', string, regex)


def REGEX_REPLACE(string: Any, regex: Any, replacement: Any, /) -> FunctionCall:
    return FunctionCall('REGEX_REPLACE', string, regex, replacement)


# [[[end]]] (checksum: f619d2351cd4e53eb2b3cd0e04f6f433)
# fmt: on


def escape_quotes(value: str) -> str:
    r"""
    Ensures any quotes are escaped. Already escaped quotes are ignored.

    Args:
        value: text to be escaped

    Usage:
        >>> escape_quotes(r"Player's Name")
        "Player\\'s Name"
        >>> escape_quotes(r"Player\'s Name")
        "Player\\'s Name"
    """
    escaped_value = re.sub("(?<!\\\\)'", "\\'", value)
    return escaped_value


def field_name(name: str) -> str:
    r"""
    Create a reference to a field. Quotes are escaped.

    Args:
        name: field name

    Usage:
        >>> FIELD("First Name")
        '{First Name}'
        >>> FIELD("Guest's Name")
        "{Guest\\'s Name}"
    """
    return "{%s}" % escape_quotes(name)


def quoted(value: str) -> str:
    r"""
    Wrap string in quotes. This is needed when referencing a string inside a formula.
    Quotes are escaped.

    >>> STR_VALUE("John")
    "'John'"
    >>> STR_VALUE("Guest's Name")
    "'Guest\\'s Name'"
    """
    return "'{}'".format(escape_quotes(str(value)))
