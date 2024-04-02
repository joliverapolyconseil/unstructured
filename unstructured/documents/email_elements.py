import hashlib
import uuid
from abc import ABC
from datetime import datetime
from typing import Callable, List, Union

from unstructured.documents.elements import Element, NoID, Text


class NoDatestamp(ABC):
    """Class to indicate that an element do not have a datetime stamp."""


class EmailElement(Element):
    """An email element is a section of the email."""


class Name(EmailElement):
    """Base element for capturing free text from within document."""

    category = "Uncategorized"

    def __init__(
        self,
        name: str,
        text: str,
        datestamp: Union[datetime, NoDatestamp] = NoDatestamp(),
        element_id: Union[str, NoID] = NoID(),
    ):
        self.name: str = name
        self.text: str = text

        if not isinstance(element_id, (str, NoID)):
            raise ValueError("element_id must be of type str or NoID")

        if isinstance(element_id, NoID):
            # NOTE(robinson) - Cut the SHA256 hex in half to get the first 128 bits
            element_id = str(uuid.uuid4())

        super().__init__(element_id=element_id)

        if isinstance(datestamp, datetime):
            self.datestamp: datetime = datestamp

    def id_to_hash(self, index_in_sequence: int) -> str:
        """
        Calculates ans assigns a deterministic hash as an ID
        based on element's text, page number, and index in sequence.

        Args:
            index_in_sequence: The index of the element in the sequence of elements.

        Returns:
            The first 32 characters of the SHA256 hash of the concatenated input parameters.
        """
        data = f"{self.text}{self.metadata.page_number}{index_in_sequence}"
        self.id = hashlib.sha256(data.encode()).hexdigest()[:32]
        return self.id

    def has_datestamp(self):
        return "self.datestamp" in globals()

    def __str__(self):
        return f"{self.name}: {self.text}"

    def __eq__(self, other):
        if self.has_datestamp():
            return (
                self.name == other.name
                and self.text == other.text
                and self.datestamp == other.datestamp
            )
        return self.name == other.name and self.text == other.text

    def apply(self, *cleaners: Callable):
        """Applies a cleaning brick to the text element. The function that's passed in
        should take a string as input and produce a string as output."""
        cleaned_text = self.text
        cleaned_name = self.name

        for cleaner in cleaners:
            cleaned_text = cleaner(cleaned_text)
            cleaned_name = cleaner(cleaned_name)

        if not isinstance(cleaned_text, str) or not isinstance(cleaned_name, str):
            raise ValueError("Cleaner produced a non-string output.")

        self.text = cleaned_text
        self.name = cleaned_name


class BodyText(List[Text]):
    """BodyText is an element consisting of multiple, well-formulated sentences. This
    excludes elements such titles, headers, footers, and captions. It is the body of an email."""

    category = "BodyText"


class Recipient(Name):
    """A text element for capturing the recipient information of an email"""

    category = "Recipient"


class Sender(Name):
    """A text element for capturing the sender information of an email"""

    category = "Sender"


class Subject(Text, EmailElement):
    """A text element for capturing the subject information of an email"""

    category = "Subject"


class MetaData(Name):
    """A text element for capturing header meta data of an email
    (miscellaneous data in the email)."""

    category = "MetaData"


class ReceivedInfo(Name):
    """A text element for capturing header information of an email (e.g. IP addresses, etc)."""

    category = "ReceivedInfo"


class Attachment(Name):
    """A text element for capturing the attachment name in an email (e.g. documents,
    images, etc)."""

    category = "Attachment"
