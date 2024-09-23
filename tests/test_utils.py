from datetime import date, datetime, timezone
from functools import partial

import pytest

from pyairtable import utils

utc_tz = partial(datetime, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "dt_obj,dt_str",
    [
        (datetime(2000, 1, 2, 3, 4, 5, 0), "2000-01-02T03:04:05.000"),
        (datetime(2025, 12, 31, 23, 59, 59, 0), "2025-12-31T23:59:59.000"),
        (datetime(2025, 12, 31, 23, 59, 59, 5_000), "2025-12-31T23:59:59.005"),
        (datetime(2025, 12, 31, 23, 59, 59, 555_000), "2025-12-31T23:59:59.555"),
        (utc_tz(2000, 1, 2, 3, 4, 5, 0), "2000-01-02T03:04:05.000Z"),
        (utc_tz(2025, 12, 31, 23, 59, 59, 0), "2025-12-31T23:59:59.000Z"),
        (utc_tz(2025, 12, 31, 23, 59, 59, 5_000), "2025-12-31T23:59:59.005Z"),
        (utc_tz(2025, 12, 31, 23, 59, 59, 555_000), "2025-12-31T23:59:59.555Z"),
    ],
)
def test_datetime_utils(dt_obj, dt_str):
    assert utils.datetime_to_iso_str(dt_obj) == dt_str
    assert utils.datetime_from_iso_str(dt_str) == dt_obj


@pytest.mark.parametrize(
    "date_obj,date_str",
    [
        (date(2000, 1, 2), "2000-01-02"),
        (date(2025, 12, 31), "2025-12-31"),
    ],
)
def test_date_utils(date_obj, date_str):
    assert utils.date_to_iso_str(date_obj) == date_str
    assert utils.date_from_iso_str(date_str) == date_obj


def test_attachment():
    with pytest.deprecated_call():
        assert utils.attachment("https://url.com") == {"url": "https://url.com"}

    with pytest.deprecated_call():
        assert utils.attachment("https://url.com", filename="test.jpg") == {
            "url": "https://url.com",
            "filename": "test.jpg",
        }


@pytest.mark.parametrize(
    "func,value,expected",
    [
        (utils.is_airtable_id, -1, False),
        (utils.is_airtable_id, "appAkBDICXDqESDhF", True),
        (utils.is_airtable_id, "app0000000000Fake", True),
        (utils.is_airtable_id, "appWrongLength", False),
        (utils.is_record_id, "rec0000000000Fake", True),
        (utils.is_record_id, "app0000000000Fake", False),
        (utils.is_base_id, "app0000000000Fake", True),
        (utils.is_base_id, "rec0000000000Fake", False),
        (utils.is_table_id, "tbl0000000000Fake", True),
        (utils.is_table_id, "rec0000000000Fake", False),
        (utils.is_field_id, "fld0000000000Fake", True),
        (utils.is_field_id, "rec0000000000Fake", False),
    ],
)
def test_id_check(func, value, expected):
    assert func(value) is expected


@pytest.mark.parametrize(
    "func,input,expected",
    [
        (utils.coerce_iso_str, None, None),
        (utils.coerce_iso_str, "asdf", ValueError),
        (utils.coerce_iso_str, -1, TypeError),
        (utils.coerce_iso_str, "2023-01-01", "2023-01-01"),
        (utils.coerce_iso_str, "2023-01-01 12:34:56", "2023-01-01 12:34:56"),
        (utils.coerce_iso_str, date(2023, 1, 1), "2023-01-01"),
        (
            utils.coerce_iso_str,
            datetime(2023, 1, 1, 12, 34, 56),
            "2023-01-01T12:34:56",
        ),
        (utils.coerce_list_str, None, []),
        (utils.coerce_list_str, "asdf", ["asdf"]),
        (utils.coerce_list_str, ("one", "two", "three"), ["one", "two", "three"]),
        (utils.coerce_list_str, -1, TypeError),
    ],
)
def test_converter(func, input, expected):
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            func(input)
        return

    assert func(input) == expected


def test_url_builder(base):
    class Example(utils.UrlBuilder):
        static = "one/two/three"
        with_attr = "id/{id}"
        with_self_attr = "self.id/{self.id}"
        with_property = "self.name/{self.name}"
        _ignored = "ignored"

    urls = Example(base)
    assert urls.static == "https://api.airtable.com/v0/one/two/three"
    assert urls.with_attr == f"https://api.airtable.com/v0/id/{base.id}"
    assert urls.with_self_attr == f"https://api.airtable.com/v0/self.id/{base.id}"
    assert urls.with_property == f"https://api.airtable.com/v0/self.name/{base.name}"
    assert urls._ignored == "ignored"


@pytest.mark.parametrize("obj", [None, object(), {"api": object()}])
def test_url_builder__invalid_context(obj):
    with pytest.raises(TypeError):
        utils.UrlBuilder(obj)


def test_url():
    v = utils.Url("https://example.com")
    assert v == "https://example.com"
    assert v / "foo/bar" / "baz" == "https://example.com/foo/bar/baz"
    assert v // [1, 2, "a", "b"] == "https://example.com/1/2/a/b"
    assert v & {"a": 1, "b": [2, 3, 4]} == "https://example.com?a=1&b=2&b=3&b=4"
    assert v.add_path(1, 2, "a", "b") == "https://example.com/1/2/a/b"
    assert v.add_qs({"a": 1}, b=[2, 3, 4]) == "https://example.com?a=1&b=2&b=3&b=4"

    with pytest.raises(TypeError):
        v.add_path()
    with pytest.raises(TypeError):
        v.add_qs()


def test_url_cannot_append_after_params():
    # cannot add path segments after params
    v = utils.Url("https://example.com?a=1&b=2")
    with pytest.raises(ValueError):
        v / "foo"
    with pytest.raises(ValueError):
        v // ["foo", "bar"]
