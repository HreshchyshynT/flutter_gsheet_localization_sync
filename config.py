import os
import argparse
from dotenv import load_dotenv
from enum import Enum


class Mode(Enum):
    INIT = "init"
    PUSH = "push"
    PULL = "pull"
    DIFF = "diff"


class Config:
    creds_path: str
    sheet_key: str
    project_path: str
    mode: Mode

    def __init__(self,
                 creds_path: str,
                 sheet_key: str,
                 project_path: str,
                 mode: Mode,
                 ):
        self.creds_path = creds_path
        self.sheet_key = sheet_key
        self.project_path = project_path
        self.mode = mode


def init_config() -> Config:
    # Load environment variables from .env file
    load_dotenv()

    # Set up command-line arguments (now optional, fallback to env vars)
    parser = argparse.ArgumentParser(
        description="Fetch localization data from a Google Sheet or initialize the sheet from ARB files."
    )
    parser.add_argument(
        "--creds", help="Path to the service account JSON credentials file."
    )
    parser.add_argument(
        "--sheet-key", help="The key of the Google Spreadsheet (found in its URL)."
    )
    parser.add_argument(
        "--project-path",
        help="Path to the project directory where l10n.yaml is located.",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["init", "push", "pull", "diff"],
        default="pull",
        help="Operation mode: init (initialize sheet from ARB files), push (push new values from ARB files to sheet), pull (update ARB files from sheet, default), diff (show differences between local ARB files and sheet)",
    )
    args = parser.parse_args()

    creds_path = args.creds or os.getenv("GOOGLE_CREDS_PATH")
    sheet_key = args.sheet_key or os.getenv("SHEET_KEY")
    project_path = args.project_path or os.getenv("PROJECT_PATH")
    mode = Mode(args.mode)

    if creds_path:
        creds_path = os.path.expanduser(creds_path)
    if project_path:
        project_path = os.path.expanduser(project_path)

    if not creds_path:
        raise ValueError(
            "Google credentials path is required. Set GOOGLE_CREDS_PATH env var or use --creds argument."
        )
    if not sheet_key:
        raise ValueError(
            "Sheet key is required. Set SHEET_KEY env var or use --sheet-key argument."
        )
    if not project_path:
        raise ValueError(
            "Project path is required. Set PROJECT_PATH env var or use --project-path argument."
        )

    if not os.path.isdir(project_path):
        raise FileNotFoundError("Project path does not exist.")

    return Config(creds_path, sheet_key, project_path, mode)
