"""
Base Collector Interface
All platform collectors inherit from this
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime


class BaseCollector(ABC):
    """Abstract base class for all trend signal collectors"""

    platform: str = "unknown"

    @abstractmethod
    async def collect(self) -> List[Dict[str, Any]]:
        """
        Collect raw signals from the platform.
        
        Returns a list of dicts with this normalized shape:
        {
            "platform": str,
            "source_id": str,
            "title": str,
            "content": str | None,
            "url": str | None,
            "media_url": str | None,
            "keywords": str | None,       # comma-separated
            "author": str | None,
            "published_at": datetime | None,
            "views": int,
            "likes": int,
            "reshares": int,
            "comments": int,
            "has_media": bool,
            "raw_data": dict,
        }
        """
        pass

    def is_configured(self) -> bool:
        """Check if required API keys are available"""
        return True

    def _make_signal(
        self,
        source_id: str,
        title: str,
        content: str = None,
        url: str = None,
        media_url: str = None,
        keywords: str = None,
        author: str = None,
        published_at: datetime = None,
        views: int = 0,
        likes: int = 0,
        reshares: int = 0,
        comments: int = 0,
        has_media: bool = False,
        raw_data: dict = None,
    ) -> Dict[str, Any]:
        """Helper to create a standardized signal dict"""
        return {
            "platform": self.platform,
            "source_id": str(source_id),
            "title": title or "",
            "content": content,
            "url": url,
            "media_url": media_url,
            "keywords": keywords,
            "author": author,
            "published_at": published_at,
            "views": views or 0,
            "likes": likes or 0,
            "reshares": reshares or 0,
            "comments": comments or 0,
            "has_media": has_media,
            "raw_data": raw_data or {},
        }
