"""
Google Trends Collector
Collects trending searches via SerpAPI's Google Trends Trending Now endpoint.
API docs: https://serpapi.com/google-trends-trending-now
"""
import aiohttp
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.trend_detector.collectors.base import BaseCollector
from app.trend_detector.config import SERPAPI_KEY


class GoogleTrendsCollector(BaseCollector):
    platform = "google_trends"

    SERPAPI_URL = "https://serpapi.com/search.json"

    # Regions to check (geo codes)
    REGIONS = [
        {"geo": "SA", "hl": "ar"},  # Saudi Arabia, Arabic
        {"geo": "US", "hl": "en"},  # United States, English
    ]

    def is_configured(self) -> bool:
        return bool(SERPAPI_KEY)

    async def collect(self) -> List[Dict[str, Any]]:
        """Collect trending searches from Google Trends via SerpAPI"""
        if not self.is_configured():
            print("[GoogleTrendsCollector] Not configured — skipping (add SERPAPI_KEY to .env)")
            return []

        signals = []
        seen_ids = set()

        async with aiohttp.ClientSession() as session:
            for region_config in self.REGIONS:
                geo = region_config["geo"]
                hl = region_config["hl"]
                try:
                    params = {
                        "engine": "google_trends_trending_now",
                        "geo": geo,
                        "hl": hl,
                        "hours": 24,
                        "api_key": SERPAPI_KEY,
                    }

                    async with session.get(self.SERPAPI_URL, params=params) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            print(f"[GoogleTrendsCollector] SerpAPI error for {geo}: {resp.status} — {body[:200]}")
                            continue

                        data = await resp.json()
                        trending = data.get("trending_searches", [])

                        for item in trending:
                            query = item.get("query", "")
                            if not query:
                                continue

                            trend_id = f"gt_{geo}_{query[:100]}"
                            if trend_id in seen_ids:
                                continue
                            seen_ids.add(trend_id)

                            # Extract search volume as a proxy for views
                            search_volume = item.get("search_volume", 0)
                            increase_pct = item.get("increase_percentage", 0)

                            # Extract categories
                            categories = item.get("categories", [])
                            category_names = [c.get("name", "") for c in categories if c.get("name")]

                            # Extract trend_breakdown as related keywords
                            trend_breakdown = item.get("trend_breakdown", [])
                            all_keywords = category_names + trend_breakdown[:5]
                            keywords_str = ",".join(all_keywords) if all_keywords else query

                            # Build explore link
                            explore_link = item.get("serpapi_google_trends_link", "")

                            # Published time from start_timestamp
                            published_at = None
                            start_ts = item.get("start_timestamp")
                            if start_ts:
                                try:
                                    published_at = datetime.fromtimestamp(int(start_ts), tz=timezone.utc)
                                except (ValueError, OSError):
                                    pass

                            is_active = item.get("active", False)

                            signal = self._make_signal(
                                source_id=trend_id,
                                title=query,
                                content=f"Trending search: {query}. Related: {', '.join(trend_breakdown[:5])}",
                                url=explore_link or f"https://trends.google.com/trending?geo={geo}",
                                media_url=None,
                                keywords=keywords_str,
                                author=None,
                                published_at=published_at or datetime.now(timezone.utc),
                                views=search_volume,
                                likes=0,
                                reshares=0,
                                comments=0,
                                has_media=False,
                                raw_data={
                                    "geo": geo,
                                    "hl": hl,
                                    "search_volume": search_volume,
                                    "increase_percentage": increase_pct,
                                    "active": is_active,
                                    "categories": categories,
                                    "trend_breakdown": trend_breakdown[:10],
                                },
                            )
                            signals.append(signal)

                except Exception as e:
                    print(f"[GoogleTrendsCollector] Error for region {geo}: {e}")
                    continue

        print(f"[GoogleTrendsCollector] Collected {len(signals)} signals")
        return signals
