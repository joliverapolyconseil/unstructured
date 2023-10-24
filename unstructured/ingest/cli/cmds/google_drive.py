import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    CliRecursiveConfig,
)
from unstructured.ingest.interfaces import BaseConfig


@dataclass
class GoogleDriveCliConfig(BaseConfig, CliMixin):
    drive_id: str
    service_account_key: str
    extension: t.Optional[str] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--drive-id"],
                required=True,
                type=str,
                help="Google Drive File or Folder ID.",
            ),
            click.Option(
                ["--service-account-key"],
                required=True,
                type=str,
                help="Path to the Google Drive service account json file.",
            ),
            click.Option(
                ["--extension"],
                default=None,
                type=str,
                help="Filters the files to be processed based on extension e.g. .jpg, .docx, etc.",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name="google-drive",
        cli_config=GoogleDriveCliConfig,
        additional_cli_options=[CliRecursiveConfig],
    )
    return cmd_cls
