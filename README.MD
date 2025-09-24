# Flutter ARB Synchronizer

A Python tool to synchronize Flutter localization ARB files with a Google Spreadsheet. Use it to update ARB files from sheet data or initialize the sheet from existing ARB files.

## Features
- **Three Operation Modes:**
  - **Pull (default)**: Update ARB files from the sheet
  - **Init**: Initialize the sheet from ARB files
  - **Push**: Push new translations to sheet
- Environment variable support with `.env` file
- Reads ARB files location from `l10n.yaml` (expects `arb-dir` entry)
- Detects available languages from ARB filenames (e.g., `app_en.arb`)
- Preserves special characters (e.g., literal `\n` remains as `\n`)
- Supports two-way synchronization between ARB files and Google Sheets

## Prerequisites
- Python 3.12+
- Google Service Account JSON (with Sheets API access)
- A Google Spreadsheet
- Flutter project with `l10n.yaml` configuration

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/flutter_l10n_gsheet_synch.git
cd flutter_l10n_gsheet_synch
```

2. Install dependencies:
```bash
uv sync
```

3. Set up Google Sheets API:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Sheets API
   - Create a Service Account and download the JSON credentials
   - Share your Google Sheet with the service account email

## Usage

### Configuration

#### Option 1: Environment Variables (Recommended)
1. Create a `.env` file in the project root:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your values:
```env
GOOGLE_CREDS_PATH=path/to/your/service-account.json
SHEET_KEY=your_google_sheet_key_here
PROJECT_PATH=path/to/your/flutter/project
```

#### Option 2: Command Line Arguments
```bash
uv run main.py --creds path/to/credentials.json --sheet-key your_sheet_key --project-path path/to/flutter_project 
```

### Command Examples

1. Update ARB files from Google Sheet (default mode):
```bash
uv run main.py
# or explicitly:
uv run main.py --mode pull
```

2. Initialize Google Sheet from existing ARB files:
```bash
uv run main.py --mode init
```

3. Push new translations from ARB files to sheet:
```bash
uv run main.py --mode push
```

### Mode Options
- `pull` (default): Update ARB files from the sheet
- `init`: Initialize the sheet from ARB files
- `push`: Push new values from ARB files to sheet (only adds missing IDs)

### Notes
- The sheet key can be found in your Google Spreadsheet URL: `https://docs.google.com/spreadsheets/d/[SHEET_KEY]/edit`
- The project path should contain a valid `l10n.yaml` file with an `arb-dir` entry
- Make sure your service account has write access to the Google Sheet
- The script expects ARB files to be named as `app_[language_code].arb` (e.g., `app_en.arb`, `app_es.arb`)
- Environment variables take precedence over command line arguments when both are provided

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
