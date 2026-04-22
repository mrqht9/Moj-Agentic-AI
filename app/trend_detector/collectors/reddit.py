"""
Reddit Collector
Collects trending/rising signals from Reddit using the official API
Targets: r/all rising, popular/hot
"""
import aiohttp
import base64
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.trend_detector.collectors.base import BaseCollector
from app.trend_detector.config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
)


class RedditCollector(BaseCollector):
    platform = "reddit"

    AUTH_URL = "https://www.reddit.com/api/v1/access_token"
    BASE_URL = "https://oauth.reddit.com"

    # Subreddits and feeds to check
    FEEDS = [
        "/r/all/rising",
        "/r/all/hot",
        "/r/popular/hot",
    ]

    LIMIT_PER_FEED = 25  # Posts per feed

    def __init__(self):
        self._access_token = None
        self._token_expires_at = None

    def is_configured(self) -> bool:
        return bool(REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET)

    async def _authenticate(self, session: aiohttp.ClientSession) -> str:
        """Get OAuth2 access token from Reddit"""
        if (
            self._access_token
            and self._token_expires_at
            and datetime.now(timezone.utc) < self._token_expires_at
        ):
            return self._access_token

        credentials = base64.b64encode(
            f"{REDDIT_CLIENT_ID}:{REDDIT_CLIENT_SECRET}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {credentials}",
            "User-Agent": REDDIT_USER_AGENT,
        }
        data = {
            "grant_type": "client_credentials",
        }

        async with session.post(self.AUTH_URL, headers=headers, data=data) as resp:
            if resp.status != 200:
                raise Exception(f"Reddit auth failed: {resp.status}")
            result = await resp.json()
            self._access_token = result["access_token"]
            # Token typically expires in 3600s, refresh a bit earlier
            from datetime import timedelta
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=result.get("expires_in", 3600) - 60)
            return self._access_token

    async def collect(self) -> List[Dict[str, Any]]:
        """Collect trending posts from Reddit"""
        if not self.is_configured():
            print("[RedditCollector] Not configured — skipping (add REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to .env)")
            return []

        signals = []
        seen_ids = set()

        async with aiohttp.ClientSession() as session:
            token = await self._authenticate(session)

            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": REDDIT_USER_AGENT,
            }

            for feed in self.FEEDS:
                try:
                    url = f"{self.BASE_URL}{feed}?limit={self.LIMIT_PER_FEED}"
                    async with session.get(url, headers=headers) as resp:
                        if resp.status != 200:
                            print(f"[RedditCollector] Failed to fetch {feed}: {resp.status}")
                            continue

                        data = await resp.json()
                        posts = data.get("data", {}).get("children", [])

                        for post in posts:
                            post_data = post.get("data", {})
                            post_id = post_data.get("id", "")

                            # Skip duplicates across feeds
                            if post_id in seen_ids:
                                continue
                            seen_ids.add(post_id)

                            # Determine if post has media
                            has_media = False
                            media_url = None

                            if post_data.get("is_video"):
                                has_media = True
                                media_url = post_data.get("url")
                            elif post_data.get("post_hint") == "image":
                                has_media = True
                                media_url = post_data.get("url")
                            elif post_data.get("thumbnail", "").startswith("http"):
                                has_media = True
                                media_url = post_data.get("thumbnail")

                            # Parse published time
                            created_utc = post_data.get("created_utc")
                            published_at = None
                            if created_utc:
                                published_at = datetime.fromtimestamp(
                                    created_utc, tz=timezone.utc
                                )

                            signal = self._make_signal(
                                source_id=post_id,
                                title=post_data.get("title", ""),
                                content=post_data.get("selftext", ""),
                                url=f"https://reddit.com{post_data.get('permalink', '')}",
                                media_url=media_url,
                                keywords=post_data.get("subreddit", ""),
                                author=post_data.get("author", ""),
                                published_at=published_at,
                                views=post_data.get("view_count") or 0,
                                likes=post_data.get("ups", 0),
                                reshares=post_data.get("num_crossposts", 0),
                                comments=post_data.get("num_comments", 0),
                                has_media=has_media,
                                raw_data={
                                    "subreddit": post_data.get("subreddit"),
                                    "subreddit_subscribers": post_data.get("subreddit_subscribers"),
                                    "upvote_ratio": post_data.get("upvote_ratio"),
                                    "domain": post_data.get("domain"),
                                    "link_flair_text": post_data.get("link_flair_text"),
                                    "over_18": post_data.get("over_18"),
                                    "feed": feed,
                                },
                            )
                            signals.append(signal)

                except Exception as e:
                    print(f"[RedditCollector] Error fetching {feed}: {e}")
                    continue

        print(f"[RedditCollector] Collected {len(signals)} signals")
        return signals
