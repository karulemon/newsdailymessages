import streamlit as st
import io
import sys
from NewsAPICode import MarketInsightsApp
from MarketInsightsReddit import get_llm_market_insights
from utils import send_email_with_summary
from sheet_subscriber import add_subscriber  # uses Google Sheets
from dotenv import load_dotenv
load_dotenv()

# --- App config ---
st.set_page_config(page_title="Market Intel Dashboard", layout="wide")
st.title("📈 Market Intel Dashboard")

# --- Sidebar Navigation ---
feature = st.sidebar.radio("Choose Feature", [
    "📬 Email Daily Market Summary",
    "🔍 Topic Insights (News)",
    "🧠 Reddit Sentiment Analyzer"
])

# --- Initialize News App ---
news_app = MarketInsightsApp()

# --- 1. Email Daily Summary ---
if feature == "📬 Email Daily Market Summary":
    st.header("📬 Receive Market Summary via Email")

    email = st.text_input("Enter your email address")

    if st.button("Send Summary"):
        summary = news_app.get_daily_market_summary()
        if summary["status"] == "success":
            success = send_email_with_summary(summary, email)
            if success:
                st.success(f"✅ Summary sent to **{email}**")
            else:
                st.error("❌ Failed to send email.")
        else:
            st.warning(summary["message"])

    with st.expander("📩 Or subscribe to get this daily:"):
        sub_email = st.text_input("Enter your email to subscribe")
        if st.button("Subscribe Me"):
            if "@" not in sub_email:
                st.error("❌ Enter a valid email address.")
            else:
                added = add_subscriber(sub_email)
                if added:
                    st.success("✅ Subscribed! You’ll get the market summary daily.")
                else:
                    st.info("You’re already subscribed.")

# --- 2. Topic Insight (NewsAPI + Gemini) ---
elif feature == "🔍 Topic Insights (News)":
    st.header("🔍 Analyze Any Topic")
    topic = st.text_input("Enter a topic, company, or market keyword")

    if st.button("Analyze Topic"):
        result = news_app.get_specific_topic_insights(topic)
        if result["status"] == "success":
            st.markdown("### 📌 Gemini AI Analysis")
            st.markdown(result["analysis"])
            st.markdown("### 📰 Top Articles")
            for art in result["top_articles"]:
                st.markdown(f"- [{art['title']}]({art['url']}) – *{art['source']}*")
        else:
            st.warning(result["message"])

# --- 3. Reddit Sentiment Analysis ---
elif feature == "🧠 Reddit Sentiment Analyzer":
    st.header("🧠 Analyze Reddit Sentiment on Any Topic")
    keyword = st.text_input("Enter a market keyword (e.g., Bitcoin, Adani, AI)")
    start_date = st.date_input("Start Date (optional)")
    end_date = st.date_input("End Date (optional)")

    if st.button("Analyze Reddit"):
        start_str = start_date.strftime('%Y-%m-%d') if start_date else None
        end_str = end_date.strftime('%Y-%m-%d') if end_date else None

        # Capture printed output
        buffer = io.StringIO()
        sys_stdout = sys.stdout
        sys.stdout = buffer
        try:
            get_llm_market_insights(keyword, start_str, end_str)
        finally:
            sys.stdout = sys_stdout

        reddit_output = buffer.getvalue()
        st.markdown("### 🧾 Reddit Insights")
        st.code(reddit_output, language='markdown')
