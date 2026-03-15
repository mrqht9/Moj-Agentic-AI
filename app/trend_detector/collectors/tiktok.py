"""
TikTok Collector
Collects trending content from TikTok via third-party API (RapidAPI or Apify).
"""
import aiohttp
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.trend_detector.collectors.base import BaseCollector
from app.trend_detector.config import TIKTOK_API_KEY, TIKTOK_API_PROVIDER


class TikTokCollector(BaseCollector):
    platform = "tiktok"

    # RapidAPI TikTok endpoint (default provider)
    RAPIDAPI_HOST = "tiktok-api23.p.rapidapi.com"
    RAPIDAPI_TRENDING_URL = "https://tiktok-api23.p.rapidapi.com/api/trending/feed"

    LIMIT = 30

    def is_configured(self) -> bool:
        return bool(TIKTOK_API_KEY)

    async def _collect_rapidapi(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Collect trending TikTok videos via RapidAPI"""
        headers = {
            "X-RapidAPI-Key": TIKTOK_API_KEY,
            "X-RapidAPI-Host": self.RAPIDAPI_HOST,
        }
        params = {
            "count": self.LIMIT,
            "region": "SA",  # Saudi Arabia
        }

        signals = []

        try:
            async with session.get(
                self.RAPIDAPI_TRENDING_URL,
                headers=headers,
                params=params,
            ) as resp:
                if resp.status != 200:
                    print(f"[TikTokCollector] RapidAPI error: {resp.status}")
                    return []

                data = await resp.json()
                items = data.get("itemList", data.get("items", []))

                for item in items:
                    video_id = item.get("id", "")
                    if not video_id:
                        continue

                    # Author info
                    author_info = item.get("author", {})
                    author = author_info.get("uniqueId", author_info.get("nickname", ""))

                    # Stats
                    stats = item.get("stats", {})

                    # Video/cover URL
                    video_data = item.get("video", {})
                    cover_url = video_data.get("cover", video_data.get("dynamicCover", ""))

                    # Description / hashtags
                    desc = item.get("desc", "")
                    challenges = item.get("challenges", [])
                    hashtags = [c.get("title", "") for c in challenges if c.get("title")]
                    keywords_str = ",".join(hashtags[:10])

                    # Published time
                    create_time = item.get("createTime", 0)
                    published_at = None
                    if create_time:
                        try:
                            published_at = datetime.fromtimestamp(int(create_time), tz=timezone.utc)
                        except (ValueError, OSError):
                            pass

                    has_media = True  # TikTok is always video content

                    signal = self._make_signal(
                        source_id=video_id,
                        title=desc[:500] if desc else f"TikTok by @{author}",
                        content=desc,
                        url=f"https://www.tiktok.com/@{author}/video/{video_id}",
                        media_url=cover_url,
                        keywords=keywords_str,
                        author=author,
                        published_at=published_at,
                        views=stats.get("playCount", 0),
                        likes=stats.get("diggCount", stats.get("likeCount", 0)),
                        reshares=stats.get("shareCount", 0),
                        comments=stats.get("commentCount", 0),
                        has_media=has_media,
                        raw_data={
                            "music": item.get("music", {}).get("title", ""),
                            "duration": video_data.get("duration", 0),
                            "challenges": hashtags,
                        },
                    )
                    signals.append(signal)

        except Exception as e:
            print(f"[TikTokCollector] RapidAPI error: {e}")

        return signals

    async def collect(self) -> List[Dict[str, Any]]:
        """Collect trending TikTok content"""
        if not self.is_configured():
            print("[TikTokCollector] Not configured — skipping (add TIKTOK_API_KEY to .env)")
            return []

        async with aiohttp.ClientSession() as session:
            if TIKTOK_API_PROVIDER == "rapidapi":
                signals = await self._collect_rapidapi(session)
            else:
                print(f"[TikTokCollector] Unknown provider: {TIKTOK_API_PROVIDER}")
                signals = []

        print(f"[TikTokCollector] Collected {len(signals)} signals")
        return signals
