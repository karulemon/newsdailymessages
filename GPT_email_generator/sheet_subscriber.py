import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
load_dotenv()

SHEET_ID = "1yEfLmSe95tDQXWb38KHrfzNSrDUBQr5jXlf9SMHfVJg"

def connect_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_json = os.getenv("GSPREAD_CREDENTIALS_JSON")
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet


def get_subscribers():
    sheet = connect_sheet()
    data = sheet.col_values(1)[1:]  # skip header
    return list(set([email.strip() for email in data if "@" in email]))

def add_subscriber(email):
    sheet = connect_sheet()
    subscribers = get_subscribers()
    if email not in subscribers:
        sheet.append_row([email])
        return True
    return False
