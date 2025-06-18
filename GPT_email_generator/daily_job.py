# daily_job.py

from NewsAPICode import MarketInsightsApp
from utils import send_email_with_summary
from sheet_subscriber import get_subscribers
from dotenv import load_dotenv
load_dotenv()
  # ✅ now using Sheets

def send_daily_digest_to_subscribers():
    """Fetches daily market summary and sends it to all Google Sheet subscribers."""
    app = MarketInsightsApp()
    summary = app.get_daily_market_summary()

    if summary["status"] != "success":
        print("❌ Failed to generate daily summary.")
        return

    subscribers = get_subscribers()
    if not subscribers:
        print("📭 No active subscribers found in Google Sheet.")
        return

    print(f"📨 Sending daily summary to {len(subscribers)} subscribers...\n")
    for email in subscribers:
        success = send_email_with_summary(summary, email)
        if success:
            print(f"✅ Sent to {email}")
        else:
            print(f"❌ Failed to send to {email}")

if __name__ == "__main__":
    send_daily_digest_to_subscribers()
