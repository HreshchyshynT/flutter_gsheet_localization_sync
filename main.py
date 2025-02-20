import argparse
import os
import json
from typing import Optional
import gspread
from gspread.worksheet import Worksheet
import yaml

def arb_files_dir(config_path: str) -> str:
    """
    Read l10n.yaml to get the 'arb-dir' entry.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    arb_dir = config.get("arb-dir")
    if not arb_dir:
        raise Exception("arb-dir not found in the l10n configuration.")
    # Resolve the arb_dir relative to the config_path directory:
    return os.path.abspath(os.path.join(os.path.dirname(config_path), arb_dir))

def find_l10n_config(project_path: str) -> Optional[str]:
    """Find the l10n.yaml configuration file in the project directory."""
    config_path = os.path.join(project_path, "l10n.yaml")
    return config_path if os.path.isfile(config_path) else None

def sync_localizations(sheet: Worksheet, localization_dir: str):
    """
    Update ARB files in localization_dir with data from the sheet.
    
    The sheet is expected to have a header row: ["id", "en", "pl", ...]
    The function reads the sheet data, converts it to a dictionary:
      { id: { language_code: translation, ... } }
    and then updates (or creates) ARB files named app_<language_code>.arb.
    """
    all_values = sheet.get_all_values()
    sheet_dict = parse_sheet_to_dict(all_values)
    
    header = all_values[0]
    language_codes = [col.strip() for col in header[1:]]
    
    for lang in language_codes:
        arb_filename = f"app_{lang}.arb"
        arb_filepath = os.path.join(localization_dir, arb_filename)
        arb_data = {}
        if os.path.isfile(arb_filepath):
            with open(arb_filepath, "r", encoding="utf-8") as f:
                arb_data = json.load(f)
        
        updated_keys = 0
        for trans_id, translations in sheet_dict.items():
            if lang in translations:
                arb_data[trans_id] = translations[lang]
                updated_keys += 1
        
        with open(arb_filepath, "w", encoding="utf-8") as f:
            json.dump(arb_data, f, ensure_ascii=False, indent=2)
        print(f"Updated {updated_keys} keys in {arb_filename}.")

def parse_sheet_to_dict(sheet_values: list[list[str]]) -> dict[str, dict[str, str]]:
    """
    Parse sheet content (as a list of lists) into a dictionary mapping:
    { id: { language_code: translation, ... } }
    
    The first row of sheet_values must be the header row:
    e.g. ["id", "en", "pl", ...]
    """
    if not sheet_values or len(sheet_values) < 2:
        raise ValueError("Sheet must have at least a header row and one data row.")
    
    header = sheet_values[0]
    # Ensure the header has at least an "id" column.
    if header[0].strip().lower() != "id":
        raise ValueError("The first header column must be 'id'.")
    
    translations_dict = {}
    for row in sheet_values[1:]:
        # Skip empty rows
        if not row or not row[0].strip():
            continue
        id_key = row[0].strip()
        # Create a dict for this id with language code -> translation.
        # We'll iterate over the rest of the columns.
        lang_translations = {}
        for i in range(1, len(header)):
            lang_code = header[i].strip()
            # If the row doesn't have a value for this column, default to an empty string.
            value = row[i].strip() if i < len(row) else ""
            lang_translations[lang_code] = value
        translations_dict[id_key] = lang_translations

    return translations_dict

def gather_localizations_from_arbs(arbs_dir: str) -> tuple[dict[str, dict[str, str]], set[str]]:
    """
    Gathers localization data from ARB files in the given directory.
    Files must be named in the format: app_[language_code].arb.
    Returns a tuple: (localizations_dict, metadata_keys)
    
    localizations_dict: { id: { language_code: translation, ... } }
    metadata_keys: set of keys that start with "@" encountered in ARB files.
    """
    localizations = {}
    metadata_keys = set()
    
    for filename in os.listdir(arbs_dir):
        if filename.startswith("app_") and filename.endswith(".arb"):
            # Extract language code from filename. Example: app_en.arb -> "en"
            parts = filename.split("_")
            if len(parts) < 2:
                continue
            lang_part = parts[1]
            language_code = lang_part.split(".")[0]
            file_path = os.path.join(arbs_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                arb_data = json.load(f)
            for key, value in arb_data.items():
                if key.startswith("@"):
                    metadata_keys.add(key)
                else: 
                    if key not in localizations:
                        localizations[key] = {}
                    localizations[key][language_code] = value
    return localizations, metadata_keys

def fill_sheet_from_localizations(sheet, localizations: dict[str, dict[str, str]]):
    """
    Fill the provided sheet with data from the localizations dictionary.
    The first row is a header: ["id", sorted_language_codes...]
    Each subsequent row contains the id and corresponding translations.
    """
    # Determine the complete set of language codes
    lang_codes = set()
    for translations in localizations.values():
        lang_codes.update(translations.keys())
    lang_codes = sorted(lang_codes)
    
    # Prepare header row
    header = ["id"] + lang_codes
    rows = [header]
    
    # Prepare each row; sort keys for consistency.
    for str_id in localizations.keys():
        row = [str_id]
        for lang in lang_codes:
            row.append(localizations[str_id].get(lang, ""))
        rows.append(row)
    
    # Clear the sheet and update with new data
    sheet.clear()
    sheet.update (rows,"A1")
    print(f"Sheet updated with {len(rows)-1} translation entries.")


def main():
    # Set up command-line arguments
    parser = argparse.ArgumentParser(
        description="Fetch localization data from a Google Sheet or initialize the sheet from ARB files."
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
    parser.add_argument(
        "--init",
        action="store_true",
        help="If provided, initialize the sheet from ARB files (default is to update ARB files from sheet)."
    )
    args = parser.parse_args()

    # Ensure the project path exists
    if not os.path.isdir(args.project_path):
        raise Exception("Project path does not exist.")

    # Set up credentials using the provided service account JSON file
    client = gspread.auth.service_account(filename=args.creds)

    # Open the spreadsheet using its key and access the first sheet
    sheet = client.open_by_key(args.sheet_key).sheet1

    config = find_l10n_config(args.project_path)
    if not config:
        raise Exception("Could not find l10n.yaml in the project directory.")
    localizations_dir = arb_files_dir(config)
    # print localizations_dir and config 
    print("localizations_dir: ", localizations_dir)
    print("config: ", config)


    if args.init:
        # Gather localizations from ARB files
        loc_dict, metadata = gather_localizations_from_arbs(localizations_dir)
        print(f"Found {len(metadata)} metadata keys and {len(loc_dict)} translation keys in ARB files.")
        
        # Fill the sheet with the gathered data
        fill_sheet_from_localizations(sheet, loc_dict)
    else:
        sync_localizations(sheet, localizations_dir)


if __name__ == "__main__":
    main()
