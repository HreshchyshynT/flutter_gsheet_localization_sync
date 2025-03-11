# Flutter ARB Synchronizer

A Python tool to synchronize Flutter localization ARB files with a Google Spreadsheet. Use it to update ARB files from sheet data or initialize the sheet from existing ARB files.

## Features
- **Three Operation Modes:** 
  - Update ARB files from the sheet (default mode)
  - Initialize the sheet from ARB files using the `--init` flag
  - Push new translations to sheet using the `--push` flag
- Reads arg files location from `l10n.yaml` (expects `arb-dir` entry)
- Detects available languages from ARB filenames (e.g., `app_en.arb`)
- Preserves special characters (e.g., literal `\n` remains as `\n`)
- Supports two-way synchronization between ARB files and Google Sheets

## Prerequisites
- Python 3.7+
- Google Service Account JSON (with Sheets API access)
- A Google Spreadsheet
- Flutter project with `l10n.yaml` configuration

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/flutter_l10n_gsheet_synch.git
cd flutter_l10n_gsheet_synch
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Google Sheets API:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Sheets API
   - Create a Service Account and download the JSON credentials
   - Share your Google Sheet with the service account email

## Usage

### Basic Command Structure
```bash
python main.py --creds path/to/credentials.json --sheet-key your_sheet_key --project-path path/to/flutter_project
```

### Command Examples

1. Update ARB files from Google Sheet (default mode):
```bash
python main.py --creds service_account.json --sheet-key 1234567890abcdef --project-path ./my_flutter_project
```

2. Initialize Google Sheet from existing ARB files:
```bash
python main.py --creds service_account.json --sheet-key 1234567890abcdef --project-path ./my_flutter_project --init
```

3. Push new translations from ARB files to sheet:
```bash
python main.py --creds service_account.json --sheet-key 1234567890abcdef --project-path ./my_flutter_project --push
```

### Notes
- The sheet key can be found in your Google Spreadsheet URL: `https://docs.google.com/spreadsheets/d/[SHEET_KEY]/edit`
- The project path should contain a valid `l10n.yaml` file with an `arb-dir` entry
- Make sure your service account has write access to the Google Sheet
- The script expects ARB files to be named as `app_[language_code].arb` (e.g., `app_en.arb`, `app_es.arb`)

## Sheet Format
The Google Sheet should be structured as follows:
- First row is the header: `id | en | es | fr | ...` (language codes)
- First column contains string IDs
- Subsequent columns contain translations for each language

Example:
| id | en | es | fr |
|----|----|----|-------|
| welcome_message | Welcome | Bienvenido | Bienvenue |
| goodbye | Goodbye | Adiós | Au revoir |

## Contributing
Feel free to open issues or submit pull requests for improvements and bug fixes.

## License
[MIT License](LICENSE)
