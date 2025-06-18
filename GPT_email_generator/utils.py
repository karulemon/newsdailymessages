import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
load_dotenv()

def send_email_with_summary(insights, to_email):
    try:
        sender_email = "arya.gupta1495@gmail.com"
        sender_password = "nmes edfj grur jswm"

        msg = MIMEMultipart("alternative")
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = f"📬 Your Daily Market Digest – {insights['date']}"

        # Format top articles list
        article_list_html = "".join([
            f"<li><a href='{a['url']}' target='_blank'>{a['title']}</a> – <i>{a['source']}</i></li>"
            for a in insights['top_articles']
        ])

        # Format summary as <p> paragraphs
        formatted_analysis = ""
        for section in insights["analysis"].split("\n"):
            if section.strip():
                if section.strip().endswith(":"):
                    formatted_analysis += f"<h4>{section.strip()}</h4>"
                elif section.strip().startswith("* "):
                    formatted_analysis += f"<ul><li>{section.strip()[2:]}</li></ul>"
                else:
                    formatted_analysis += f"<p>{section.strip()}</p>"

        # Full email HTML
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #2e2e2e; padding: 20px;">
            <h2 style="color: #9d03fc;">📈 Daily Market Digest – {insights['date']}</h2>
            <p><b>Sentiment Score:</b> {insights['sentiment_score']:.2f}</p>
            
            <div style="margin-top: 20px;">
                {formatted_analysis}
            </div>

            <h3 style="margin-top: 30px;">🔗 Top Articles</h3>
            <ul>
                {article_list_html}
            </ul>

            <p style="margin-top: 30px; font-size: 12px; color: gray;">
                Sent by <b>MarketIntel Bot</b>. This is not financial advice.<br>
                You’re receiving this email because you opted-in via the Streamlit app.
            </p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html"))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True

    except Exception as e:
        print(f"❌ Email send error: {e}")
        return False
