# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Python CLI tool that synchronizes Flutter ARB localization files with Google Sheets. Supports three modes: **pull** (sheet → ARB files, default), **push** (new ARB keys → sheet, preserves existing), **init** (overwrite sheet from ARB files).

## Commands

```bash
# Install dependencies
uv sync

# Run (uses .env for config)
uv run main.py                # pull mode (default)
uv run main.py --mode init    # init mode
uv run main.py --mode push    # push mode

# Run with explicit args
uv run main.py --creds path/to/creds.json --sheet-key SHEET_KEY --project-path /path/to/flutter/project
```

No tests, linter, or formatter are configured.

## Architecture

Two source files:

- **`config.py`** — CLI arg parsing + `.env` loading via `python-dotenv`. CLI args take precedence over env vars (not the other way around as README states). Defines `Mode` enum (INIT/PUSH/PULL) and `Config` dataclass-like class.

- **`main.py`** — All localization logic:
  - `main()` — Entry point. Reads config, authenticates via `gspread` service account, dispatches to mode handler.
  - `sync_localizations()` — PULL: reads sheet → updates/creates `app_{lang}.arb` files. Merges with existing ARB data.
  - `push_values_to_sheet()` — PUSH: reads ARBs → appends only new IDs to sheet (existing rows untouched).
  - `fill_sheet_from_localizations()` — INIT: reads ARBs → overwrites entire sheet.
  - `gather_localizations_from_arbs()` — Reads all `app_*.arb` files from directory, returns `{id: {lang: translation}}` dict + metadata keys (prefixed with `@`).
  - `parse_sheet_to_dict()` — Parses sheet rows into `{id: {lang: translation}}` dict. Expects header row: `id | en | pl | ...`.

## Key Conventions

- ARB files follow Flutter naming: `app_{language_code}.arb` (e.g., `app_en.arb`)
- ARB directory is resolved from `l10n.yaml`'s `arb-dir` entry in the Flutter project
- Newlines in translations are escaped as `\n` in sheets and unescaped when writing ARB files
- Missing translations for a key are skipped (not written as empty strings)
- Sheet operations write data before resizing to prevent data loss on API failure
- Requires Python >=3.13, managed with `uv`
