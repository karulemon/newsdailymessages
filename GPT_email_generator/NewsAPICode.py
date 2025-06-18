import os
import requests
from datetime import datetime, timedelta
import google.generativeai as genai
import textwrap
from textblob import TextBlob
from dotenv import load_dotenv
load_dotenv()

# Environment variables
SERP_API_KEY = os.getenv("SERP_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Safety Checks
if not SERP_API_KEY:
    print("🛑 ERROR: SERP_API_KEY not found. Please set the environment variable.")
    exit()
if not NEWS_API_KEY:
    print("🛑 ERROR: NEWS_API_KEY not found. Please set the environment variable.")
    exit()
if not GOOGLE_API_KEY:
    print("🛑 ERROR: GOOGLE_API_KEY environment variable not set.")
    print("   Please get a key from https://aistudio.google.com/ and set the environment variable.")
    exit()

# Configure Google Generative AI
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    llm_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    print("✅ Google Generative AI (Gemini) Initialized.")
except Exception as e:
    print(f"🛑 ERROR: Failed to configure Google Generative AI: {e}")
    exit()

class MarketInsightsApp:
    def __init__(self):
        self.serp_api_key = SERP_API_KEY
        self.news_api_key = NEWS_API_KEY
        self.model = llm_model
        self.news_base_url = "https://newsapi.org/v2"

    def fetch_daily_market_summary_serpapi(self, num_results=40):
        """Fetch today's comprehensive market news using SerpAPI"""
        print(f"\n🔍 Fetching today's comprehensive market summary...")
        
        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Comprehensive market query for today's summary
        market_query = f"stock market today {today} financial markets trading earnings economic news S&P 500 Dow Jones NASDAQ"
        
        # SerpAPI REST endpoint
        url = "https://serpapi.com/search"
        params = {
            "q": market_query,
            "tbm": "nws",
            "num": num_results,
            "tbs": "qdr:d",  # Results from past day
            "api_key": self.serp_api_key,
            "engine": "google"
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            results = response.json()
            
            articles = results.get("news_results", [])
            
            if not articles:
                print("⚠️ No market news results found from SerpAPI for today.")
                return None

            # Normalize SerpAPI format
            normalized_articles = []
            for article in articles:
                normalized_articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("snippet", ""),
                    "source": {"name": article.get("source", "Unknown")},
                    "publishedAt": article.get("date", ""),
                    "url": article.get("link", "")
                })
            
            print(f"✅ Found {len(normalized_articles)} market articles for today's summary.")
            return {"articles": normalized_articles}
            
        except requests.exceptions.RequestException as e:
            print(f"🛑 SerpAPI request failed: {e}")
            return None
        except Exception as e:
            print(f"🛑 SerpAPI fetch failed: {e}")
            return None

    def fetch_specific_topic_newsapi(self, query, days=7, page_size=25):
        """Fetch specific topic news using NewsAPI"""
        print(f"\n🔍 Searching for '{query}' using NewsAPI...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        from_date = start_date.strftime("%Y-%m-%d")
        to_date = end_date.strftime("%Y-%m-%d")
        
        url = f"{self.news_base_url}/everything"
        params = {
            "q": query,
            "from": from_date,
            "to": to_date,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": page_size,
            "apiKey": self.news_api_key
        }

        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "ok":
                if data.get("totalResults", 0) > 0:
                    print(f"✅ Found {data['totalResults']} articles for '{query}' (processing top {len(data.get('articles',[]))}).")
                    return data
                else:
                    print(f"⚠️ No articles found for '{query}' in the last {days} days.")
                    return None
            else:
                err_code = data.get("code", "Unknown")
                err_msg = data.get("message", "Unknown API error")
                print(f"🛑 NewsAPI Error ({err_code}): {err_msg}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"🛑 NewsAPI request failed: {e}")
            return None
        except Exception as e:
            print(f"🛑 NewsAPI fetch failed: {e}")
            return None

    def _format_articles_for_llm(self, articles, max_articles=30):
        """Formats news articles into a text block suitable for LLM prompt."""
        print(f"📝 Formatting {min(len(articles), max_articles)} articles for AI analysis...")
        content_pieces = []
        processed_count = 0
        
        for article in articles:
            if processed_count >= max_articles:
                break

            title = article.get("title", "N/A")
            source = article.get("source", {}).get("name", "N/A")
            description = article.get("description", "")
            published_at = article.get("publishedAt", "N/A")

            # Basic cleaning
            if description:
                description = description.replace("\r\n", " ").replace("\n", " ")
                description = description.split(" [+")[0]  # Remove common truncation markers
                description = description[:400]  # Limit length

            if title and title != "N/A":
                content_pieces.append(
                    f"--- Article {processed_count + 1} ---\n"
                    f"Title: {title}\n"
                    f"Source: {source}\n"
                    f"Time: {published_at}\n"
                    f"Summary: {description}\n"
                )
                processed_count += 1

        if not content_pieces:
            return None

        return "\n".join(content_pieces)

    def _get_llm_response(self, prompt):
        """Sends prompt to the LLM and returns the text response."""
        print("🤖 Generating AI analysis...")
        try:
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
            ]
            response = self.model.generate_content(prompt, safety_settings=safety_settings)

            if response.parts:
                return response.text.strip()
            elif response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text.strip()
            else:
                return "LLM analysis could not be generated (possibly due to safety filters)."
                
        except Exception as e:
            print(f"🛑 ERROR: LLM generation failed: {e}")
            return f"Error during LLM analysis: {e}"

    def analyze_sentiment_basic(self, articles):
        """Performs basic sentiment scoring using TextBlob."""
        if not articles:
            return {"polarity": 0, "subjectivity": 0}

        text_parts = []
        for a in articles:
            title = a.get("title", "") or ""
            desc = a.get("description", "") or ""
            if title or desc:
                cleaned_text = (title + " " + desc).replace("\r\n", " ").replace("\n", " ")
                text_parts.append(cleaned_text)

        if not text_parts:
            return {"polarity": 0, "subjectivity": 0}

        full_text = " ".join(text_parts)
        try:
            blob = TextBlob(full_text)
            return {
                "polarity": round(blob.sentiment.polarity, 3),
                "subjectivity": round(blob.sentiment.subjectivity, 3)
            }
        except Exception as e:
            print(f"⚠️ Error during sentiment analysis: {e}")
            return {"polarity": 0, "subjectivity": 0}

    def get_daily_market_summary(self):
        """Generate today's comprehensive market summary using SerpAPI"""
        today_date = datetime.now().strftime("%B %d, %Y")
        
        # Fetch today's market news from SerpAPI
        news_data = self.fetch_daily_market_summary_serpapi()
        if not news_data or not news_data.get("articles"):
            return {
                "status": "error",
                "message": "Could not retrieve today's market news. Please check SerpAPI connection."
            }

        articles = news_data["articles"]
        basic_sentiment = self.analyze_sentiment_basic(articles)
        polarity_score = basic_sentiment['polarity']

        # Format articles for LLM
        formatted_articles = self._format_articles_for_llm(articles, max_articles=35)
        if not formatted_articles:
            return {"status": "error", "message": "Could not format articles for analysis."}

        # LLM prompt for daily market summary
        prompt = f"""
        You are a senior business and market analyst. Analyze today's ({today_date}) full spectrum of business, startup, and market news to produce a detailed daily digest.
        
        Overall sentiment polarity: {polarity_score:.2f} (-1 = very negative, 0 = neutral, +1 = very positive)
        
        Your summary should be structured with the following sections:
        
        1. **MARKET OVERVIEW (3-5 sentences):** Summarize today's major market movements and the performance of key indices (S&P 500, Dow, NASDAQ), global cues, and investor sentiment.
        
        2. **TOP BUSINESS & STARTUP HIGHLIGHTS (5-7 bullet points):** Spotlight key events from the world of startups, big tech, new funding rounds, M&A deals, IPO buzz, regulatory changes, or product launches.
        
        3. **SECTOR & INDUSTRY WATCH:** Highlight performance across key sectors (Tech, Consumer, Finance, Energy, etc.), and note any emerging industry-specific trends or shifts.
        
        4. **BREAKTHROUGH PRODUCTS & TECH TRENDS:** Cover any newly launched or trending products, viral technologies, or innovations that gained traction today.
        
        5. **KEY COMPANY MOVES:** List notable updates from large public or private companies (earnings, leadership changes, controversies, expansions).
        
        6. **MACRO & POLICY ROUNDUP:** Mention any economic data releases, Fed announcements, government policies, or global events that impacted sentiment or markets.
        
        7. **SENTIMENT SNAPSHOT:** Describe the tone of the day across investors, media, and public perception. Was the day optimistic, cautious, fearful, or speculative?
        
        8. **WHAT TO WATCH TOMORROW:** Curate what investors, founders, and business watchers should look out for tomorrow — earnings reports, major announcements, or expected events.
        
        Be insightful and concise. Prioritize relevance and clarity for readers interested in both markets and the broader business ecosystem.
        
        --- TODAY'S BUSINESS & MARKET NEWS ---
        {formatted_articles}
        --- END NEWS ---
        
        DAILY BUSINESS DIGEST - {today_date}:
        """


        # Get AI analysis
        llm_analysis = self._get_llm_response(prompt)

        return {
            "status": "success",
            "type": "daily_summary",
            "date": today_date,
            "article_count": len(articles),
            "sentiment_score": polarity_score,
            "analysis": llm_analysis,
            "top_articles": [
                {
                    "title": a.get("title"),
                    "source": a.get("source", {}).get("name"),
                    "time": a.get("publishedAt"),
                    "url": a.get("url")
                } for a in articles[:10] if a.get("title")
            ]
        }

    def get_specific_topic_insights(self, query):
        """Generate insights for a specific topic using NewsAPI"""
        # Fetch topic-specific news from NewsAPI
        news_data = self.fetch_specific_topic_newsapi(query)
        if not news_data or not news_data.get("articles"):
            return {
                "status": "error",
                "message": f"Could not retrieve articles for '{query}'. Please try a different search term."
            }

        articles = news_data["articles"]
        basic_sentiment = self.analyze_sentiment_basic(articles)
        polarity_score = basic_sentiment['polarity']

        # Format articles for LLM
        formatted_articles = self._format_articles_for_llm(articles, max_articles=25)
        if not formatted_articles:
            return {"status": "error", "message": "Could not format articles for analysis."}

        # LLM prompt for specific topic analysis
        prompt = f"""
        You are a financial analyst specializing in company and sector research. Analyze recent news about "{query}" and provide detailed insights.

        Sentiment polarity score: {polarity_score:.2f} (-1 = very negative, 0 = neutral, +1 = very positive)

        Based on the articles, provide:

        1. **EXECUTIVE SUMMARY (3-4 sentences):** Key developments regarding "{query}" in recent news.

        2. **SENTIMENT ANALYSIS:** Current sentiment around "{query}" (positive/negative/mixed) and why.

        3. **KEY DEVELOPMENTS (bullet points):** Major news events, announcements, or changes related to "{query}".

        4. **FINANCIAL IMPACT:** Any mention of financial performance, earnings, revenue, or market impact.

        5. **MARKET IMPLICATIONS:** How might these developments affect the stock price, sector, or market?

        6. **RELATED ENTITIES:** Other companies, competitors, or sectors mentioned in relation to "{query}".

        7. **INVESTMENT PERSPECTIVE:** What should investors know about "{query}" based on this news?

        Be objective and focus on facts from the articles. Highlight both opportunities and risks mentioned.

        --- NEWS ARTICLES ABOUT "{query}" ---
        {formatted_articles}
        --- END ARTICLES ---

        ANALYSIS FOR "{query}":
        """

        # Get AI analysis
        llm_analysis = self._get_llm_response(prompt)

        return {
            "status": "success",
            "type": "topic_search",
            "query": query,
            "article_count": len(articles),
            "sentiment_score": polarity_score,
            "analysis": llm_analysis,
            "top_articles": [
                {
                    "title": a.get("title"),
                    "source": a.get("source", {}).get("name"),
                    "published_at": a.get("publishedAt"),
                    "url": a.get("url")
                } for a in articles[:7] if a.get("title")
            ]
        }

    def print_insights(self, insights):
        """Print insights in a readable format"""
        if insights.get("status") == "error":
            print(f"🛑 Error: {insights.get('message')}")
            return

        print("\n" + "=" * 100)
        
        if insights.get("type") == "daily_summary":
            print(f"📈 DAILY MARKET SUMMARY - {insights['date']}")
            print("=" * 100)
            print(f"\n📊 Analyzed {insights['article_count']} articles | Market Sentiment: {insights['sentiment_score']:.2f}")
        else:
            print(f"🔍 TOPIC ANALYSIS: {insights['query'].upper()}")
            print("=" * 100)
            print(f"\n📊 Analyzed {insights['article_count']} articles | Sentiment: {insights['sentiment_score']:.2f}")

        print("-" * 100)
        print("\n🤖 AI ANALYSIS:")
        print("-" * 100)
        print(textwrap.fill(insights.get('analysis', 'Analysis not available.'), width=98))
        print("-" * 100)

        print(f"\n📰 TOP ARTICLES FOR REFERENCE:")
        print("-" * 100)
        if not insights['top_articles']:
            print("  (No articles available)")
        else:
            for i, article in enumerate(insights['top_articles'], 1):
                print(f"{i}. {article.get('title', 'N/A')}")
                print(f"   📺 {article.get('source', 'Unknown')} | ⏰ {article.get('published_at') or article.get('time', 'N/A')}")
                if article.get('url'):
                    print(f"   🔗 {article.get('url')}")
                print()

        print("=" * 100)

def main():
    app = MarketInsightsApp()

    print("📈 COMPREHENSIVE MARKET INSIGHTS GENERATOR 📊")
    print("=" * 60)
    print("1. Daily Market Summary (SerpAPI) - Today's complete market overview")
    print("2. Specific Topic Search (NewsAPI) - Search companies, sectors, etc.")
    print("=" * 60)

    while True:
        print("\n🔹 OPTIONS:")
        print("1. Get today's daily market summary")
        print("2. Search for specific topic/company")
        print("3. Exit")
        
        choice = input("\nSelect option (1, 2, or 3): ").strip()
        
        if choice == "1":
            print(f"\n🔄 Generating today's comprehensive market summary...")
            insights = app.get_daily_market_summary()
            app.print_insights(insights)
            
        elif choice == "2":
            query = input("\nEnter company name, ticker, or topic to search: ").strip()
            if not query:
                print("Please enter a search term.")
                continue
            print(f"\n🔄 Searching for insights on '{query}'...")
            insights = app.get_specific_topic_insights(query)
            app.print_insights(insights)
            
        elif choice == "3":
            print("\n👋 Thank you for using Market Insights Generator!")
            break
            
        else:
            print("Invalid option. Please select 1, 2, or 3.")

        # Disclaimer
        print("\n⚠️  DISCLAIMER: This is AI-generated analysis, NOT financial advice. Always DYOR!")

if __name__ == "__main__":
    main()