import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import (
    requires_dependencies,
    validate_date_args,
)

DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z")


@dataclass
class SimpleSlackConfig(BaseConnectorConfig):
    """Connector config to process all messages by channel id's."""

    channels: List[str]
    token: str
    oldest: Optional[str]
    latest: Optional[str]
    verbose: bool = False

    def validate_inputs(self):
        oldest_valid = True
        latest_valid = True

        if self.oldest:
            oldest_valid = validate_date_args(self.oldest)

        if self.latest:
            latest_valid = validate_date_args(self.latest)

        return oldest_valid, latest_valid

    def __post_init__(self):
        oldest_valid, latest_valid = self.validate_inputs()
        if not oldest_valid and not latest_valid:
            raise ValueError(
                "Start and/or End dates are not valid. ",
            )

    @staticmethod
    def parse_channels(channel_str: str) -> List[str]:
        """Parses a comma separated list of channels into a list."""
        return [x.strip() for x in channel_str.split(",")]

@dataclass
class SlackFileMeta:
    date_created: str
    date_modified: str

@dataclass
class SlackIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    config: SimpleSlackConfig
    channel: str
    token: str
    oldest: Optional[str]
    latest: Optional[str]
    file_exists: Optional[bool] = False
    file_meta: Optional[SlackFileMeta] = None
    registry_name: str = "slack"

    # NOTE(crag): probably doesn't matter,  but intentionally not defining tmp_download_file
    # __post_init__ for multiprocessing simplicity (no Path objects in initially
    # instantiated object)
    def _tmp_download_file(self):
        channel_file = self.channel + ".xml"
        return Path(self.standard_config.download_dir) / channel_file

    @property
    def _output_filename(self):
        output_file = self.channel + ".json"
        return Path(self.standard_config.output_dir) / output_file
    
    @property
    def date_created(self) -> Optional[str]:
        if self.file_meta is None:
            self.get_file_metadata()
        return self.file_meta.date_created

    @property
    def date_modified(self) -> Optional[str]:
        if self.file_meta is None:
            self.get_file_metadata()
        return self.file_meta.date_modified
    
    @property
    def exists(self) -> Optional[bool]:
        if self.file_exists is None:
            self.get_file_metadata()
        return self.file_exists
    
    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @requires_dependencies(dependencies=["slack_sdk"], extras="slack")
    def _fetch_messages(self):
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
        self.client = WebClient(token=self.token)
        try:
            oldest = "0"
            latest = "0"
            if self.oldest:
                oldest = self.convert_datetime(self.oldest)

            if self.latest:
                latest = self.convert_datetime(self.latest)

            result = self.client.conversations_history(
                channel=self.channel,
                oldest=oldest,
                latest=latest,
            )
        except SlackApiError as e:
            logger.error(f"Error: {e}")
            self.file_exists = False
            raise
        self.file_exists = True
        return result


    def get_file_metadata(self, messages = None):
        if messages is None:
            messages = self._fetch_messages()
        
        timestamps = [m["ts"] for m in messages]
        timestamps.sort()
        if len(timestamps) > 0:
            created = datetime.fromtimestamp(float(timestamps[0]))
            modified = datetime.fromtimestamp(float(timestamps[len(timestamps)-1]))

        self.file_meta = SlackFileMeta(
            created.isoformat(),
            modified.isoformat()
        )


    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(dependencies=["slack_sdk"], extras="slack")
    def get_file(self):
        from slack_sdk.errors import SlackApiError
        """Fetches the data from a slack channel and stores it locally."""

        self._create_full_tmp_dir_path()

        if self.config.verbose:
            logger.debug(f"fetching channel {self.channel} - PID: {os.getpid()}")
    
        result = self._fetch_messages()
        root = ET.Element("messages")
        for message in result["messages"]:
            message_elem = ET.SubElement(root, "message")
            text_elem = ET.SubElement(message_elem, "text")
            text_elem.text = message.get("text")

            cursor = None
            while True:
                try:
                    response = self.client.conversations_replies(
                        channel=self.channel,
                        ts=message["ts"],
                        cursor=cursor,
                    )

                    for reply in response["messages"]:
                        reply_msg = reply.get("text")
                        text_elem.text = "".join([str(text_elem.text), " <reply> ", reply_msg])

                    if not response["has_more"]:
                        break

                    cursor = response["response_metadata"]["next_cursor"]

                except SlackApiError as e:
                    print(f"Error retrieving replies: {e.response['error']}")
        self.get_file_metadata(result["messages"])
        tree = ET.ElementTree(root)
        tree.write(self._tmp_download_file(), encoding="utf-8", xml_declaration=True)

    def convert_datetime(self, date_time):
        for format in DATE_FORMATS:
            try:
                return datetime.strptime(date_time, format).timestamp()
            except ValueError:
                pass

    @property
    def filename(self):
        """The filename of the file created from a slack channel"""
        return self._tmp_download_file()


@requires_dependencies(dependencies=["slack_sdk"], extras="slack")
class SlackConnector(ConnectorCleanupMixin, BaseConnector):
    """Objects of this class support fetching document(s) from"""

    config: SimpleSlackConfig

    def __init__(self, standard_config: StandardConnectorConfig, config: SimpleSlackConfig):
        super().__init__(standard_config, config)

    def initialize(self):
        """Verify that can get metadata for an object, validates connections info."""
        pass

    def get_ingest_docs(self):
        return [
            SlackIngestDoc(
                self.standard_config,
                self.config,
                channel,
                self.config.token,
                self.config.oldest,
                self.config.latest,
            )
            for channel in self.config.channels
        ]
