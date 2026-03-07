"""
X (Twitter) Collector
Collects trending/viral content from X using a custom API server.
Endpoints: POST /api/search, GET /api/top_posts
"""
import aiohttp
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.trend_detector.collectors.base import BaseCollector
from app.trend_detector.config import X_API_SERVER_URL


class XCollector(BaseCollector):
    platform = "x"

    # Search queries — focused on Saudi/Arabic trending content
    SEARCH_QUERIES = [
        {"query": "ترند السعودية", "type": "Top", "max_pages": 3},
        {"query": "عاجل السعودية", "type": "Latest", "max_pages": 2},
        {"query": "هاشتاق ترند", "type": "Top", "max_pages": 2},
        {"query": "اكثر شي متداول", "type": "Latest", "max_pages": 2},
    ]

    # Countries for Creator Studio top posts
    TOP_POSTS_COUNTRIES = ["SAU", "ar"]

    REQUEST_TIMEOUT = 120  # seconds

    def is_configured(self) -> bool:
        return bool(X_API_SERVER_URL)

    async def _search_tweets(self, session: aiohttp.ClientSession, query_config: dict) -> List[Dict[str, Any]]:
        """Search tweets via POST /api/search"""
        try:
            async with session.post(
                f"{X_API_SERVER_URL}/api/search",
                json=query_config,
                timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    print(f"[XCollector] Search API error {resp.status} for query: {query_config['query']}")
                    return []

                data = await resp.json()
                if data.get("error"):
                    print(f"[XCollector] Search error: {data['error']}")
                    return []

                return data.get("tweets", [])

        except Exception as e:
            print(f"[XCollector] Search request error for '{query_config['query']}': {e}")
            return []

    async def _get_top_posts(self, session: aiohttp.ClientSession, country: str) -> List[Dict[str, Any]]:
        """Get top posts via GET /api/top_posts"""
        try:
            async with session.get(
                f"{X_API_SERVER_URL}/api/top_posts",
                params={"country": country},
                timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    print(f"[XCollector] Top posts API error {resp.status} for {country}")
                    return []

                data = await resp.json()
                if data.get("error"):
                    print(f"[XCollector] Top posts error: {data['error']}")
                    return []

                return data.get("tweets", [])

        except Exception as e:
            print(f"[XCollector] Top posts request error for {country}: {e}")
            return []

    def _parse_tweet(self, tweet: dict, source: str) -> Dict[str, Any]:
        """Convert a tweet from the custom API format into a normalized signal dict"""
        tweet_id = tweet.get("tweet_id", "")
        screen_name = tweet.get("screen_name", "")
        full_text = tweet.get("full_text", "")

        # Parse views_count (can be string like "150000")
        views = tweet.get("views_count", 0)
        if isinstance(views, str):
            try:
                views = int(views.replace(",", ""))
            except (ValueError, TypeError):
                views = 0

        # Media detection
        media_urls = tweet.get("media_urls", [])
        has_media = bool(media_urls)
        media_url = media_urls[0] if media_urls else None

        # Parse created_at
        published_at = None
        created_at_str = tweet.get("created_at")
        if created_at_str:
            try:
                published_at = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
            except (ValueError, TypeError):
                pass

        return self._make_signal(
            source_id=str(tweet_id),
            title=full_text[:500] if full_text else f"Tweet by @{screen_name}",
            content=full_text,
            url=f"https://x.com/{screen_name}/status/{tweet_id}",
            media_url=media_url,
            keywords="",
            author=screen_name,
            published_at=published_at,
            views=views or 0,
            likes=tweet.get("favorite_count", 0) or 0,
            reshares=tweet.get("retweet_count", 0) or 0,
            comments=tweet.get("reply_count", 0) or 0,
            has_media=has_media,
            raw_data={
                "source": source,
                "quote_count": tweet.get("quote_count", 0),
                "bookmark_count": tweet.get("bookmark_count", 0),
                "followers_count": tweet.get("followers_count", 0),
                "is_verified": tweet.get("is_verified", False),
                "lang": tweet.get("lang", ""),
                "user_name": tweet.get("user_name", ""),
                "media_urls": media_urls,
            },
        )

    async def collect(self) -> List[Dict[str, Any]]:
        """Collect trending tweets from X via custom API"""
        if not self.is_configured():
            print("[XCollector] Not configured — skipping (add X_API_SERVER_URL to .env)")
            return []

        signals = []
        seen_ids = set()

        async with aiohttp.ClientSession() as session:
            # 1. Search queries
            for query_config in self.SEARCH_QUERIES:
                tweets = await self._search_tweets(session, query_config)
                for tweet in tweets:
                    tid = tweet.get("tweet_id", "")
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        signals.append(self._parse_tweet(tweet, f"search:{query_config['query']}"))

            # 2. Creator Studio top posts
            for country in self.TOP_POSTS_COUNTRIES:
                tweets = await self._get_top_posts(session, country)
                for tweet in tweets:
                    tid = tweet.get("tweet_id", "")
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        signals.append(self._parse_tweet(tweet, f"top_posts:{country}"))

        print(f"[XCollector] Collected {len(signals)} signals")
        return signals
