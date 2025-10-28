import os
import tweepy
import time
import random
import schedule
import logging
import json
import argparse
import requests
from datetime import datetime, date, timezone, timedelta
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
    # Crypto Development & Technical
    "blockchain development breakthroughs",
    "smart contract innovations and audits", 
    "Layer 2 scaling solutions updates",
    "zero-knowledge proof implementations",
    "cryptography security developments",
    "web3 development frameworks",
    "decentralized identity solutions",
    "cross-chain interoperability protocols",
    
    # Crypto News & Market
    "crypto market analysis and trends",
    "cryptocurrency regulatory updates",
    "institutional crypto adoption news",
    "crypto exchange developments",
    "DeFi protocol launches and updates",
    "NFT marketplace trends and sales",
    "crypto partnership announcements",
    "blockchain gaming and metaverse",
    
    # Influential Personalities & Community
    "Vitalik Buterin latest statements",
    "CZ Binance recent announcements", 
    "crypto Twitter viral discussions",
    "Satoshi Nakamoto references and theories",
    "crypto influencer predictions",
    "blockchain conference highlights",
    "crypto community debates and opinions",
    "developer community discussions",
    
    # Innovation & Trends
    "emerging crypto technologies",
    "blockchain use case innovations",
    "crypto startup funding rounds",
    "web3 social media platforms",
    "decentralized finance innovations",
    "crypto environmental sustainability",
    "quantum computing crypto impact",
    "central bank digital currencies"
]
TWITTER_API = None
TWITTER_CLIENT = None
SCHEDULE_FILE = "schedule.json"

# Global variable to track recent queries for diversity
RECENT_QUERIES = []
MAX_RECENT_QUERIES = 10

# Post Templates for Diverse Content Generation
POST_TEMPLATES = {
    "breaking_news": {
        "style": "urgent, attention-grabbing",
        "structure": "🚨 BREAKING: [headline] [impact/implication] [call_to_action] #hashtags",
        "tone": "excited, urgent",
        "examples": ["🚨 BREAKING:", "JUST IN:", "ALERT:"]
    },
    "technical_analysis": {
        "style": "analytical, expert-level",
        "structure": "[technical_insight] [data/metrics] [expert_opinion] [future_prediction] #hashtags",
        "tone": "analytical, authoritative",
        "examples": ["Deep dive:", "Technical breakdown:", "Analysis:"]
    },
    "personal_insight": {
        "style": "conversational, thought-provoking",
        "structure": "[personal_observation] [reasoning] [broader_implication] [question] #hashtags",
        "tone": "thoughtful, conversational",
        "examples": ["Been thinking about", "My take on", "Interesting observation:"]
    },
    "educational": {
        "style": "informative, accessible",
        "structure": "[concept_explanation] [why_it_matters] [practical_application] [learn_more] #hashtags",
        "tone": "educational, helpful",
        "examples": ["Quick explainer:", "For those wondering:", "Let me break this down:"]
    },
    "prediction": {
        "style": "forward-looking, bold",
        "structure": "[prediction] [reasoning] [timeline] [implications] #hashtags",
        "tone": "confident, visionary",
        "examples": ["Prediction:", "Mark my words:", "Calling it now:"]
    },
    "github_showcase": {
        "style": "proud, technical",
        "structure": "[project_highlight] [technical_details] [use_case] [github_link] #hashtags",
        "tone": "proud, technical",
        "examples": ["Just shipped:", "Working on:", "New project:"]
    },
    "market_commentary": {
        "style": "observational, market-focused",
        "structure": "[market_observation] [data_point] [analysis] [outlook] #hashtags",
        "tone": "observational, analytical",
        "examples": ["Market watch:", "Interesting trend:", "Data shows:"]
    },
    "community_engagement": {
        "style": "interactive, community-focused",
        "structure": "[topic_introduction] [community_question] [encourage_discussion] #hashtags",
        "tone": "engaging, inclusive",
        "examples": ["Community question:", "What do you think?", "Let's discuss:"]
    }
}

# Personality Modes for Human-like Variation
PERSONALITY_MODES = {
    "excited_builder": {
        "characteristics": "enthusiastic, optimistic, builder-focused",
        "language": "energetic, uses emojis, focuses on possibilities",
        "perspective": "sees opportunities, emphasizes innovation"
    },
    "analytical_expert": {
        "characteristics": "data-driven, precise, technical",
        "language": "measured, uses specific metrics, technical terms",
        "perspective": "focuses on facts, trends, and analysis"
    },
    "cautious_realist": {
        "characteristics": "balanced, risk-aware, practical",
        "language": "measured, mentions risks and benefits",
        "perspective": "considers downsides, emphasizes due diligence"
    },
    "community_leader": {
        "characteristics": "inclusive, educational, supportive",
        "language": "welcoming, asks questions, encourages participation",
        "perspective": "focuses on community building and education"
    }
}

# GitHub Integration Variables
GITHUB_USERNAME = "nnlgsakib"
GITHUB_API_URL = "https://api.github.com"

# Post History Tracking
POSTS_FILE = "posts.json"

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
        return None
    
    try:
        response = TWITTER_CLIENT.create_tweet(text=text)
        tweet_id = response.data['id']
        logging.info(f"Successfully posted tweet! ID: {tweet_id}")
        logging.debug(f"Posted Text: {text}") # Use debug for the full text to keep info clean
        return tweet_id
    except Exception as e:
        logging.error(f"Error posting tweet: {e}")
        return None


# --- Gemini API Functions ---

def load_posts_history():
    """
    Loads the post history from posts.json file.
    """
    try:
        if os.path.exists(POSTS_FILE):
            with open(POSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logging.info(f"Loaded {len(data.get('posts', []))} posts from history")
                return data
        else:
            # Create initial structure if file doesn't exist
            initial_data = {
                "posts": [],
                "metadata": {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "total_posts": 0,
                    "version": "1.0"
                },
                "settings": {
                    "max_history_days": 30,
                    "similarity_threshold": 0.7,
                    "min_topic_diversity_hours": 6
                }
            }
            save_posts_history(initial_data)
            return initial_data
    except Exception as e:
        logging.error(f"Error loading posts history: {e}")
        return {"posts": [], "metadata": {"total_posts": 0}, "settings": {}}

def save_posts_history(posts_data):
    """
    Saves the post history to posts.json file.
    """
    try:
        posts_data["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        posts_data["metadata"]["total_posts"] = len(posts_data.get("posts", []))
        
        with open(POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(posts_data, f, indent=2, ensure_ascii=False)
        logging.info(f"Saved posts history with {posts_data['metadata']['total_posts']} posts")
    except Exception as e:
        logging.error(f"Error saving posts history: {e}")

def add_post_to_history(post_content, tweet_id, search_query, template_name, personality_name, trending_topics):
    """
    Adds a new post to the history with all relevant metadata.
    """
    try:
        posts_data = load_posts_history()
        
        new_post = {
            "id": tweet_id,
            "content": post_content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "search_query": search_query,
            "template": template_name,
            "personality": personality_name,
            "trending_topics": trending_topics,
            "character_count": len(post_content),
            "hashtags": [word for word in post_content.split() if word.startswith('#')]
        }
        
        posts_data["posts"].append(new_post)
        
        # Clean old posts (keep only last 30 days by default)
        max_days = posts_data.get("settings", {}).get("max_history_days", 30)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_days)
        
        posts_data["posts"] = [
            post for post in posts_data["posts"]
            if datetime.fromisoformat(post["timestamp"].replace('Z', '+00:00')) > cutoff_date
        ]
        
        save_posts_history(posts_data)
        logging.info(f"Added new post to history: {post_content[:50]}...")
        
    except Exception as e:
        logging.error(f"Error adding post to history: {e}")

def analyze_topic_similarity_with_ai(new_content, recent_posts, similarity_threshold=0.7):
    """
    Uses AI to analyze if the new content is too similar to recent posts.
    Returns True if content is diverse enough, False if too similar.
    """
    if not recent_posts or not GEMINI_API_KEY:
        return True  # Allow posting if no history or no AI available
    
    try:
        # Get recent posts from last 24 hours
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_posts_content = []
        
        for post in recent_posts[-10:]:  # Check last 10 posts max
            post_time = datetime.fromisoformat(post["timestamp"].replace('Z', '+00:00'))
            if post_time > recent_cutoff:
                recent_posts_content.append({
                    "content": post["content"],
                    "topics": post.get("trending_topics", []),
                    "template": post.get("template", "unknown"),
                    "hours_ago": (datetime.now(timezone.utc) - post_time).total_seconds() / 3600
                })
        
        if not recent_posts_content:
            return True  # No recent posts to compare
        
        recent_posts_text = "\n".join([
            f"- {post['content']} (Template: {post['template']}, {post['hours_ago']:.1f}h ago)"
            for post in recent_posts_content
        ])
        
        prompt = f"""
        You are an expert content analyst. Analyze if the NEW POST is too similar to RECENT POSTS.
        
        **SIMILARITY CRITERIA:**
        - Same main topic/subject (e.g., both about Ethereum, both about DeFi, both about specific coins)
        - Similar angle or perspective on the same news/trend
        - Repetitive themes within 24 hours
        - Same template style covering identical topics
        
        **DIVERSITY CRITERIA (GOOD):**
        - Different blockchain topics (Ethereum vs Bitcoin vs DeFi vs NFTs)
        - Different angles on broad topics (technical vs market vs regulatory)
        - Different template styles (news vs analysis vs personal insight)
        - Time-sensitive updates on evolving stories
        
        **NEW POST TO ANALYZE:**
        {new_content}
        
        **RECENT POSTS (last 24h):**
        {recent_posts_text}
        
        **DECISION REQUIRED:**
        Respond with ONLY one word:
        - "DIVERSE" if the new post covers different topics/angles and adds value
        - "SIMILAR" if the new post is too repetitive or covers the same ground
        
        Consider that crypto moves fast - multiple posts about different aspects of the same major event can be valuable, but avoid repetitive takes on the same specific topic.
        """
        
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
        
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': GEMINI_API_KEY
        }
        
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            ai_decision = result['candidates'][0]['content']['parts'][0]['text'].strip().upper()
            
            is_diverse = "DIVERSE" in ai_decision
            logging.info(f"AI Topic Analysis: {ai_decision} - {'✅ Diverse enough' if is_diverse else '❌ Too similar'}")
            return is_diverse
        else:
            logging.error(f"AI similarity check failed: {response.status_code}")
            return True  # Default to allowing post if AI fails
            
    except Exception as e:
        logging.error(f"Error in AI similarity analysis: {e}")
        return True  # Default to allowing post if error occurs

def get_github_repositories():
    """
    Fetches user's GitHub repositories and returns interesting projects for showcasing.
    """
    try:
        url = f"{GITHUB_API_URL}/users/{GITHUB_USERNAME}/repos"
        params = {
            'sort': 'updated',
            'per_page': 20,
            'type': 'owner'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            repos = response.json()
            
            # Filter for interesting repositories (not forks, has description, recent activity)
            interesting_repos = []
            for repo in repos:
                if (not repo['fork'] and 
                    repo['description'] and 
                    repo['stargazers_count'] >= 0 and  # Include all repos for now
                    repo['language']):  # Has a primary language
                    
                    interesting_repos.append({
                        'name': repo['name'],
                        'description': repo['description'],
                        'language': repo['language'],
                        'stars': repo['stargazers_count'],
                        'url': repo['html_url'],
                        'updated_at': repo['updated_at'],
                        'topics': repo.get('topics', [])
                    })
            
            # Sort by stars and recent activity
            interesting_repos.sort(key=lambda x: (x['stars'], x['updated_at']), reverse=True)
            
            logging.info(f"Found {len(interesting_repos)} interesting GitHub repositories")
            return interesting_repos[:10]  # Return top 10
            
        else:
            logging.error(f"GitHub API Error: {response.status_code}")
            return []
            
    except Exception as e:
        logging.error(f"Error fetching GitHub repositories: {e}")
        return []

def select_post_template_and_personality():
    """
    Randomly selects a post template and personality mode for diverse content generation.
    """
    # Randomly select template and personality
    template_name = random.choice(list(POST_TEMPLATES.keys()))
    personality_name = random.choice(list(PERSONALITY_MODES.keys()))
    
    template = POST_TEMPLATES[template_name]
    personality = PERSONALITY_MODES[personality_name]
    
    logging.info(f"Selected template: {template_name}, personality: {personality_name}")
    
    return template_name, template, personality_name, personality

def generate_multiple_posts_with_ai(content_snippets: list, num_posts: int = 2) -> list:
    """
    Generates multiple human-like, diverse X posts using dynamic templates and personalities.
    Uses the gemini-2.0-pro model with randomized approaches for maximum variety.
    """
    # The client is configured globally, so we only need to check the API key
    if not GEMINI_API_KEY:
        logging.error("Gemini API key not configured for post generation.")
        return []
    
    # Select random template and personality for this generation
    template_name, template, personality_name, personality = select_post_template_and_personality()
    
    # Combine content snippets into a single string for the prompt
    input_content = "\n---\n".join(content_snippets)
    
    # Decide if we should include GitHub showcase (20% chance)
    include_github = random.random() < 0.2 and template_name == "github_showcase"
    github_repos = []
    
    if include_github:
        github_repos = get_github_repositories()
        if github_repos:
            # Add top 3 repos to content for AI to reference
            repo_info = "\n".join([
                f"Repository: {repo['name']} - {repo['description']} ({repo['language']}, {repo['stars']} stars) - {repo['url']}"
                for repo in github_repos[:3]
            ])
            input_content += f"\n\n--- YOUR GITHUB PROJECTS TO SHOWCASE ---\n{repo_info}"
    
    # Create dynamic prompt based on selected template and personality
    prompt = f"""
    You are NLG Sakib (@nlg_sakib_), a renowned Blockchain Developer, Researcher, and Cryptographer with 10+ years of experience. Your posts consistently go viral and establish thought leadership in the crypto space.
    
    **CURRENT POSTING STYLE:** {template_name.upper().replace('_', ' ')}
    **PERSONALITY MODE:** {personality_name.upper().replace('_', ' ')}
    
    **Template Guidelines:**
    - Style: {template['style']}
    - Structure: {template['structure']}
    - Tone: {template['tone']}
    - Example starters: {', '.join(template['examples'])}
    
    **Personality Characteristics:**
    - {personality['characteristics']}
    - Language style: {personality['language']}
    - Perspective: {personality['perspective']}
    
    **Mission:** Create {num_posts} COMPLETELY DIFFERENT posts using the {template_name} template with {personality_name} personality. Each post should feel authentically human and offer unique angles on the trending content.
    
    **CRITICAL DIVERSITY REQUIREMENTS:**
    1. Use DIFFERENT sentence structures for each post
    2. Vary emotional intensity (excited vs calm vs urgent vs thoughtful)
    3. Different hooks: questions, bold statements, predictions, observations
    4. Mix technical depth levels (beginner-friendly vs expert-level)
    5. Vary hashtag strategies and placement
    6. Different call-to-actions or engagement styles
    
    **Content Strategy Based on Template:**
    {f"- GITHUB SHOWCASE: Highlight your development work and technical expertise from your repositories" if include_github else ""}
    - Lead with the most compelling element from the research
    - Connect breaking news to broader industry implications
    - Add your expert perspective based on your {personality_name} personality
    - Use specific data points and metrics when available
    - Create appropriate urgency or curiosity based on the template style
    
    **Human-like Variation Techniques:**
    - Use different sentence lengths (short punchy vs longer explanatory)
    - Vary emoji usage (0-2 per post, contextually relevant)
    - Mix formal and casual language appropriately
    - Include personal opinions and predictions
    - Use different engagement hooks (questions, statements, calls-to-action)
    - Vary technical jargon vs accessible language
    
    **Technical Requirements:**
    1. Maximum 280 characters per post (including hashtags and emojis)
    2. Include 2-4 strategic hashtags relevant to the content and template
    3. Naturally integrate trending keywords from the research
    4. NO generic phrases like "exciting news" or "check this out"
    5. NO prefixes like "Post 1:" - deliver content only
    6. Each post must be COMPLETELY different in structure and approach
    7. NEVER use placeholder links like [hypothetical_repo], [example_link], or [project_name]
    8. Only include REAL, ACTUAL repository links from the provided GitHub data
    9. If no real GitHub repos are provided, do NOT mention any code repositories or links
    10. Focus on the trending content and insights, not placeholder references
    11. ABSOLUTELY FORBIDDEN: Any text in square brackets like [anything] - this will be rejected
    12. If you need to reference code or projects, use descriptive text instead of placeholder links
    
    **Latest Trend Research & Content:**
    ---
    {input_content}
    ---
    
    Generate exactly {num_posts} posts that are DRAMATICALLY different from each other, all following the {template_name} template with {personality_name} personality. Make each post feel like it came from a different moment of inspiration.
    
    Format your response as:
    
    POST_1:
    [First post content]
    
    POST_2:
    [Second post content]
    
    POST_3:
    [Third post content if num_posts > 2]
    
    Return ONLY the posts in this exact format without explanations.
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
            
            # Parse multiple posts from the response
            posts = []
            lines = generated_text.strip().split('\n')
            current_post = ""
            
            for line in lines:
                line = line.strip()
                if line.startswith('POST_'):
                    # If we have a current post, save it
                    if current_post:
                        posts.append(current_post.strip())
                    current_post = ""
                elif line and not line.startswith('POST_'):
                    # Add content to current post
                    if current_post:
                        current_post += " " + line
                    else:
                        current_post = line
            
            # Don't forget the last post
            if current_post:
                posts.append(current_post.strip())
            
            # Clean up each post
            cleaned_posts = []
            for post in posts:
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
                    "[First post content]",
                    "[Second post content]",
                    "[Third post content]"
                ]
                
                cleaned_post = post
                for prefix in prefixes_to_remove:
                    if cleaned_post.startswith(prefix):
                        cleaned_post = cleaned_post[len(prefix):].strip()
                
                # Remove quotes if the entire text is wrapped in them
                if cleaned_post.startswith('"') and cleaned_post.endswith('"'):
                    cleaned_post = cleaned_post[1:-1].strip()
                
                if cleaned_post:  # Only add non-empty posts
                    cleaned_posts.append(cleaned_post)
            
            logging.info(f"Generated {len(cleaned_posts)} posts successfully")
            return cleaned_posts if cleaned_posts else []
        else:
            logging.error(f"Gemini API Error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logging.error(f"Gemini API Generation Error: {e}")
        return []

def select_best_post_with_ai(posts: list) -> str:
    """
    Compares multiple posts and selects the one with the highest viral potential using AI analysis.
    """
    if not posts:
        logging.error("No posts provided for selection")
        return ""
    
    if len(posts) == 1:
        logging.info("Only one post provided, returning it directly")
        return posts[0]
    
    if not GEMINI_API_KEY:
        logging.error("Gemini API key not configured for post selection.")
        return posts[0]  # Return first post as fallback
    
    # Create numbered list of posts for comparison
    posts_text = ""
    for i, post in enumerate(posts, 1):
        posts_text += f"\nPOST {i}:\n{post}\n"
    
    selection_prompt = f"""
    You are an expert social media strategist and viral content analyst specializing in crypto/blockchain content. Your mission is to analyze these X posts and select the ONE with the highest viral potential and engagement probability.

    **Posts to Analyze:**
    {posts_text}

    **Evaluation Criteria (Rate each post 1-10):**

    **1. HOOK STRENGTH (40% weight):**
    - Opening impact and attention-grabbing power
    - Curiosity generation and scroll-stopping ability
    - Emotional resonance (excitement, urgency, FOMO, controversy)

    **2. ENGAGEMENT POTENTIAL (30% weight):**
    - Likelihood to generate replies, retweets, likes
    - Discussion-starting capability
    - Shareability and viral mechanics

    **3. AUTHORITY & CREDIBILITY (20% weight):**
    - Technical depth and expertise demonstration
    - Industry insight and thought leadership
    - Authenticity and human voice

    **4. TECHNICAL OPTIMIZATION (10% weight):**
    - Character count efficiency
    - Hashtag strategy and discoverability
    - Call-to-action effectiveness

    **Analysis Process:**
    1. Evaluate each post against all criteria
    2. Consider target audience (crypto enthusiasts, developers, investors)
    3. Assess timing relevance and trend alignment
    4. Predict engagement patterns and viral potential

    **Response Format:**
    ANALYSIS:
    Post 1: [Brief analysis with scores]
    Post 2: [Brief analysis with scores]
    Post 3: [Brief analysis with scores if applicable]

    WINNER: POST [NUMBER]
    REASON: [2-3 sentences explaining why this post has the highest viral potential]

    SELECTED_POST:
    [Return the exact text of the winning post without any modifications]

    Analyze thoroughly and select the post most likely to go viral and drive maximum engagement.
    """

    try:
        # Prepare the request payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": selection_prompt
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
            
            # Extract the selected post from the response
            lines = generated_text.split('\n')
            selected_post = ""
            capture_post = False
            
            for line in lines:
                line = line.strip()
                if line.startswith('SELECTED_POST:'):
                    capture_post = True
                    continue
                elif capture_post and line:
                    if selected_post:
                        selected_post += " " + line
                    else:
                        selected_post = line
                elif capture_post and not line:
                    break
            
            if selected_post:
                logging.info("Best post selected successfully using AI analysis")
                return selected_post.strip()
            else:
                # Fallback: try to extract winner number and return corresponding post
                for line in lines:
                    if line.startswith('WINNER: POST'):
                        try:
                            winner_num = int(line.split('POST')[1].strip())
                            if 1 <= winner_num <= len(posts):
                                logging.info(f"Selected post {winner_num} based on AI analysis")
                                return posts[winner_num - 1]
                        except (ValueError, IndexError):
                            pass
                
                # Final fallback: return first post
                logging.warning("Could not parse AI selection, returning first post")
                return posts[0]
        else:
            logging.error(f"Gemini API Error during post selection: {response.status_code} - {response.text}")
            return posts[0]  # Return first post as fallback
            
    except Exception as e:
        logging.error(f"Error selecting best post with AI: {e}")
        return posts[0]  # Return first post as fallback

def review_post_with_ai(post_text):
    """Reviews and potentially improves a post using Gemini AI with advanced optimization strategies."""
    try:
        # First, check for placeholder content
        import re
        placeholder_patterns = [
            r'\[.*?\]',  # Any text in square brackets
            r'hypothetical_\w+',  # Words starting with "hypothetical_"
            r'example_\w+',  # Words starting with "example_"
            r'placeholder_\w+',  # Words starting with "placeholder_"
            r'sample_\w+',  # Words starting with "sample_"
        ]
        
        for pattern in placeholder_patterns:
            if re.search(pattern, post_text, re.IGNORECASE):
                logging.warning(f"🚫 Post rejected: Contains placeholder content matching pattern '{pattern}'")
                return None  # Reject posts with placeholder content
        
        review_prompt = f"""
        You are an expert social media strategist and viral content creator specializing in crypto/blockchain content. Your mission is to optimize this X post for maximum engagement and virality.

        **Current Post:** "{post_text}"

        **CRITICAL CONTENT RULES:**
        - NEVER include placeholder text in square brackets like [anything]
        - NEVER use hypothetical links or fake repository references
        - Only reference REAL, ACTUAL projects and links
        - If you can't verify a link or project, remove the reference entirely
        - Focus on the core message and insights, not placeholder content

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

def generate_dynamic_search_query():
    """
    Uses AI to generate dynamic, contextual search queries based on crypto niches and current trends.
    Returns a targeted search query for trend research.
    """
    global RECENT_QUERIES
    
    if not GEMINI_API_KEY:
        logging.warning("Gemini API key not configured for dynamic query generation. Using fallback.")
        # Fallback to enhanced static queries
        enhanced_queries = [
            "Vitalik Buterin latest tweets and announcements",
            "CZ Binance recent updates and statements", 
            "crypto development breakthroughs this week",
            "blockchain innovation and new protocols",
            "DeFi protocol launches and updates",
            "NFT market trends and major sales",
            "crypto regulatory news and policy changes",
            "web3 gaming and metaverse developments",
            "Layer 2 scaling solutions progress",
            "crypto institutional adoption news",
            "smart contract security and audits",
            "decentralized identity solutions",
            "zero-knowledge proof implementations",
            "crypto Twitter viral discussions",
            "major crypto partnerships and collaborations"
        ]
        # Filter out recently used queries
        available_queries = [q for q in enhanced_queries if q not in RECENT_QUERIES]
        if not available_queries:
            available_queries = enhanced_queries  # Reset if all used
            RECENT_QUERIES.clear()
        
        selected_query = random.choice(available_queries)
        RECENT_QUERIES.append(selected_query)
        if len(RECENT_QUERIES) > MAX_RECENT_QUERIES:
            RECENT_QUERIES.pop(0)
        return selected_query

    try:
        # Build recent queries context for AI to avoid repetition
        recent_context = ""
        if RECENT_QUERIES:
            recent_context = f"\n\n**IMPORTANT - AVOID THESE RECENT TOPICS:**\n{', '.join(RECENT_QUERIES[-5:])}\n\nGenerate something COMPLETELY DIFFERENT from these recent queries."

        # AI prompt to generate contextual search queries
        query_prompt = f"""
        You are an expert crypto trend researcher and social media strategist. Generate ONE highly specific, engaging search query that would uncover the most viral and trending crypto content right now.

        **Your Expertise Areas:**
        - Crypto development and technical innovations
        - Crypto news and market movements  
        - Crypto trends and viral discussions
        - Crypto innovations and breakthrough technologies
        - Influential crypto personalities (Vitalik Buterin, CZ, Satoshi references, etc.)
        - Cryptography and security developments
        - Web3 and blockchain development
        - DeFi, NFTs, and emerging protocols
        - Regulatory developments and institutional adoption
        - Community discussions and debates

        **Query Generation Strategy:**
        - Focus on RECENT developments (last 24-48 hours)
        - Target HIGH-ENGAGEMENT topics that spark discussion
        - Include specific names, projects, or events when relevant
        - Balance technical depth with broad appeal
        - Consider what's trending on Crypto Twitter right now
        - Look for controversial, exciting, or breakthrough developments
        - VARY your topics - explore different crypto niches each time

        **Examples of Great Queries:**
        - "Solana network outage recovery and validator updates"
        - "Bitcoin ETF approval impact on institutional adoption"
        - "Polygon zkEVM mainnet launch and developer migration"
        - "Coinbase regulatory compliance and SEC developments"
        - "Chainlink oracle integration with traditional finance"
        - "Uniswap v4 hooks and concentrated liquidity features"
        - "Arbitrum token airdrop and governance proposals"
        - "OpenSea NFT marketplace competition and alternatives"
        {recent_context}

        Generate ONE specific, targeted search query (maximum 10 words) that would find the most engaging crypto content trending right now:
        """

        # Prepare the request payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": query_prompt
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
            generated_query = result['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # Clean up the response - remove quotes and extra formatting
            generated_query = generated_query.replace('"', '').replace("'", '').strip()
            
            # Ensure it's not too long
            if len(generated_query) > 100:
                generated_query = generated_query[:100].rsplit(' ', 1)[0]
            
            # Track this query to avoid repetition
            RECENT_QUERIES.append(generated_query)
            if len(RECENT_QUERIES) > MAX_RECENT_QUERIES:
                RECENT_QUERIES.pop(0)
            
            logging.info(f"AI generated search query: '{generated_query}'")
            return generated_query
        else:
            logging.error(f"Gemini API Error during query generation: {response.status_code} - {response.text}")
            # Fallback to enhanced static query with diversity
            enhanced_queries = [
                "Solana network performance and validator updates",
                "Bitcoin Lightning Network adoption progress", 
                "Ethereum Layer 2 scaling solution developments",
                "Polygon zkEVM and zero-knowledge innovations",
                "Chainlink oracle integrations and partnerships"
            ]
            available_queries = [q for q in enhanced_queries if q not in RECENT_QUERIES]
            if not available_queries:
                available_queries = enhanced_queries
                RECENT_QUERIES.clear()
            
            selected_query = random.choice(available_queries)
            RECENT_QUERIES.append(selected_query)
            if len(RECENT_QUERIES) > MAX_RECENT_QUERIES:
                RECENT_QUERIES.pop(0)
            return selected_query
            
    except Exception as e:
        logging.error(f"Error generating dynamic search query: {e}")
        # Fallback to enhanced static query with diversity
        enhanced_queries = [
            "crypto development breakthroughs",
            "blockchain innovation news",
            "web3 trending discussions",
            "crypto regulatory updates",
            "DeFi protocol developments"
        ]
        available_queries = [q for q in enhanced_queries if q not in RECENT_QUERIES]
        if not available_queries:
            available_queries = enhanced_queries
            RECENT_QUERIES.clear()
        
        selected_query = random.choice(available_queries)
        RECENT_QUERIES.append(selected_query)
        if len(RECENT_QUERIES) > MAX_RECENT_QUERIES:
            RECENT_QUERIES.pop(0)
        return selected_query

def get_trending_content():
    """
    Uses Perplexity AI to research current trends in blockchain, crypto, and web3.
    Returns a list of relevant content snippets based on real-time information.
    """
    if not PERPLEXITY_API_KEY:
        logging.error("Perplexity API key not configured for trend research.")
        return []

    try:
        # Generate a dynamic query using AI based on crypto niches
        query = generate_dynamic_search_query()
        logging.info(f"Researching trends with AI-generated query: '{query}'")

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

def load_schedule(silent=False):
    """
    Loads the schedule from schedule.json file.
    Returns the schedule data or creates a new one if file doesn't exist.
    
    Args:
        silent (bool): If True, suppresses info logging to avoid spam
    """
    try:
        if os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, 'r') as f:
                schedule_data = json.load(f)
                if not silent:
                    logging.info("Loaded existing schedule from schedule.json")
                return schedule_data
        else:
            if not silent:
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

def create_new_schedule(first_post_minutes=None, posts_per_day=None, interval_minutes=None):
    """
    Creates a new schedule for today with random post times or fixed intervals.
    
    Args:
        first_post_minutes (int, optional): If provided, schedules the first post 
                                          after this many minutes from now.
        posts_per_day (int, optional): Number of posts to schedule per day (default: 5).
        interval_minutes (int, optional): If provided, schedules posts at fixed intervals 
                                        instead of random times.
    """
    today = date.today().isoformat()
    
    # Set default posts per day if not provided
    if posts_per_day is None:
        posts_per_day = 5
    
    # Validate posts_per_day
    if posts_per_day < 1:
        posts_per_day = 1
        logging.warning("Posts per day cannot be less than 1, setting to 1")
    elif posts_per_day > 20:
        posts_per_day = 20
        logging.warning("Posts per day cannot be more than 20, setting to 20")
    
    # Interval-based scheduling
    if interval_minutes is not None:
        logging.info(f"Creating interval-based schedule with {interval_minutes} minute intervals")
        
        # Start from now or from first_post_minutes if specified
        if first_post_minutes is not None:
            start_time = datetime.now() + timedelta(minutes=first_post_minutes)
        else:
            start_time = datetime.now() + timedelta(minutes=interval_minutes)
        
        all_minutes = []
        current_time = start_time
        
        # Generate posts at fixed intervals until end of day or max posts reached
        END_OF_DAY = datetime.now().replace(hour=23, minute=59, second=59)
        
        for i in range(posts_per_day):
            if current_time > END_OF_DAY:
                break
                
            # Convert to minutes from midnight
            minutes_from_midnight = current_time.hour * 60 + current_time.minute
            all_minutes.append(minutes_from_midnight)
            
            # Add interval for next post
            current_time += timedelta(minutes=interval_minutes)
        
        logging.info(f"Scheduled {len(all_minutes)} posts at {interval_minutes}-minute intervals")
        
    elif first_post_minutes is not None:
        # Schedule first post at specified time from now
        first_post_time = datetime.now() + timedelta(minutes=first_post_minutes)
        first_hour = first_post_time.hour
        first_minute = first_post_time.minute
        first_time_str = f"{first_hour:02d}:{first_minute:02d}"
        
        # Posting window in minutes from midnight (9:00 = 540, 21:00 = 1260)
        START_MIN = 540 
        END_MIN = 1260
        
        # Calculate first post time in minutes from midnight
        first_post_minutes_from_midnight = first_hour * 60 + first_minute
        
        # Generate additional random times after the first post within the window
        # Ensure they're after the first post time
        min_time = max(first_post_minutes_from_midnight + 30, START_MIN)  # At least 30 min after first post
        max_time = END_MIN
        
        if min_time >= max_time:
            # If first post is too late, just use it alone
            random_minutes = []
        else:
            # Generate remaining times
            available_range = list(range(min_time, max_time))
            num_additional = min(posts_per_day - 1, len(available_range))
            if num_additional > 0:
                random_minutes = sorted(random.sample(available_range, num_additional))
            else:
                random_minutes = []
        
        # Combine first post with additional posts
        all_minutes = [first_post_minutes_from_midnight] + random_minutes
        all_minutes = sorted(list(set(all_minutes)))  # Remove duplicates and sort
        
    else:
        # Default behavior: random times within posting window
        START_MIN = 540 
        END_MIN = 1260
        available_range = list(range(START_MIN, END_MIN))
        num_posts = min(posts_per_day, len(available_range))
        all_minutes = sorted(random.sample(available_range, num_posts))
    
    post_times = []
    for minutes in all_minutes:
        hour = minutes // 60
        minute = minutes % 60
        time_str = f"{hour:02d}:{minute:02d}"
        post_times.append({
            "time": time_str,
            "completed": False,
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        })
    
    schedule_data = {
        "date": today,
        "posts": post_times,
        "posts_completed": 0,
        "max_posts_per_day": len(post_times)
    }
    
    save_schedule(schedule_data)
    logging.info(f"Created new schedule with {len(post_times)} posts for {today}")
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
            post["completed_at"] = datetime.now(timezone.utc).isoformat()
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

def schedule_posts_smart(first_post_minutes=None, posts_per_day=None, interval_minutes=None):
    """
    Smart scheduler that checks existing schedule and updates for new days.
    
    Args:
        first_post_minutes (int, optional): If provided, resets schedule and schedules 
                                          first post after this many minutes from now.
        posts_per_day (int, optional): Number of posts to schedule per day.
        interval_minutes (int, optional): If provided, schedules posts at fixed intervals.
    """
    schedule_data = load_schedule()
    
    # If first_post_minutes or interval_minutes is provided, reset the schedule
    if first_post_minutes is not None or interval_minutes is not None:
        if interval_minutes is not None:
            logging.info(f"Resetting schedule with {interval_minutes} minute intervals")
        if first_post_minutes is not None:
            logging.info(f"First post scheduled in {first_post_minutes} minutes")
        schedule_data = create_new_schedule(first_post_minutes, posts_per_day, interval_minutes)
    # Check if it's a new day
    elif is_new_day(schedule_data):
        logging.info("New day detected, creating fresh schedule")
        schedule_data = create_new_schedule(posts_per_day=posts_per_day)
    
    # Clear any existing scheduled jobs
    schedule.clear()
    
    # Schedule remaining posts for today
    remaining_posts = [post for post in schedule_data["posts"] if not post["completed"]]
    
    if not remaining_posts:
        logging.info("All posts for today have been completed")
        return
    
    logging.info(f"Scheduling {len(remaining_posts)} remaining posts for today:")
    current_time = datetime.now()
    logging.info(f"Current local time: {current_time.strftime('%H:%M:%S')}")
    
    for post in remaining_posts:
        time_str = post["time"]
        
        # Parse the scheduled time and check if it's in the future
        try:
            scheduled_hour, scheduled_minute = map(int, time_str.split(':'))
            scheduled_time = current_time.replace(hour=scheduled_hour, minute=scheduled_minute, second=0, microsecond=0)
            
            # If the scheduled time has already passed today, skip it
            if scheduled_time <= current_time:
                logging.warning(f"Scheduled time {time_str} has already passed today, marking as completed")
                update_schedule_after_post(time_str)
                continue
                
        except ValueError:
            logging.error(f"Invalid time format: {time_str}")
            continue
        
        # Create a closure to capture the current time_str
        def create_post_job(post_time):
            def job():
                logging.info(f"🚀 Executing scheduled post at {post_time}")
                tweet_id = create_and_post()
                if tweet_id:
                    update_schedule_after_post(post_time)
                    logging.info(f"✅ Post at {post_time} completed successfully and schedule updated")
                else:
                    logging.error(f"❌ Post at {post_time} failed - schedule not updated")
            return job
        
        # Schedule the job
        schedule.every().day.at(time_str).do(create_post_job(time_str))
        logging.info(f"✅ Scheduled post at: {time_str} (local time)")

def schedule_posts():
    """
    Legacy function for backward compatibility.
    Now redirects to smart scheduler.
    """
    schedule_posts_smart()

# --- Content Validation ---

def validate_content_length(content, min_length=100):
    """
    Validates if the content meets minimum length requirements.
    
    Args:
        content (str): The content to validate
        min_length (int): Minimum character length required (default: 100)
    
    Returns:
        bool: True if content is long enough, False otherwise
    """
    if not content:
        return False
    
    # Remove hashtags and extra whitespace for length calculation
    clean_content = content.strip()
    # Remove common hashtag patterns for more accurate content length
    import re
    clean_content = re.sub(r'#\w+', '', clean_content).strip()
    
    actual_length = len(clean_content)
    logging.info(f"Content length validation: {actual_length} characters (min required: {min_length})")
    
    return actual_length >= min_length

def generate_alternative_content():
    """
    Generates content with alternative topics when original content is too short.
    
    Returns:
        list: Alternative content snippets focusing on different crypto topics
    """
    alternative_topics = [
        "Bitcoin price analysis and market trends",
        "Ethereum network upgrades and development updates", 
        "DeFi protocol innovations and yield farming strategies",
        "NFT marketplace developments and digital art trends",
        "Blockchain technology adoption in traditional finance",
        "Cryptocurrency regulatory updates and compliance news",
        "Layer 2 scaling solutions and network performance",
        "Web3 development tools and developer ecosystem growth",
        "Institutional crypto adoption and corporate treasury strategies",
        "Decentralized governance and DAO management trends"
    ]
    
    # Select 2-3 random alternative topics
    import random
    selected_topics = random.sample(alternative_topics, min(3, len(alternative_topics)))
    
    logging.info(f"Generated alternative topics: {selected_topics}")
    return selected_topics

# --- Main Posting Logic ---

def create_and_post():
    """Main function to perform the content curation, generation, review, and posting cycle with content length validation and retry logic."""
    logging.info("--- Starting Post Generation Cycle ---")
    
    max_retries = 2  # Maximum number of retries for short content
    retry_count = 0
    
    while retry_count <= max_retries:
        if retry_count > 0:
            logging.info(f"--- Retry Attempt {retry_count}/{max_retries} with Alternative Topics ---")
        
        # 1. Data Curation
        if retry_count == 0:
            # First attempt: use trending content
            content_snippets = get_trending_content()
            if not content_snippets:
                logging.warning("No trending content found. Using alternative topics.")
                content_snippets = generate_alternative_content()
        else:
            # Retry attempts: use alternative topics
            logging.info("Using alternative topics for content generation...")
            content_snippets = generate_alternative_content()
        
        if not content_snippets:
            logging.warning("No content found. Skipping post cycle.")
            return False
        
        # 2. AI Generation - Generate multiple posts
        logging.info("Generating multiple posts with AI...")
        generated_posts = generate_multiple_posts_with_ai(content_snippets, num_posts=2)
        if not generated_posts:
            logging.error("AI failed to generate posts. Trying next attempt...")
            retry_count += 1
            continue
        
        logging.info(f"Generated {len(generated_posts)} posts")
        for i, post in enumerate(generated_posts, 1):
            logging.debug(f"Generated Post {i}:\n{post}")
        
        # 3. AI Selection - Choose the best post
        logging.info("Selecting best post with AI...")
        selected_post = select_best_post_with_ai(generated_posts)
        if not selected_post:
            logging.error("AI failed to select best post. Trying next attempt...")
            retry_count += 1
            continue
        
        logging.info(f"Selected Post: {selected_post}")
        
        # 4. Content Length Validation
        if not validate_content_length(selected_post):
            logging.warning(f"⚠️ Content too short (attempt {retry_count + 1}/{max_retries + 1}). Regenerating with different topics...")
            retry_count += 1
            continue
        
        logging.info("✅ Content length validation passed")
        
        # 5. AI Review - Final optimization
        logging.info("Reviewing selected post with AI...")
        final_post = review_post_with_ai(selected_post)
        if not final_post:
            logging.warning("AI review failed. Using selected post without review.")
            final_post = selected_post
        logging.info(f"Final Approved Post: {final_post}")
        
        # 6. Final length check after review
        if not validate_content_length(final_post):
            logging.warning(f"⚠️ Final post too short after review (attempt {retry_count + 1}/{max_retries + 1}). Regenerating...")
            retry_count += 1
            continue
        
        # 7. Topic Diversity Check - Prevent repetitive content
        logging.info("Checking topic diversity against recent posts...")
        posts_data = load_posts_history()
        recent_posts = posts_data.get("posts", [])
        
        is_diverse = analyze_topic_similarity_with_ai(final_post, recent_posts)
        if not is_diverse:
            logging.warning("🚫 Post rejected: Too similar to recent posts. Skipping this cycle to maintain content diversity.")
            return False
        
        logging.info("✅ Post passed diversity check - content is sufficiently different from recent posts")
        
        # 8. Posting
        tweet_id = post_tweet(final_post)
        success = tweet_id is not None
        logging.info(f"Posting Status: {'SUCCESS' if success else 'FAILURE'}")
        
        # 9. Add to history if successful
        if success:
            # Extract metadata for history tracking
            template_name = "unknown"  # Will be enhanced when we integrate template selection
            personality_name = "unknown"  # Will be enhanced when we integrate personality selection
            search_query = "trending content" if retry_count == 0 else "alternative topics"
            trending_topics = content_snippets[:3] if content_snippets else []
            
            add_post_to_history(final_post, tweet_id, search_query, template_name, personality_name, trending_topics)
        
        return success
    
    # If all retries failed
    logging.error(f"❌ Failed to generate adequate content after {max_retries + 1} attempts. Skipping post cycle.")
    return False


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
    Immediate posting mode - generates multiple posts, selects the best one, reviews it, and posts it.
    """
    logging.info("Running in immediate post mode...")
    
    try:
        # Get trending content
        logging.info("Fetching trending content...")
        content_snippets = get_trending_content()
        
        if not content_snippets:
            logging.warning("No trending content found. Generating post with general topics.")
            content_snippets = ["Latest developments in blockchain and crypto technology"]
        
        # Generate multiple posts
        logging.info("Generating multiple posts with AI...")
        generated_posts = generate_multiple_posts_with_ai(content_snippets, num_posts=2)
        
        if not generated_posts:
            logging.error("Failed to generate post content")
            return False
        
        logging.info(f"Generated {len(generated_posts)} posts")
        for i, post in enumerate(generated_posts, 1):
            logging.debug(f"Generated Post {i}:\n{post}")
        
        # Select best post
        logging.info("Selecting best post with AI...")
        selected_post = select_best_post_with_ai(generated_posts)
        
        if not selected_post:
            logging.warning("Post selection failed, using first generated post")
            selected_post = generated_posts[0] if generated_posts else ""
        
        if not selected_post:
            logging.error("No valid post content available")
            return False
        
        logging.info(f"Selected Post: {selected_post}")
        
        # Review post
        logging.info("Reviewing selected post with AI...")
        reviewed_post = review_post_with_ai(selected_post)
        
        if not reviewed_post:
            logging.warning("Post review failed, using selected post without review")
            reviewed_post = selected_post
        
        # Topic Diversity Check - Prevent repetitive content
        logging.info("Checking topic diversity against recent posts...")
        posts_data = load_posts_history()
        recent_posts = posts_data.get("posts", [])
        
        is_diverse = analyze_topic_similarity_with_ai(reviewed_post, recent_posts)
        if not is_diverse:
            logging.warning("🚫 Post rejected: Too similar to recent posts. Skipping this cycle to maintain content diversity.")
            return False
        
        logging.info("✅ Post passed diversity check - content is sufficiently different from recent posts")
        
        # Post to Twitter
        logging.info("Posting to Twitter...")
        tweet_id = post_tweet(reviewed_post)
        success = tweet_id is not None
        
        if success:
            logging.info("Post successfully published!")
            logging.info(f"Posted content: {reviewed_post}")
            
            # Add to history
            template_name = "unknown"  # Will be enhanced when we integrate template selection
            personality_name = "unknown"  # Will be enhanced when we integrate personality selection
            search_query = "trending content"  # Will be enhanced with actual search query
            trending_topics = content_snippets[:3] if content_snippets else []
            
            add_post_to_history(reviewed_post, tweet_id, search_query, template_name, personality_name, trending_topics)
            
            return True
        else:
            logging.error("Failed to post to Twitter")
            return False
            
    except Exception as e:
        logging.error(f"Error in post_now_mode: {e}")
        return False

def get_next_post_countdown():
    """
    Get the time remaining until the next scheduled post.
    Returns a formatted string with the countdown.
    """
    try:
        schedule_data = load_schedule(silent=True)  # Use silent mode to prevent logging spam
        if not schedule_data or 'posts' not in schedule_data:
            return "No posts scheduled"
        
        now = datetime.now()  # Use local time instead of UTC
        next_post_time = None
        
        # Find the next scheduled post
        for post in schedule_data['posts']:
            # Check if post is not completed (using 'completed' field)
            if not post.get('completed', False):
                # Parse the time field to create a datetime for today
                time_str = post['time']
                hour, minute = map(int, time_str.split(':'))
                
                # Create datetime for today with the scheduled time (local time)
                today = now.date()
                post_time = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
                # No timezone conversion needed - keep as local time
                
                # If the time has passed today, schedule for tomorrow
                if post_time <= now:
                    post_time = post_time + timedelta(days=1)
                
                if next_post_time is None or post_time < next_post_time:
                    next_post_time = post_time
        
        if next_post_time is None:
            return "No upcoming posts scheduled"
        
        # Calculate time difference
        time_diff = next_post_time - now
        total_seconds = int(time_diff.total_seconds())
        
        if total_seconds <= 0:
            return "Next post due now!"
        
        # Format the countdown
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"Next post in: {hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"Next post in: {minutes}m {seconds}s"
        else:
            return f"Next post in: {seconds}s"
            
    except Exception as e:
        logging.error(f"Error calculating countdown: {e}")
        return "Countdown unavailable"

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='X Auto Poster - Automated Twitter posting tool')
    parser.add_argument('--post-now', action='store_true', 
                       help='Generate and post immediately, then exit (no scheduling)')
    parser.add_argument('--fp', '--first-post', type=int, metavar='MINUTES',
                       help='Schedule first post after specified minutes from now (resets existing schedule)')
    parser.add_argument('--ppd', '--posts-per-day', type=int, metavar='COUNT', default=5,
                       help='Number of posts to schedule per day (default: 5, min: 1, max: 20)')
    parser.add_argument('--interval', type=int, metavar='MINUTES',
                       help='Post every X minutes (e.g., 30 for every 30 minutes). Overrides random scheduling.')
    return parser.parse_args()

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    if initialize_clients():
        if args.post_now:
            # Immediate posting mode
            logging.info("Starting immediate post mode...")
            tweet_id = post_now_mode()
            if tweet_id:
                logging.info("Immediate post completed successfully!")
            else:
                logging.error("Immediate post failed!")
            logging.info("Exiting...")
        else:
            logging.info("Starting scheduled mode...")
            schedule_posts_smart(args.fp, args.ppd, args.interval)  # Pass --fp, --ppd, and --interval arguments

            logging.info("Scheduler started. The tool will now run indefinitely, posting daily.")
            logging.info("Press Ctrl+C to stop the process.")
            
            # Main scheduler loop
            try:
                import sys
                while True:
                    schedule.run_pending()
                    
                    # Display real-time countdown that updates every second
                    countdown = get_next_post_countdown()
                    # Use carriage return to overwrite the same line
                    sys.stdout.write(f"\r📅 {countdown}")
                    sys.stdout.flush()
                    
                    time.sleep(1)
            except KeyboardInterrupt:
                logging.info("Scheduler stopped by user.")
            except Exception as e:
                logging.error(f"Unexpected error in scheduler loop: {e}")
                logging.info("Restarting scheduler in 60 seconds...")
                time.sleep(60)
                # Restart scheduler with same parameters
                schedule_posts_smart(args.fp, args.ppd, args.interval)
            
    else:
        logging.critical("Tool failed to initialize. Please check the .env file and your network connection.")
    logging.info("---------------------------------------------")

