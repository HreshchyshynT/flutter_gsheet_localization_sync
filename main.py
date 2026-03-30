import os
import sys
import json
from typing import Optional
import gspread
from gspread.worksheet import Worksheet
import yaml
import config as cfg


class _Colors:
    def __init__(self):
        use_color = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
        if use_color:
            self.RED = "\033[31m"
            self.GREEN = "\033[32m"
            self.YELLOW = "\033[33m"
            self.CYAN = "\033[36m"
            self.BOLD = "\033[1m"
            self.DIM = "\033[2m"
            self.RESET = "\033[0m"
        else:
            self.RED = self.GREEN = self.YELLOW = ""
            self.CYAN = self.BOLD = self.DIM = self.RESET = ""


def arb_files_dir(config_path: str) -> str:
    """
    Read l10n.yaml to get the 'arb-dir' entry.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    arb_dir = config.get("arb-dir")
    if not arb_dir:
        raise ValueError("arb-dir not found in the l10n configuration.")
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
            json_str = json.dumps(arb_data, ensure_ascii=False, indent=2)
            f.write(json_str)
        print(f"Updated {updated_keys} keys in {arb_filename}.")


def parse_sheet_to_dict(sheet_values: list[list[str]]) -> dict[str, dict[str, str]]:
    """
    Parse sheet content (as a list of lists) into a dictionary mapping:
    { id: { language_code: translation, ... } }

    The first row of sheet_values must be the header row:
    e.g. ["id", "en", "pl", ...]
    """
    if not sheet_values or len(sheet_values) < 2:
        raise ValueError(
            "Sheet must have at least a header row and one data row.")

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
        missing_translations = []
        for i in range(1, len(header)):
            lang_code = header[i].strip()
            # If the row doesn't have a value for this column, default to an empty string.
            if i >= len(row) or len(row[i]) == 0:
                missing_translations.append(lang_code)
                continue
            value = row[i]
            lang_translations[lang_code] = value.replace("\\n", "\n")
        translations_dict[id_key] = lang_translations
        if len(missing_translations) > 0:
            print(f"Missing translations for {id_key}: {missing_translations}")

    return translations_dict


def push_values_to_sheet(sheet, localizations: dict[str, dict[str, str]]):
    """
    Update the sheet with only the actual differences from the localizations dictionary.
    Changed cells are updated individually via batch_update, new entries are appended.
    Unchanged data is not touched, keeping Google Sheets version history clean.
    """
    existing_data = sheet.get_all_values()
    if not existing_data:
        # Sheet is empty — write header + all data in one go
        lang_codes = set()
        for translations in localizations.values():
            lang_codes.update(translations.keys())
        lang_codes = sorted(lang_codes)
        header = ["id"] + lang_codes
        rows = [header]
        for str_id, translations in localizations.items():
            row = [str_id]
            for lang in lang_codes:
                row.append(translations.get(lang, "").replace("\n", "\\n"))
            rows.append(row)
        sheet.update("A1", rows)
        sheet.resize(rows=len(rows), cols=len(rows[0]))
        print(f"Initialized sheet with {len(rows) - 1} translation entries.")
        return

    existing_dict = parse_sheet_to_dict(existing_data)
    header = existing_data[0]
    lang_codes = [h.strip() for h in header[1:]]

    # Build row index: translation id -> sheet row number (1-based)
    row_index = {}
    for i, row in enumerate(existing_data[1:], start=2):
        if row and row[0].strip():
            row_index[row[0].strip()] = i

    # Find changed cells in existing rows
    cells_to_update = []
    updated_keys = set()
    for str_id, translations in localizations.items():
        if str_id in existing_dict:
            row_num = row_index[str_id]
            for j, lang in enumerate(lang_codes):
                col_num = j + 2  # column 1 is id, columns 2+ are languages
                local_val = translations.get(lang)
                existing_val = existing_dict[str_id].get(lang)

                if local_val is None:
                    continue  # Don't clear existing translations
                if local_val != existing_val:
                    cell_ref = gspread.utils.rowcol_to_a1(row_num, col_num)
                    cells_to_update.append({
                        "range": cell_ref,
                        "values": [[local_val.replace("\n", "\\n")]],
                    })
                    updated_keys.add(str_id)

    # Find new keys and build rows to append
    new_rows = []
    new_ids = []
    for str_id, translations in localizations.items():
        if str_id not in existing_dict:
            row = [str_id]
            for lang in lang_codes:
                row.append(translations.get(lang, "").replace("\n", "\\n"))
            new_rows.append(row)
            new_ids.append(str_id)

    # Apply only the actual changes
    if cells_to_update:
        sheet.batch_update(cells_to_update)
        print(f"Updated {len(updated_keys)} existing entries ({len(cells_to_update)} cells).")

    if new_rows:
        sheet.append_rows(new_rows)
        print(f"Added {len(new_rows)} new translation entries.")
        print(f"New IDs added: \n\t{'\n\t'.join(sorted(new_ids))}")

    if not cells_to_update and not new_rows:
        print("No changes to push. Local ARB files and sheet are in sync.")


def gather_localizations_from_arbs(
    arbs_dir: str,
) -> tuple[dict[str, dict[str, str]], set[str]]:
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

    # Prepare each row
    for str_id in localizations.keys():
        row = [str_id]
        for lang in lang_codes:
            # replace \n with \\n to avoid newlines in the sheet
            row.append(localizations[str_id].get(
                lang, "").replace("\n", "\\n"))
        rows.append(row)

    # Update the sheet with new data (write first, then trim excess to prevent data loss)
    sheet.update(rows, "A1")
    sheet.resize(rows=len(rows), cols=len(rows[0]))
    print(f"Sheet updated with {len(rows)-1} translation entries.")


def diff_localizations(sheet: Worksheet, localization_dir: str) -> int:
    """
    Compare local ARB files with Google Sheet data and print a colored diff report.
    Returns 0 if in sync, 1 if differences found.
    """
    c = _Colors()

    all_values = sheet.get_all_values()
    sheet_dict = parse_sheet_to_dict(all_values)
    local_dict, _ = gather_localizations_from_arbs(localization_dir)

    local_keys = set(local_dict.keys())
    sheet_keys = set(sheet_dict.keys())

    local_only = sorted(local_keys - sheet_keys)
    sheet_only = sorted(sheet_keys - local_keys)
    common_keys = local_keys & sheet_keys

    # Collect all languages from both sources
    all_languages = set()
    for translations in local_dict.values():
        all_languages.update(translations.keys())
    for translations in sheet_dict.values():
        all_languages.update(translations.keys())
    all_languages = sorted(all_languages)

    changed: dict[str, dict[str, tuple[str, str]]] = {}
    missing: dict[str, dict[str, str]] = {}

    for key in sorted(common_keys):
        local_trans = local_dict[key]
        sheet_trans = sheet_dict[key]

        for lang in all_languages:
            local_val = local_trans.get(lang)
            sheet_val = sheet_trans.get(lang)

            if local_val is not None and sheet_val is not None:
                if local_val != sheet_val:
                    if key not in changed:
                        changed[key] = {}
                    changed[key][lang] = (local_val, sheet_val)
            elif local_val is not None and sheet_val is None:
                if key not in missing:
                    missing[key] = {}
                missing[key][lang] = "sheet"
            elif local_val is None and sheet_val is not None:
                if key not in missing:
                    missing[key] = {}
                missing[key][lang] = "local"

    has_diff = local_only or sheet_only or changed or missing

    if not has_diff:
        print(f"{c.GREEN}Local ARB files and Google Sheet are in sync.{c.RESET}")
        return 0

    in_sync_count = len(common_keys) - len(changed) - len(missing)

    print(f"\n{c.BOLD}=== Localization Diff: Local ARB files vs Google Sheet ==={c.RESET}\n")
    print(f"{c.BOLD}Summary:{c.RESET}")
    print(f"  Keys in sync:              {c.GREEN}{in_sync_count}{c.RESET}")
    if local_only:
        print(f"  Keys only in local (ARB):  {c.GREEN}{len(local_only)}{c.RESET}")
    if sheet_only:
        print(f"  Keys only in sheet:        {c.RED}{len(sheet_only)}{c.RESET}")
    if changed:
        print(f"  Changed translations:      {c.YELLOW}{len(changed)}{c.RESET}")
    if missing:
        print(f"  Missing translations:      {c.CYAN}{len(missing)}{c.RESET}")

    if local_only:
        print(f"\n{c.BOLD}--- Keys only in local (ARB) ---{c.RESET}")
        for key in local_only:
            print(f"  {c.GREEN}+ {key}{c.RESET}")

    if sheet_only:
        print(f"\n{c.BOLD}--- Keys only in sheet ---{c.RESET}")
        for key in sheet_only:
            print(f"  {c.RED}- {key}{c.RESET}")

    if changed:
        print(f"\n{c.BOLD}--- Changed translations ---{c.RESET}")
        for key in sorted(changed.keys()):
            print(f"  {c.BOLD}{key}{c.RESET}")
            for lang, (local_val, sheet_val) in sorted(changed[key].items()):
                local_display = local_val.replace("\n", "\\n")
                sheet_display = sheet_val.replace("\n", "\\n")
                print(f"    {lang}: {c.GREEN}\"{local_display}\"{c.RESET} -> {c.RED}\"{sheet_display}\"{c.RESET}")

    if missing:
        print(f"\n{c.BOLD}--- Missing translations ---{c.RESET}")
        for key in sorted(missing.keys()):
            print(f"  {c.BOLD}{key}{c.RESET}")
            by_source: dict[str, list[str]] = {}
            for lang, source in sorted(missing[key].items()):
                by_source.setdefault(source, []).append(lang)
            for source, langs in sorted(by_source.items()):
                print(f"    {c.CYAN}missing in {source}: {', '.join(langs)}{c.RESET}")

    print()
    return 1


def main():
    config = cfg.init_config()

    # Set up credentials using the provided service account JSON file
    client = gspread.auth.service_account(filename=config.creds_path)

    # Open the spreadsheet using its key and access the first sheet
    sheet = client.open_by_key(config.sheet_key).sheet1

    l10_config = find_l10n_config(config.project_path)
    if not l10_config:
        raise FileNotFoundError("Could not find l10n.yaml in the project directory.")
    localizations_dir = arb_files_dir(l10_config)
    # print localizations_dir and config
    print("localizations_dir: ", localizations_dir)
    print("config: ", l10_config)

    if config.mode == cfg.Mode.INIT:
        # Gather localizations from ARB files
        loc_dict, metadata = gather_localizations_from_arbs(localizations_dir)
        print(
            f"Found {len(metadata)} metadata keys and {
                len(loc_dict)} translation keys in ARB files."
        )

        # Fill the sheet with the gathered data
        fill_sheet_from_localizations(sheet, loc_dict)
    elif config.mode == cfg.Mode.PUSH:
        # Gather localizations from ARB files
        loc_dict, metadata = gather_localizations_from_arbs(localizations_dir)
        print(
            f"Found {len(metadata)} metadata keys and {
                len(loc_dict)} translation keys in ARB files."
        )

        # push new values from loc_dict to sheet
        push_values_to_sheet(sheet, loc_dict)
    elif config.mode == cfg.Mode.DIFF:
        diff_localizations(sheet, localizations_dir)
    else:  # PULL mode (default)
        sync_localizations(sheet, localizations_dir)


if __name__ == "__main__":
    main()
