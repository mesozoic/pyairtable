"""
pyAirtable provides a number of type aliases and TypedDicts which are used as inputs
and return values to various pyAirtable methods.
"""
from functools import lru_cache
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

from typing_extensions import Required, TypeAlias, TypedDict

from pyairtable._compat import pydantic

T = TypeVar("T")

#: An alias for ``str`` used internally for disambiguation.
#: Record IDs for Airtable look like ``"rec00Adw9EjV90xbZ"``.
RecordId: TypeAlias = str

#: An alias for ``str`` used internally for disambiguation.
#: Airtable returns timestamps as ISO 8601 UTC strings,
#: e.g. ``"2023-05-22T21:24:15.333134Z"``
Timestamp: TypeAlias = str

#: An alias for ``str`` used internally for disambiguation.
#: Field names can be any valid string.
FieldName: TypeAlias = str


class AttachmentDict(TypedDict, total=False):
    """
    A ``dict`` representing an attachment stored in an Attachments field.

    >>> record = table.get('rec00W8eG2x0ew1Af')
    >>> record['fields']['Attachments']
    [
        {
            'id': 'attW8eG2x0ew1Af',
            'url': 'https://example.com/hello.jpg',
            'filename': 'hello.jpg'
        }
    ]

    See https://airtable.com/developers/web/api/field-model#multipleattachment
    """

    id: Required[str]
    url: Required[str]
    type: str
    filename: str
    size: int
    height: int
    width: int
    thumbnails: Dict[str, Dict[str, Union[str, int]]]


class CreateAttachmentDict(TypedDict, total=False):
    """
    A ``dict`` representing a new attachment to be written to the Airtable API.

    >>> record = table.get("rec00W8eG2x0ew1Af")
    >>> new_attachment = {
    ...     "url": "https://example.com/image.jpg",
    ...     "filename": "something_else.jpg",
    ... }
    >>> existing = record["fields"].setdefault("Attachments", [])
    >>> existing.append(new_attachment)
    >>> table.update(record["id"], record["fields"])
    {
        'id': 'rec00W8eG2x0ew1Af',
        'createdTime': '...',
        'fields': {
            'Attachments': [...],
            ...
        }
    }
    """

    url: Required[str]
    filename: str


class BarcodeDict(TypedDict, total=False):
    """
    A ``dict`` representing the value stored in a Barcode field.

    >>> record = table.get('rec00W8eG2x0ew1Af')
    >>> record['fields']['Barcode']
    {'type': 'upce', 'text': '01234567'}

    See https://airtable.com/developers/web/api/field-model#barcode
    """

    type: str
    text: Required[str]


class ButtonDict(TypedDict):
    """
    A ``dict`` representing the value stored in a Button field.

    >>> record = table.get('rec00W8eG2x0ew1Af')
    >>> record['fields']['Click Me']
    {'label': 'Click Me', 'url': 'http://example.com'}

    See https://airtable.com/developers/web/api/field-model#button
    """

    label: str
    url: Optional[str]


class CollaboratorDict(TypedDict, total=False):
    """
    A dict representing the value stored in a User field returned from the API.

    >>> record = table.get('rec00W8eG2x0ew1Af')
    >>> record['fields']['Created By']
    {
        'id': 'usrAdw9EjV90xbW',
        'email': 'alice@example.com',
        'name': 'Alice Arnold'
    }
    >>> record['fields']['Collaborators']
    [
        {
            'id': 'usrAdw9EjV90xbW',
            'email': 'alice@example.com',
            'name': 'Alice Arnold'
        },
        {
            'id': 'usrAdw9EjV90xbX',
            'email': 'bob@example.com',
            'name': 'Bob Barker'
        }
    ]

    See https://airtable.com/developers/web/api/field-model#collaborator
    """

    id: Required[str]
    email: str
    name: str
    profilePicUrl: str


class CollaboratorEmailDict(TypedDict):
    """
    A dict representing a collaborator identified by email, not by ID.
    Often used when writing to the API, because the email of a collaborator
    may be more easily accessible than their Airtable user ID.

    >>> record = table.update("rec00W8eG2x0ew1Ac", {
    ...     "Collaborator": {"email": "alice@example.com"}
    ... })
    >>> record
    {
        'id': 'rec00W8eG2x0ew1Ac',
        'createdTime': '...',
        'fields': {
            'Collaborator': {
                'id': 'usrAdw9EjV90xbW',
                'email': 'alice@example.com',
                'name': 'Alice Arnold'
            }
        }
    }
    """

    email: str


#: Represents the types of values that we might receive from the API.
#: At present, is an alias for ``Any`` because we don't want to lose
#: forward compatibility with any changes Airtable makes in the future.
FieldValue: TypeAlias = Any


#: A mapping of field names to values that we might receive from the API.
Fields: TypeAlias = Dict[FieldName, FieldValue]


#: Represents the types of values that can be written to the Airtable API.
WritableFieldValue: TypeAlias = Union[
    None,
    str,
    int,
    float,
    bool,
    CollaboratorDict,
    CollaboratorEmailDict,
    BarcodeDict,
    List[str],
    List[AttachmentDict],
    List[CreateAttachmentDict],
    List[CollaboratorDict],
    List[CollaboratorEmailDict],
]


#: A mapping of field names to values which can be sent to the API.
WritableFields: TypeAlias = Dict[FieldName, WritableFieldValue]


class RecordDict(TypedDict):
    """
    A ``dict`` representing a record returned from the Airtable API.
    See `List records <https://airtable.com/developers/web/api/list-records>`__.

    Usage:
        >>> table.first()
        {
            'id': 'rec00W8eG2x0ew1Af',
            'createdTime': '...',
            'fields': {
                ...
            }
        }
    """

    id: RecordId
    createdTime: Timestamp
    fields: Fields


class CreateRecordDict(TypedDict):
    """
    A ``dict`` representing the payload passed to the Airtable API to create a record.

    Field values must each be a :data:`~pyairtable.api.types.WritableFieldValue`.

    Usage:
        >>> record = table.create({
        ...     "fields": {
        ...         "Field Name": "Field Value",
        ...         "Other Field": ["Value 1", "Value 2"]
        ...     }
        ... })
    """

    fields: WritableFields


class UpdateRecordDict(TypedDict):
    """
    A ``dict`` representing the payload passed to the Airtable API to update a record.

    Field values must each be a :data:`~pyairtable.api.types.WritableFieldValue`.

    Usage:
        >>> records = table.batch_update([
        ...     {
        ...         "id": "recAdw9EjV90xbcdW",
        ...         "fields": {
        ...             "Email": "alice@example.com"
        ...         }
        ...     },
        ...     {
        ...         "id": "recAdw9EjV90xbcdX",
        ...         "fields": {
        ...             "Email": "bob@example.com"
        ...         }
        ...     }
        ... ])
    """

    id: RecordId
    fields: WritableFields


class RecordDeletedDict(TypedDict):
    """
    A ``dict`` representing the payload returned by the Airtable API to confirm a deletion.

    Usage:
        >>> table.delete("rec00W8eG2x0ew1Af")
        {'id': 'rec00W8eG2x0ew1Af', 'deleted': True}
    """

    id: RecordId
    deleted: bool


class UpsertResultDict(TypedDict):
    """
    A ``dict`` representing the payload returned by the Airtable API after an upsert.
    For more details on this data structure, see the
    `Update multiple records <https://airtable.com/developers/web/api/update-multiple-records>`__
    API documentation.

    Usage:
        >>> table.batch_upsert(upserts, key_fields=["Name"])
        {
            'createdRecords': [...],
            'updatedRecords': [...],
            'records': [...]
        }
    """

    createdRecords: List[RecordId]
    updatedRecords: List[RecordId]
    records: List[RecordDict]


class UserAndScopesDict(TypedDict, total=False):
    """
    A ``dict`` representing the `Get user ID & scopes <https://airtable.com/developers/web/api/get-user-id-scopes>`_ endpoint.

    Usage:
        >>> api.whoami()
        {'id': 'usrX9e810wHn3mMLz'}
    """

    id: Required[str]
    scopes: List[str]


@lru_cache
def _create_model_from_typeddict(cls: Type[T]) -> Type[pydantic.BaseModel]:
    """
    Creates a pydantic model from a TypedDict to use as a validator.
    Memoizes the result so we don't have to call this more than once per class.
    """
    # Mypy can't tell that we are using pydantic v1.
    return pydantic.create_model_from_typeddict(cls)  # type: ignore[no-any-return, operator, unused-ignore]


def assert_typed_dict(cls: Type[T], obj: Any) -> T:
    """
    Raises a TypeError if the given object is not a dict, or raises
    pydantic.ValidationError if the given object does not conform
    to the interface declared by the given TypedDict.

    Args:
        cls: The TypedDict class.
        obj: The object that should be a TypedDict.

    Usage:
        >>> assert_typed_dict(
        ...     RecordDict,
        ...     {
        ...         "id": "rec00Adw9EjV90xbZ",
        ...         "createdTime": "2023-05-22T21:24:15.333134Z",
        ...         "fields": {},
        ...     }
        ... )
        {
            'id': 'rec00Adw9EjV90xbZ',
            'createdTime': '2023-05-22T21:24:15.333134Z',
            'fields': {}
        }

        >>> assert_typed_dict(RecordDict, {"foo": "bar"})
        Traceback (most recent call last):
        pydantic.v1.error_wrappers.ValidationError: 3 validation errors for RecordDict
        id
          field required (type=value_error.missing)
        createdTime
          field required (type=value_error.missing)
        fields
          field required (type=value_error.missing)
    """
    if not isinstance(obj, dict):
        raise TypeError(f"expected dict, got {type(obj)}")
    # mypy complains cls isn't Hashable, but it is; see https://github.com/python/mypy/issues/2412
    model = _create_model_from_typeddict(cls)  # type: ignore
    model(**obj)
    return cast(T, obj)


def assert_typed_dicts(cls: Type[T], objects: Any) -> List[T]:
    """
    Like :func:`~pyairtable.api.types.assert_typed_dict` but for a list of dicts.

    Args:
        cls: The TypedDict class.
        objects: The object that should be a list of TypedDicts.
    """
    if not isinstance(objects, list):
        raise TypeError(f"expected list, got {type(objects)}")
    return [assert_typed_dict(cls, obj) for obj in objects]


def is_airtable_error(obj: Any) -> bool:
    """
    Returns whether the given object represents an Airtable error.
    """
    if isinstance(obj, dict):
        return set(obj) in ({"error"}, {"specialValue"})
    return False
