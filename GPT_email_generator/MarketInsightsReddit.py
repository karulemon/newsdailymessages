import json
import praw
from textblob import TextBlob
import time
from datetime import datetime, timedelta
from collections import Counter
import google.generativeai as genai
import os
import textwrap 
from dotenv import load_dotenv
load_dotenv()

# For formatting LLM output

# ----------- LOAD ENVIRONMENT VARIABLES (Optional but Recommended) -----------
# from dotenv import load_dotenv
# load_dotenv() # Load variables from a .env file if you have one

# ----------- API KEYS AND CONFIG -----------
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "") # Use env var or default
REDDIT_SECRET = os.getenv("REDDIT_SECRET", "") # Use env var or default
REDDIT_USER_AGENT = "PiggyLime's Advanced Market Bot v3" # Update user agent
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY','') # Get Google AI key from environment

# --- Safety Check ---
if not GOOGLE_API_KEY:
    print("🛑 ERROR: GOOGLE_API_KEY environment variable not set.")
    print("   Please get a key from https://aistudio.google.com/ and set the environment variable.")
    exit() # Exit if the key is missing

# ----------- INIT APIS -----------
# Initialize Reddit API
try:
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        # check_for_async=False # Optional: Add if encountering related warnings
    )
    print(f"Reddit API Initialized (Read Only: {reddit.read_only})")
except Exception as e:
    print(f"🛑 ERROR: Failed to initialize Reddit API: {e}")
    exit()

# Configure Google Generative AI
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    # Consider using gemini-1.5-flash for potentially faster/cheaper summaries
    # or gemini-1.5-pro for larger context windows if needed.
    llm_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    print("Google Generative AI (Gemini) Initialized.")
except Exception as e:
    print(f"🛑 ERROR: Failed to configure Google Generative AI: {e}")
    exit()


# ----------- SENTIMENT ANALYSIS (Keep your enhanced version) -----------
def analyze_sentiment(text):
    """Enhanced sentiment analysis with context awareness for financial text"""
    if not text or not isinstance(text, str):
        return 0.0

    # Base sentiment from TextBlob
    blob = TextBlob(text)
    base_sentiment = blob.sentiment.polarity

    # Financial context adjustment (Your custom logic)
    financial_boosters = {
        'crash': -0.3, 'collapse': -0.3, 'plummet': -0.3, 'tank': -0.25,
        'bearish': -0.2, 'sell-off': -0.2, 'downturn': -0.15, 'recession': -0.25,
        'bankruptcy': -0.35, 'default': -0.25, 'debt': -0.1, 'inflation': -0.1,

        'bullish': 0.2, 'rally': 0.2, 'surge': 0.25, 'soar': 0.25,
        'outperform': 0.2, 'beat': 0.15, 'growth': 0.15, 'profit': 0.2,
        'buy': 0.1, 'upgrade': 0.15, 'dividend': 0.15, 'recovery': 0.15
    }

    text_lower = text.lower()
    sentiment_adjustment = 0

    for term, value in financial_boosters.items():
        if term in text_lower:
            sentiment_adjustment += value

    adjusted_sentiment = max(min(base_sentiment + sentiment_adjustment, 1.0), -1.0)
    return adjusted_sentiment

# ----------- DATE CONVERSION (Keep as is) -----------
def convert_time_filter(start_date, end_date):
    """Convert date range to appropriate Reddit time filter"""
    now = datetime.now()
    days_diff = (now - start_date).days

    if days_diff <= 1: return 'day'
    elif days_diff <= 7: return 'week'
    elif days_diff <= 31: return 'month'
    elif days_diff <= 365: return 'year'
    else: return 'all'

# ----------- DATE PARSING (Keep as is) -----------
def parse_date(date_str):
    """Parse date string into datetime object"""
    if not date_str or not isinstance(date_str, str): return None
    try:
        formats = [ '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y',
                    '%m-%d-%Y', '%d %b %Y', '%b %d %Y' ]
        for fmt in formats:
            try: return datetime.strptime(date_str, fmt)
            except ValueError: continue
        raise ValueError(f"Couldn't parse date: {date_str}")
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None

# ----------- REDDIT ANALYSIS (Keep your enhanced version) -----------
def fetch_reddit(keyword, start_date=None, end_date=None, limit=15, min_score=2):
    """ Enhanced Reddit data collection with date filtering (returns list of dicts) """
    print(f"\n🔍 Reddit posts on: '{keyword}'")

    date_str = ""
    time_filter = 'month' # Default
    if start_date and end_date:
        date_str = f" from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        time_filter = convert_time_filter(start_date, datetime.now())
        print(f"📅 Time range:{date_str}")
    elif start_date:
        time_filter = convert_time_filter(start_date, datetime.now())
        print(f"📅 Time range: From {start_date.strftime('%Y-%m-%d')} ({time_filter})")
    else:
         print(f"📅 Time range: Past {time_filter} (default)")


    posts = []
    subreddits = [ # Your comprehensive list
        "investing", "stocks", "wallstreetbets", "StockMarket", "ValueInvesting",
        "options", "algotrading", "SecurityAnalysis", "InvestmentEducation","CreditCardsIndia",
        "dividends", "Daytrading", "StockMarket", "pennystocks", "investing_discussion",
        "IndiaInvestments", "IndianStreetBets", "IndiaFinance", "IndianStockMarket", "CREDclub",
        "DalalStreetTalks", "fiindia", "indianbusinessowners",
        "economy", "Economics", "finance", "FinancialIndependence", "Banking",
        "GlobalMarkets", "econmonitor", "IndianEconomy", "supplychain",
        "Bitcoin", "cryptocurrency", "CryptoMarkets", "ethtrader", "CryptoCurrencyTrading",
        "CryptoTechnology", "altcoin", "defi", "NFT", "IndianCryptoMarkets",
        "tech", "technology", "business", "realestateinvesting", "Energy",
        "startups", "healthcare", "retailinvesting", "AutoIndustry", "renewableenergy",
        "worldnews", "news", "india", "dataisbeautiful", "AskEconomics"
    ]
    finance_terms = ['market', 'stock', 'invest', 'price', 'share', 'trading', # Your terms list
                     'finance', 'dividend', 'bull', 'bear', 'crypto', 'quarter',
                     'earnings', 'portfolio', 'economy', 'fiscal', 'trend', 'growth',
                     'profit', 'loss', 'debt', 'revenue', 'valuation', 'forecast',
                     'analysis', 'sector', 'fund', 'etf', 'index', 'inflation']

    subreddit_count = Counter()
    total_processed = 0
    post_dates = []

    try:
        for sub in subreddits:
            print(f"📬 Searching r/{sub}...")
            processed_in_sub = 0
            try:
                # Use relevance sort + time filter
                search_results = reddit.subreddit(sub).search(
                    f'"{keyword}"', sort='relevance', time_filter=time_filter, limit=limit
                )

                for submission in search_results:
                    total_processed += 1
                    post_date = datetime.fromtimestamp(submission.created_utc)

                    # Server-side filtering helped, but double-check the date range here
                    if start_date and post_date < start_date: continue
                    if end_date and post_date > (end_date + timedelta(days=1)): continue # Include the end date itself

                    post_dates.append(post_date)
                    if submission.score < min_score: continue

                    title = submission.title
                    selftext = submission.selftext if hasattr(submission, 'selftext') else ""
                    # Ensure text fields are strings before lowercasing
                    safe_title = title if isinstance(title, str) else ""
                    safe_selftext = selftext if isinstance(selftext, str) else ""
                    full_content_lower = (safe_title + " " + safe_selftext).lower()

                    # More robust keyword check needed after using quotes in search
                    # Simple check first
                    if keyword.lower() not in full_content_lower:
                         # If not found directly, check if parts of keyword match (for multi-word keywords)
                         kw_parts = keyword.lower().split()
                         if not all(part in full_content_lower for part in kw_parts):
                             continue


                    primary_finance_subs = ["investing", "stocks", "wallstreetbets", "IndiaInvestments",
                                           "cryptocurrency", "economy", "finance"]
                    if sub not in primary_finance_subs:
                         has_finance_term = any(term in full_content_lower for term in finance_terms)
                         if not has_finance_term: continue

                    comments = []
                    try: # Fetching comments can fail
                        submission.comments.replace_more(limit=0) # Don't load MoreComments objects
                        for comment in submission.comments[:3]:
                            if comment.score > 1 and isinstance(comment.body, str):
                                comments.append(comment.body[:200]) # Limit comment length
                    except Exception as comment_err:
                         print(f"   Warning: Could not fetch comments for post ID {submission.id}: {comment_err}")


                    # Combine text for sentiment calculation
                    comment_text = " ".join(comments)
                    sentiment_content = f"{title}. {selftext[:500]} {comment_text}" # Limit selftext length for analysis

                    # Calculate sentiment using your enhanced function
                    weighted_sentiment = analyze_sentiment(sentiment_content)

                    post_data = {
                        "title": title,
                        "content_preview": selftext[:300] + "..." if len(selftext) > 300 else selftext,
                        "subreddit": sub,
                        "sentiment": round(weighted_sentiment, 3), # More precision
                        "score": submission.score,
                        "num_comments": submission.num_comments, # More direct attribute
                        "url": submission.url,
                        "date": post_date.strftime('%Y-%m-%d'),
                        "engagement": submission.score + (submission.num_comments * 2),
                        "flair": submission.link_flair_text if hasattr(submission, 'link_flair_text') else None,
                        "full_text_for_llm": f"Title: {title}\nSubreddit: r/{sub}\nDate: {post_date.strftime('%Y-%m-%d')}\nScore: {submission.score}\nComments: {submission.num_comments}\nSentiment: {weighted_sentiment:.2f}\nPreview: {selftext[:500]}..." # Create combined text here
                    }
                    posts.append(post_data)
                    subreddit_count[sub] += 1
                    processed_in_sub +=1

                if processed_in_sub > 0:
                    print(f"   Found {processed_in_sub} relevant posts in r/{sub}.")
                time.sleep(0.1) # Avoid hitting rate limits

            except praw.exceptions.PRAWException as praw_e:
                print(f"   PRAW Error in r/{sub}: {praw_e}")
            except Exception as e:
                print(f"   Error searching r/{sub}: {e}")
                continue

    except Exception as e:
        print(f"🛑 Major Error fetching Reddit posts: {e}")

    # Sort posts before returning - perhaps by date or engagement?
    posts.sort(key=lambda x: x["date"], reverse=True) # Sort newest first for LLM context

    print(f"\n✅ Processed ~{total_processed} posts. Found {len(posts)} relevant results.")

    if post_dates:
        earliest = min(post_dates).strftime('%Y-%m-%d')
        latest = max(post_dates).strftime('%Y-%m-%d')
        print(f"📅 Posts actual date range found: {earliest} to {latest}")
    if posts:
      print(f"🏆 Most active subreddits: {', '.join([f'r/{sub} ({count})' for sub, count in subreddit_count.most_common(5)])}")

    return posts # Return the list of dictionaries


# --- LLM Interaction ---
def get_llm_summary(prompt_text, model=llm_model):
    """Sends text to the LLM and returns the generated summary."""
    print("\n🤖 Asking LLM to analyze and summarize...")
    try:
        # Configure safety settings if needed (e.g., block harmful content)
        safety_settings = [
            { "category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE" },
            { "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE" },
            { "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE" },
            { "category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]
        response = model.generate_content(prompt_text, safety_settings=safety_settings)
        # More robust check for response content
        if response.parts:
             return response.text.strip()
        else:
            print(f"⚠️ WARNING: LLM returned no content. Safety Feedback: {response.prompt_feedback}")
            # Try to find candidate if available
            if response.candidates and response.candidates[0].content.parts:
                 print("   Extracting text from candidate.")
                 return response.candidates[0].content.parts[0].text.strip()
            return "LLM generation failed or content was blocked due to safety settings."

    except Exception as e:
        print(f"🛑 ERROR: LLM generation failed: {e}")
        # Try to access potential detailed error info if available
        error_details = getattr(e, 'response', None) or getattr(e, 'message', str(e))
        print(f"   Error Details: {error_details}")
        return f"Error during LLM summarization: {e}"

# --- Format data for LLM ---
def format_posts_for_llm(posts, max_posts=50, max_len_per_post=1000):
     """ Formats the list of post dictionaries into a single text block for the LLM. """
     print(f"📝 Formatting {min(len(posts), max_posts)} most recent posts for LLM...")
     formatted_texts = []
     # Use the most recent 'max_posts' (already sorted by date desc)
     for post in posts[:max_posts]:
          # Use the pre-formatted text from the dictionary
          post_text = post.get("full_text_for_llm", "")
          # Truncate if excessively long (double check)
          formatted_texts.append(post_text[:max_len_per_post])

     if not formatted_texts:
          return ""

     # Join with clear separators
     return "\n\n---\n[POST END]\n---\n\n".join(formatted_texts)


# ----------- LLM-POWERED SUMMARY WORKFLOW -----------
def get_llm_market_insights(query, start_date=None, end_date=None):
    """ Fetches Reddit data and uses LLM to generate insights. """
    print(f"\n🚀 Initiating LLM-Powered Insight Generation for: '{query}'")

    # 1. Parse Dates
    start_date_obj = parse_date(start_date) if start_date else None
    # Default end_date to today if start_date is given but end_date isn't
    if start_date_obj and not end_date:
        end_date_obj = datetime.now()
    else:
        end_date_obj = parse_date(end_date) if end_date else None


    # Construct date range string for prompt
    date_prompt_str = "over the default period (likely past month)"
    if start_date_obj and end_date_obj:
        date_prompt_str = f"between {start_date_obj.strftime('%Y-%m-%d')} and {end_date_obj.strftime('%Y-%m-%d')}"
    elif start_date_obj:
         date_prompt_str = f"since {start_date_obj.strftime('%Y-%m-%d')}"
    elif end_date_obj:
         date_prompt_str = f"up to {end_date_obj.strftime('%Y-%m-%d')}"


    # 2. Fetch Reddit Data
    # Fetch more posts initially to give LLM a better sample, maybe filter later if needed
    reddit_posts = fetch_reddit(query, start_date_obj, end_date_obj, limit=30, min_score=1)

    if not reddit_posts:
        print("\n❌ No relevant Reddit posts found for the specified query and period.")
        return # Exit if no data

    # 3. Format Data for LLM
    # Limit to a reasonable number of recent posts to fit context window & keep focus
    formatted_data = format_posts_for_llm(reddit_posts, max_posts=50)

    if not formatted_data:
        print("\n❌ Failed to format any post data for the LLM.")
        return

    # Calculate average sentiment from fetched data (can add to prompt context)
    sentiments = [p['sentiment'] for p in reddit_posts if 'sentiment' in p]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0


    # 4. Construct LLM Prompt
    prompt = f"""
    You are a financial analyst AI specializing in interpreting online discussions.
    Analyze the following collection of Reddit post snippets related to "{query}" gathered {date_prompt_str}.
    The snippets include title, subreddit, date, score, comment count, a preview of the content, and a pre-calculated sentiment score (-1: very negative, 1: very positive).

    Based *only* on the information present in these snippets:

    1.  **Overall Sentiment:** What is the dominant sentiment (Positive, Negative, Mixed/Neutral) regarding "{query}" in these discussions? Briefly explain why. Reference the calculated average sentiment of {avg_sentiment:.2f} if it aligns or contrasts with your assessment of the text.
    2.  **Key Themes & Topics:** What are the 2-3 most frequently discussed themes, concerns, or news items related to "{query}" mentioned in these posts?
    3.  **Community Focus:** Are discussions concentrated in specific types of subreddits (e.g., general investing, speculative trading, crypto, specific industries)? Mention 1-2 prominent ones if identifiable.
    4.  **Notable Contrasts:** Are there any significant disagreements, contrasting viewpoints or recurring debates visible in the snippets?
    5.  **Emerging Trends (Optional):** If identifiable from the text snippets, mention any very recent shifts in discussion or sentiment (e.g., a sudden increase in posts about a specific event).

    Provide your analysis as a concise summary (approx. 3-5 paragraphs). Focus solely on the provided text snippets. Do not add external information or opinions. Be factual and objective based *only* on the data below.

    --- BEGIN REDDIT POST SNIPPETS ---
    {formatted_data}
    --- END REDDIT POST SNIPPETS ---

    Reddit Discussion Analysis for "{query}":
    """

    # 5. Get LLM Summary
    llm_summary = get_llm_summary(prompt)

    # 6. Print Result
    print("\n" + "="*25 + f" L L M  I N S I G H T S : '{query}' " + "="*25)
    print(f"(Based on {len(reddit_posts)} fetched Reddit posts, {date_prompt_str})\n")
    # Use textwrap for better readability of potentially long LLM output
    print(textwrap.fill(llm_summary, width=80)) # Adjust width as needed
    print("-" * (60 + len(query)))


# ----------- MAIN EXECUTION -----------
if __name__ == '__main__':
    print("🚀 LLM-Powered Market Sentiment Analyzer (Reddit Focus) 🚀")
    print("----------------------------------------------------------")

    user_query = ""
    while not user_query: # Loop until a query is entered
        user_query = input("Enter market topic/stock ticker/keyword to research: ").strip()
        if not user_query:
            print("Please enter a topic.")

    # Optional date filtering
    start_date_str = None
    end_date_str = None
    use_dates = input("Filter by date range? (y/n, default n): ").lower()
    if use_dates == 'y':
        start_date_str = input("Enter start date (e.g., YYYY-MM-DD, leave blank for none): ").strip() or None
        end_date_str = input("Enter end date (e.g., YYYY-MM-DD, leave blank for today): ").strip() or None
        if end_date_str == "": # Handle blank input for end date meaning today
            end_date_str = datetime.now().strftime('%Y-%m-%d')


    # --- Run the analysis ---
    get_llm_market_insights(user_query, start_date_str, end_date_str)


    print("\nBot finished analysis.")
    # --- Disclaimer ---
    print("\n*** DISCLAIMER ***")
    print("This bot provides AI-generated summaries based on public Reddit data.")
    print("This is NOT financial advice. Information may be incomplete, inaccurate, or biased.")
    print("Always perform your own comprehensive research (DYOR) before making any financial decisions.")