import argparse
import os
from typing import Optional
import gspread
import yaml

def l10n_files_dir(config_path: str) -> str:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    arb_dir = config.get("arb-dir")
    if not arb_dir:
        raise Exception("arb-dir not found in the l10n configuration.")
    # Resolve the arb_dir relative to the config_path directory:
    return os.path.abspath(os.path.join(os.path.dirname(config_path), arb_dir))

def find_l10n_config(project_path: str) -> Optional[str]:
    config_path = os.path.join(project_path, "l10n.yaml")
    return config_path if os.path.isfile(config_path) else None

def sync_localizations(sheet_data: list[dict[str, int|str|float]], localization_dir: str):
    pass

def main():
    # Set up command-line arguments
    parser = argparse.ArgumentParser(
        description="Fetch localization data from a Google Sheet and save it to the directory where l10n.yaml is located."
    )
    parser.add_argument(
        "--creds",
        required=True,
        help="Path to the service account JSON credentials file."
    )
    parser.add_argument(
        "--sheet-key",
        required=True,
        help="The key of the Google Spreadsheet (found in its URL)."
    )
    parser.add_argument(
        "--project-path",
        required=True,
        help="Path to the project directory where l10n.yaml is located."
    )
    args = parser.parse_args()

    # Ensure the project path exists
    if not os.path.isdir(args.project_path):
        os.makedirs(args.project_path, exist_ok=True)

    # Set up credentials using the provided service account JSON file
    client = gspread.auth.service_account(filename=args.creds)

    # Open the spreadsheet using its key and access the first sheet
    sheet = client.open_by_key(args.sheet_key).sheet1

    # Read data from the sheet
    data = sheet.get_all_records()
    print(data)

    config = find_l10n_config(args.project_path)
    if not config:
        raise Exception("Could not find l10n.yaml in the project directory.")
    localizations_dir = l10n_files_dir(config)
    # print localizations_dir and config 
    print("localizations_dir: ", localizations_dir)
    print("config: ", config)
    sync_localizations(data, localizations_dir)


if __name__ == "__main__":
    main()
