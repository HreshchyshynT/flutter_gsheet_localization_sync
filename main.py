import argparse
import gspread

def main():
    # Set up command-line arguments
    parser = argparse.ArgumentParser(
        description="Fetch localization data from a Google Sheet."
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
    args = parser.parse_args()

    # Instead of using gspread.authorize, use the service_account function:
    gc = gspread.auth.service_account(filename=args.creds)

    # Open the spreadsheet using its key and access the first sheet
    sheet = gc.open_by_key(args.sheet_key).sheet1

    # Read data from the sheet
    data = sheet.get_all_records()
    print(data)

if __name__ == "__main__":
    main()
