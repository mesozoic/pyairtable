from typing import Dict, Optional

from pyairtable.api.types import CollaboratorDict
from pyairtable.models._base import AirtableModel, SerializableModel


class Comment(SerializableModel):
    """
    A record comment that has been retrieved from the Airtable API.

    >>> comment = table.add_comment("recMNxslc6jG0XedV", "Hello, @[usrVMNxslc6jG0Xed]!")
    >>> table.comments("recMNxslc6jG0XedV")
    [
        Comment(
            id='comdVMNxslc6jG0Xe',
            text='Hello, @[usrVMNxslc6jG0Xed]!',
            created_time='2023-06-07T17:46:24.435891',
            last_updated_time=None,
            mentioned={
                'usrVMNxslc6jG0Xed': Mentioned(
                    display_name='Alice',
                    email='alice@example.com',
                    id='usrVMNxslc6jG0Xed',
                    type='user'
                )
            },
            author={
                'id': 'usrL2xZC5xoH4luAi',
                'email': 'pyairtable@example.com',
                'name': 'Your pyairtable access token'
            }
        )
    ]
    >>> comment.text = "Never mind!"
    >>> comment.save()
    >>> comment.delete()
    """

    __writable__ = ["text"]

    #: The unique ID of the comment.
    id: str

    #: The text of the comment.
    text: str

    #: The ISO 8601 timestamp of when the comment was created.
    created_time: str

    #: The ISO 8601 timestamp of when the comment was last edited.
    last_updated_time: Optional[str]

    #: The account which created the comment.
    author: CollaboratorDict

    #: Users or groups that were mentioned in the text.
    mentioned: Optional[Dict[str, "Comment.Mentioned"]]

    class Mentioned(AirtableModel):
        """
        A user or group that was mentioned within a comment.
        Stored as a ``dict`` that is keyed by ID.

        >>> comment = table.add_comment(record_id, "Hello, @[usrVMNxslc6jG0Xed]!")
        >>> comment.mentioned
        {
            "usrVMNxslc6jG0Xed": Mentioned(
                display_name='Alice',
                email='alice@example.com',
                id='usrVMNxslc6jG0Xed',
                type='user'
            )
        }

        See `User mentioned <https://airtable.com/developers/web/api/model/user-mentioned>`_ for more details.
        """

        id: str
        type: str
        display_name: str
        email: Optional[str] = None


Comment.update_forward_refs()