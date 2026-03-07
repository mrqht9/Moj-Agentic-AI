"""
Trend Detector Configuration
Scoring weights, thresholds, intervals, and API settings
"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)


# =============================================================================
# API Keys (loaded from .env)
# =============================================================================
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "MojTrendDetector/1.0")

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

X_API_SERVER_URL = os.getenv("X_API_SERVER_URL", "")  # Custom X API server

TIKTOK_API_KEY = os.getenv("TIKTOK_API_KEY", "")
TIKTOK_API_PROVIDER = os.getenv("TIKTOK_API_PROVIDER", "rapidapi")  # rapidapi or apify

GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")


# =============================================================================
# Collector Polling Intervals (in minutes)
# =============================================================================
COLLECTOR_INTERVALS = {
    "x": 10,
    "google_trends": 30,
    "reddit": 15,
    "tiktok": 60,
}

# Watchlist re-check interval (minutes)
WATCHLIST_CHECK_INTERVAL = 15

# Max re-checks before EARLY signal expires
WATCHLIST_MAX_CHECKS = 6


# =============================================================================
# Scoring Weights
# Points awarded when a signal exceeds the platform-specific threshold
# =============================================================================
SCORING_WEIGHTS = {
    "views": 3,
    "reshares": 3,
    "likes": 4,
    "comments": 2,
    "unique_authors": 3,
    "cross_platform": 5,      # Signal found on 2+ platforms
    "trending_source": 6,     # Signal from a trending aggregator (e.g. Google Trends)
    "has_media": 1,           # Bonus for signals with media content
}


# =============================================================================
# Platform-Specific Thresholds
# A signal must exceed these to earn points for that metric
# =============================================================================
PLATFORM_THRESHOLDS = {
    "reddit": {
        "views": 5000,
        "reshares": 100,       # crosspost count
        "likes": 1000,         # upvotes
        "comments": 200,
    },
    "x": {
        "views": 10000,
        "reshares": 500,       # retweets
        "likes": 1000,
        "comments": 300,       # replies
    },
    "google_trends": {
        "views": 0,
        "reshares": 0,
        "likes": 0,
        "comments": 0,
        "is_trending_source": True,  # Auto-awarded trending_source bonus
    },
    "tiktok": {
        "views": 50000,
        "reshares": 1000,      # shares
        "likes": 5000,
        "comments": 500,
    },
}


# =============================================================================
# Validation Thresholds (X Validation stage)
# Used to decide HOT / EARLY / NOT_YET
# =============================================================================
VALIDATION_THRESHOLDS = {
    "hot": {
        "min_score": 8,             # Pre-filter score — X validation is the real gate
        "min_unique_authors": 8,    # At least 8 distinct posters on X
        "min_post_density": 4,      # At least 4 posts in last 4 hours
    },
    "early": {
        "min_score": 6,
        "min_unique_authors": 2,
        "min_post_density": 1,
    },
    # Below "early" thresholds → NOT_YET
}


# =============================================================================
# Classifier Categories
# =============================================================================
CLASSIFIER_CATEGORIES = [
    "سياسي",       # Political
    "اجتماعي",     # Social
    "رياضة",       # Sports
    "ترفيه",       # Entertainment
    "اقتصاد",      # Economy
    "تقنية",       # Technology
    "تاريخي",      # Historical
    "ثقافي",       # Cultural
    "صحة",         # Health
    "أخرى",        # Other
]

SENSITIVITY_LEVELS = ["low", "medium", "high", "critical"]


# =============================================================================
# Deduplication
# =============================================================================
DEDUP_SIMILARITY_THRESHOLD = 0.75  # Cosine similarity threshold for merging
