import os
import tweepy
import time
import random
import schedule
import logging
import json
import argparse
import requests
from datetime import datetime, date
from dotenv import load_dotenv

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# from google.generativeai.errors import APIError # Using standard Exception for now due to import error

# --- Configuration & Initialization ---
load_dotenv()

# Twitter Credentials
TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")

# Gemini Credentials
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Perplexity Credentials
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# --- Global Clients ---
SEARCH_QUERIES = [
    "blockchain development",
    "crypto research",
    "cryptography news",
    "web3 innovation",
    "zero-knowledge proof",
    "decentralized identity",
    "smart contract audit"
]
TWITTER_API = None
TWITTER_CLIENT = None
SCHEDULE_FILE = "schedule.json"

# --- Twitter API Functions ---

def authenticate_twitter():
    """Authenticates with the Twitter API v1.1 and v2."""
    global TWITTER_API, TWITTER_CLIENT
    
    # For OAuth 1.0a (standard method for posting)
    if not all([TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        logging.error("Error: Twitter API credentials are not fully set in the .env file.")
        return False

    try:
        # Authenticate for API v1.1 (required for search/data gathering)
        auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
        TWITTER_API = tweepy.API(auth, wait_on_rate_limit=True)

        # Authenticate for API v2 (required for posting tweets)
        TWITTER_CLIENT = tweepy.Client(
            consumer_key=TWITTER_CONSUMER_KEY,
            consumer_secret=TWITTER_CONSUMER_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
            bearer_token=TWITTER_BEARER_TOKEN
        )
        
        logging.info("Twitter API authentication successful.")
        return True
    except Exception as e:
        logging.error(f"Twitter API Authentication Error: {e}")
        return False

def post_tweet(text: str):
    """Posts a tweet using the authenticated Twitter client."""
    if TWITTER_CLIENT is None:
        logging.error("Cannot post tweet: Twitter client is not authenticated.")
        return False
    
    try:
        response = TWITTER_CLIENT.create_tweet(text=text)
        tweet_id = response.data['id']
        logging.info(f"Successfully posted tweet! ID: {tweet_id}")
        logging.debug(f"Posted Text: {text}") # Use debug for the full text to keep info clean
        return True
    except Exception as e:
        logging.error(f"Error posting tweet: {e}")
        return False


# --- Gemini API Functions ---

def generate_post_with_ai(content_snippets: list) -> str:
    """
    Generates a human-like, SEO-optimized X post based on curated content.
    Uses the gemini-2.0-pro model as requested by the user for high quality.
    """
    # The client is configured globally, so we only need to check the API key
    if not GEMINI_API_KEY:
        logging.error("Gemini API key not configured for post generation.")
        return ""
    
    # Combine content snippets into a single string for the prompt
    input_content = "\n---\n".join(content_snippets)
    
    # Enhanced prompt for high-quality, human-like, SEO-optimized post based on Perplexity trends
    prompt = f"""
    You are a renowned Blockchain Developer, Researcher, and Cryptographer with 10+ years of experience. Your posts consistently go viral and establish thought leadership in the crypto space.
    
    **Mission:** Transform the latest trend research into a compelling X post that feels authentically human, drives massive engagement, and positions you as an industry authority.
    
    **Voice & Tone Guidelines:**
    - Write like a seasoned expert sharing genuine insights from fresh research, not recycled content
    - Use conversational yet authoritative language that shows deep understanding
    - Include subtle technical depth that showcases expertise without alienating newcomers
    - Vary between analytical, excited, cautionary, or forward-thinking tones based on the trend
    - Add personality through strategic use of emojis (1-2 max, contextually relevant)
    - Show genuine curiosity and passion for the technology
    
    **Trend-Based Content Strategy:**
    - Lead with the most compelling/surprising element from the research
    - Connect breaking news to broader implications for the industry
    - Add your expert perspective or prediction based on the trend data
    - Use specific numbers, percentages, or timeframes from the research when available
    - Create urgency around time-sensitive developments
    - Position emerging trends within historical context
    
    **Engagement Optimization:**
    - Start with a hook: bold statement, intriguing question, or surprising insight from the trends
    - Use power words: "breakthrough," "revolutionary," "critical," "emerging," "game-changing," "unprecedented"
    - Include actionable insights or bold predictions based on the trend analysis
    - Create FOMO around emerging opportunities or warn about potential risks
    - End with a thought-provoking question that invites expert discussion
    
    **Technical Requirements:**
    1. Maximum 280 characters (including hashtags, spaces, and emojis)
    2. Include 3-4 strategic hashtags that maximize discoverability for the specific trends
    3. Naturally integrate trending keywords and topics from the research
    4. Avoid generic phrases like "exciting news," "check this out," or "thoughts?"
    5. No introductory text - deliver the post content only
    6. Do not include any prefixes like "Improved post:" or "Here's the post:"
    
    **Research-Driven Approach:**
    - Synthesize multiple trend insights into one cohesive narrative
    - Highlight the most newsworthy or surprising elements
    - Connect dots between different developments mentioned in the research
    - Use the freshness of the information as a competitive advantage
    - Reference specific developments, partnerships, or breakthroughs mentioned
    
    **Latest Trend Research:**
    ---
    {input_content}
    ---
    
    Generate ONLY the final X post that leverages these fresh trends to maximize engagement and establish thought leadership. Return the tweet text directly without any prefixes or explanations.
    """
    
    try:
        # Prepare the request payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        # Set up headers
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': GEMINI_API_KEY
        }
        
        # Make the HTTP request
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
            
            # Clean up any unwanted prefixes or formatting
            cleaned_text = generated_text.strip()
            
            # Remove common prefixes that AI might add
            prefixes_to_remove = [
                "Improved post:",
                "Here's the post:",
                "Tweet:",
                "Post:",
                "Here's a tweet:",
                "Here's an improved version:",
                "Revised post:",
                "Updated post:"
            ]
            
            for prefix in prefixes_to_remove:
                if cleaned_text.startswith(prefix):
                    cleaned_text = cleaned_text[len(prefix):].strip()
            
            # Remove quotes if the entire text is wrapped in them
            if cleaned_text.startswith('"') and cleaned_text.endswith('"'):
                cleaned_text = cleaned_text[1:-1].strip()
            
            logging.info("AI Post Generated.")
            return cleaned_text
        else:
            logging.error(f"Gemini API Error: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        logging.error(f"Gemini API Generation Error: {e}")
        return ""

def review_post_with_ai(post_text):
    """Reviews and potentially improves a post using Gemini AI with advanced optimization strategies."""
    try:
        review_prompt = f"""
        You are an expert social media strategist and viral content creator specializing in crypto/blockchain content. Your mission is to optimize this X post for maximum engagement and virality.

        **Current Post:** "{post_text}"

        **Optimization Framework:**
        
        **1. ENGAGEMENT ANALYSIS:**
        - Does it have a strong hook in the first 10 words?
        - Is there emotional resonance (excitement, curiosity, urgency, FOMO)?
        - Does it invite interaction (questions, debates, shares)?
        - Are there specific, compelling details vs. generic statements?

        **2. VIRAL POTENTIAL CHECKLIST:**
        - Newsworthy/timely information ✓
        - Surprising or counterintuitive insights ✓
        - Expert credibility signals ✓
        - Community-relevant hashtags ✓
        - Clear value proposition ✓

        **3. TECHNICAL OPTIMIZATION:**
        - Character count under 280 (including spaces, hashtags, emojis)
        - Strategic hashtag placement (3-4 max, highly relevant)
        - Emoji usage (1-2 max, contextually perfect)
        - Readability and flow optimization

        **4. CONTENT ENHANCEMENT STRATEGIES:**
        - Add specific numbers, percentages, or timeframes if missing
        - Include power words: "breakthrough," "unprecedented," "critical," "emerging"
        - Create urgency or scarcity when appropriate
        - End with engaging questions or bold predictions
        - Reference credible sources or recent developments

        **5. AUDIENCE TARGETING:**
        - Appeals to both crypto veterans and newcomers
        - Uses industry terminology appropriately
        - Connects to broader market implications
        - Encourages expert discussion

        **Instructions:**
        - If the post is already optimized for virality, return it unchanged
        - If improvements are needed, return the enhanced version
        - Focus on making it more engaging, specific, and shareable
        - Maintain the core message while amplifying its impact
        - Return ONLY the final tweet text without any prefixes, explanations, or quotes around the entire post
        """
        
        # Prepare the request payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": review_prompt
                        }
                    ]
                }
            ]
        }
        
        # Set up headers
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': GEMINI_API_KEY
        }
        
        # Make the HTTP request
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
            
            # Clean up any unwanted prefixes or formatting
            cleaned_text = generated_text.strip()
            
            # Remove common prefixes that AI might add
            prefixes_to_remove = [
                "Improved post:",
                "Here's the post:",
                "Tweet:",
                "Post:",
                "Here's a tweet:",
                "Here's an improved version:",
                "Revised post:",
                "Updated post:",
                "Here's the improved post:",
                "Final post:",
                "Optimized post:",
                "Enhanced version:",
                "Better version:"
            ]
            
            for prefix in prefixes_to_remove:
                if cleaned_text.startswith(prefix):
                    cleaned_text = cleaned_text[len(prefix):].strip()
            
            # Remove quotes if the entire text is wrapped in them
            if cleaned_text.startswith('"') and cleaned_text.endswith('"'):
                cleaned_text = cleaned_text[1:-1].strip()
            
            logging.info("AI Post Reviewed and Optimized.")
            return cleaned_text
        else:
            logging.error(f"Gemini API Review Error: {response.status_code} - {response.text}")
            return post_text
            
    except Exception as e:
        logging.error(f"Gemini API Review Error: {e}")
        return post_text


# --- Data Curation Functions ---

def get_trending_content():
    """
    Uses Perplexity AI to research current trends in blockchain, crypto, and web3.
    Returns a list of relevant content snippets based on real-time information.
    """
    if not PERPLEXITY_API_KEY:
        logging.error("Perplexity API key not configured for trend research.")
        return []

    try:
        # Select a random query to research
        query = random.choice(SEARCH_QUERIES)
        logging.info(f"Researching trends with query: '{query}'")

        # Create a comprehensive research prompt for Perplexity
        research_prompt = f"""
        Research the most engaging and viral trends related to '{query}' from the past 24-48 hours that would make excellent social media content.

        Focus on finding:
        1. BREAKING NEWS: Major announcements, partnerships, or launches
        2. VIRAL MOMENTS: Trending topics, memes, or community discussions
        3. MARKET CATALYSTS: Price movements, adoption milestones, or institutional moves
        4. TECHNICAL BREAKTHROUGHS: New protocols, upgrades, or innovations
        5. REGULATORY DEVELOPMENTS: Policy changes, legal decisions, or government actions
        6. COMMUNITY BUZZ: Popular debates, predictions, or expert takes
        7. EDUCATIONAL OPPORTUNITIES: Complex topics that need simple explanations

        For each trend, provide:
        - The core story/development
        - Why it matters to the crypto community
        - What makes it shareable/engaging
        - Any relevant data points or quotes

        Return 4-6 distinct trends that would generate high engagement on social media.
        Prioritize trends that are:
        - Timely and newsworthy
        - Emotionally engaging (exciting, surprising, or thought-provoking)
        - Relevant to both beginners and experts
        - Backed by credible sources
        """

        # Prepare the request payload for Perplexity API
        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": """You are an expert crypto/blockchain trend researcher and social media strategist. Your mission is to identify the most engaging, shareable, and timely content opportunities in the crypto space.

Key principles:
- Prioritize RECENCY: Focus on developments from the last 24-48 hours
- Seek ENGAGEMENT: Look for stories that spark discussion, debate, or excitement
- Ensure ACCURACY: Only report verified information from credible sources
- Think VIRAL: Consider what would make people want to share, comment, or react
- Balance ACCESSIBILITY: Include both technical developments and broader market stories
- Identify EMOTIONS: Look for stories that evoke curiosity, excitement, concern, or hope

You have access to real-time information. Use it to find the freshest, most compelling stories that crypto Twitter would be talking about right now."""
                },
                {
                    "role": "user", 
                    "content": research_prompt
                }
            ],
            "max_tokens": 1500,
             "temperature": 0.3,
             "top_p": 0.9,
             "return_citations": True,
             "search_domain_filter": [],
             "return_images": False,
             "return_related_questions": True,
             "search_recency_filter": "day",
             "top_k": 0,
             "stream": False,
             "frequency_penalty": 0.8
        }

        # Set up headers
        headers = {
            'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
            'Content-Type': 'application/json'
        }

        # Make the HTTP request
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Split the content into individual insights
            insights = [insight.strip() for insight in content.split('\n') if insight.strip() and len(insight.strip()) > 20]
            
            # Format as content snippets
            content_snippets = []
            for i, insight in enumerate(insights[:5], 1):  # Limit to 5 insights
                snippet = f"Trend Insight {i}: {insight}"
                content_snippets.append(snippet)
            
            logging.info(f"Found {len(content_snippets)} trend insights from Perplexity.")
            return content_snippets
        else:
            logging.error(f"Perplexity API Error: {response.status_code} - {response.text}")
            return []

    except Exception as e:
        logging.error(f"Error during Perplexity trend research: {e}")
        return []


def initialize_gemini():
    """Initializes the Gemini API client."""
    if not GEMINI_API_KEY:
        logging.error("Error: GEMINI_API_KEY is not set in the .env file.")
        return False
    
    logging.info("Gemini API client initialized successfully.")
    return True

# --- Main Execution ---

# --- Scheduling Logic ---

def load_schedule():
    """
    Loads the schedule from schedule.json file.
    Returns the schedule data or creates a new one if file doesn't exist.
    """
    try:
        if os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, 'r') as f:
                schedule_data = json.load(f)
                logging.info("Loaded existing schedule from schedule.json")
                return schedule_data
        else:
            logging.info("No existing schedule found, creating new one")
            return create_new_schedule()
    except Exception as e:
        logging.error(f"Error loading schedule: {e}")
        return create_new_schedule()

def save_schedule(schedule_data):
    """
    Saves the schedule data to schedule.json file.
    """
    try:
        with open(SCHEDULE_FILE, 'w') as f:
            json.dump(schedule_data, f, indent=2)
        logging.info("Schedule saved to schedule.json")
    except Exception as e:
        logging.error(f"Error saving schedule: {e}")

def create_new_schedule():
    """
    Creates a new schedule for today with random post times.
    """
    today = date.today().isoformat()
    
    # Posting window in minutes from midnight (9:00 = 540, 21:00 = 1260)
    START_MIN = 540 
    END_MIN = 1260
    
    # Calculate 5 random times within the window
    random_minutes = sorted(random.sample(range(START_MIN, END_MIN), 5))
    
    post_times = []
    for minutes in random_minutes:
        hour = minutes // 60
        minute = minutes % 60
        time_str = f"{hour:02d}:{minute:02d}"
        post_times.append({
            "time": time_str,
            "completed": False,
            "scheduled_at": datetime.now().isoformat()
        })
    
    schedule_data = {
        "date": today,
        "posts": post_times,
        "posts_completed": 0,
        "max_posts_per_day": 5
    }
    
    save_schedule(schedule_data)
    return schedule_data

def update_schedule_after_post(post_time):
    """
    Updates the schedule after a successful post.
    """
    schedule_data = load_schedule()
    
    # Mark the specific post as completed
    for post in schedule_data["posts"]:
        if post["time"] == post_time and not post["completed"]:
            post["completed"] = True
            post["completed_at"] = datetime.now().isoformat()
            schedule_data["posts_completed"] += 1
            break
    
    save_schedule(schedule_data)
    logging.info(f"Updated schedule: Post at {post_time} marked as completed")

def is_new_day(schedule_data):
    """
    Checks if it's a new day compared to the schedule date.
    """
    today = date.today().isoformat()
    return schedule_data.get("date") != today

def schedule_posts_smart():
    """
    Smart scheduler that checks existing schedule and updates for new days.
    """
    schedule_data = load_schedule()
    
    # Check if it's a new day
    if is_new_day(schedule_data):
        logging.info("New day detected, creating fresh schedule")
        schedule_data = create_new_schedule()
    
    # Clear any existing scheduled jobs
    schedule.clear()
    
    # Schedule remaining posts for today
    remaining_posts = [post for post in schedule_data["posts"] if not post["completed"]]
    
    if not remaining_posts:
        logging.info("All posts for today have been completed")
        return
    
    logging.info(f"Scheduling {len(remaining_posts)} remaining posts for today:")
    
    for post in remaining_posts:
        time_str = post["time"]
        
        # Create a closure to capture the current time_str
        def create_post_job(post_time):
            def job():
                create_and_post()
                update_schedule_after_post(post_time)
            return job
        
        # Schedule the job
        schedule.every().day.at(time_str).do(create_post_job(time_str))
        logging.info(f"Scheduled post at: {time_str} UTC")

def schedule_posts():
    """
    Legacy function for backward compatibility.
    Now redirects to smart scheduler.
    """
    schedule_posts_smart()

# --- Main Posting Logic ---

def create_and_post():
    """Main function to perform the content curation, generation, review, and posting cycle."""
    logging.info("--- Starting Post Generation Cycle ---")
    
    # 1. Data Curation
    content_snippets = get_trending_content()
    if not content_snippets:
        logging.warning("No content found. Skipping post cycle.")
        return False
    
    # 2. AI Generation
    raw_post = generate_post_with_ai(content_snippets)
    if not raw_post:
        logging.error("AI failed to generate a post. Skipping post cycle.")
        return False
    logging.debug(f"Raw Generated Post:\n{raw_post}")
    
    # 3. AI Review
    final_post = review_post_with_ai(raw_post)
    if not final_post:
        logging.error("AI review failed. Skipping post cycle.")
        return False
    logging.info(f"Final Approved Post: {final_post}")
    
    # 4. Posting
    success = post_tweet(final_post)
    logging.info(f"Posting Status: {'SUCCESS' if success else 'FAILURE'}")
    
    return success


# --- Main Execution ---

def initialize_clients():
    """Initializes all required API clients."""
    logging.info("--- Initializing API Clients ---")
    
    twitter_ok = authenticate_twitter()
    gemini_ok = initialize_gemini()
    
    if not twitter_ok or not gemini_ok:
        logging.critical("One or more API clients failed to initialize. Please check your credentials.")
        return False
    
    logging.info("All clients initialized successfully.")
    return True

def post_now_mode():
    """
    Immediate posting mode - generates, reviews, and posts a single tweet then exits.
    """
    logging.info("Running in immediate post mode...")
    
    try:
        # Get trending content
        logging.info("Fetching trending content...")
        content_snippets = get_trending_content()
        
        if not content_snippets:
            logging.warning("No trending content found. Generating post with general topics.")
            content_snippets = ["Latest developments in blockchain and crypto technology"]
        
        # Generate post
        logging.info("Generating post with AI...")
        post_text = generate_post_with_ai(content_snippets)
        
        if not post_text:
            logging.error("Failed to generate post content")
            return False
        
        # Review post
        logging.info("Reviewing post with AI...")
        reviewed_post = review_post_with_ai(post_text)
        
        if not reviewed_post:
            logging.warning("Post review failed, using original post")
            reviewed_post = post_text
        
        # Post to Twitter
        logging.info("Posting to Twitter...")
        success = post_tweet(reviewed_post)
        
        if success:
            logging.info("Post successfully published!")
            logging.info(f"Posted content: {reviewed_post}")
            return True
        else:
            logging.error("Failed to post to Twitter")
            return False
            
    except Exception as e:
        logging.error(f"Error in post_now_mode: {e}")
        return False

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='X Auto Poster - Automated Twitter posting tool')
    parser.add_argument('--post-now', action='store_true', 
                       help='Generate and post immediately, then exit (no scheduling)')
    return parser.parse_args()

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    if initialize_clients():
        if args.post_now:
            # Immediate posting mode
            logging.info("Starting immediate post mode...")
            success = post_now_mode()
            if success:
                logging.info("Immediate post completed successfully!")
            else:
                logging.error("Immediate post failed!")
            logging.info("Exiting...")
        else:
            # Normal scheduled mode
            logging.info("Starting scheduled mode...")
            schedule_posts_smart()
            
            logging.info("Scheduler started. The tool will now run indefinitely, posting daily.")
            logging.info("Press Ctrl+C to stop the process.")
            
            # Main loop to keep the script running and check for scheduled jobs
            try:
                while True:
                    schedule.run_pending()
                    time.sleep(1)
            except KeyboardInterrupt:
                logging.info("Scheduler stopped by user.")
            
    else:
        logging.critical("Tool failed to initialize. Please check the .env file and your network connection.")
    logging.info("---------------------------------------------")
