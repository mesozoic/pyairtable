import os

import pytest

from pyairtable import Base, Table


@pytest.fixture
def api_key():
    return os.environ["AIRTABLE_API_KEY"]


@pytest.fixture
def create_meta(api_key, base_id):
    """
    This fixture is a callable that returns a Meta class with a real API key.

    ``create_meta(table)`` uses the ``base_id`` fixture by default.
    ``create_meta(base, table)`` only uses the ``api_key`` fixture.
    """

    def _create_meta(*args):
        if len(args) == 1:
            _base_id, table_name = base_id, args[0]
        elif len(args) == 2:
            _base_id, table_name = args
        else:
            raise ValueError("create_meta() takes 1 (table) or 2 (base, table) args")
        cfg = {"api_key": api_key, "base_id": _base_id, "table_name": table_name}
        return type("Meta", (), cfg)

    return _create_meta


@pytest.fixture
def base_id():
    return "appaPqizdsNHDvlEm"


@pytest.fixture
def base_name():
    return "Test Wrapper"


@pytest.fixture
def valid_img_url():
    return "https://github.com/gtalarico/pyairtable/raw/9f243cb0935ad7112859f990434612efdaf49c67/docs/source/_static/logo.png"


@pytest.fixture
def cols():
    class Columns:
        # Table should have these Columns
        TEXT = "text"  # Text
        TEXT_ID = "fldzbVdWW4xJdZ1em"  # for returnFieldsByFieldId
        NUM = "number"  # Number, float
        NUM_ID = "fldFLyuxGuWobyMV2"  # for returnFieldsByFieldId
        BOOL = "boolean"  # Boolean
        DATETIME = "datetime"  # Datetime
        ATTACHMENT = "attachment"  # attachment

    return Columns


@pytest.fixture
def base(api_key, base_id):
    base = Base(api_key, base_id)
    yield base
    table_name = "TEST_TABLE"
    records = base.all(table_name)
    base.batch_delete(table_name, [r["id"] for r in records])


@pytest.fixture
def table(api_key, base_id):
    table_name = "TEST_TABLE"
    table = Table(api_key, base_id, table_name)
    yield table
    records = table.all()
    table.batch_delete([r["id"] for r in records])
