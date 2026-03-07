"""
Vision Analyzer
Analyzes media (images) using Google Cloud Vision API to extract text and labels.
Runs as a pre-filter before normalization: signals with media get their media_text populated.
"""
import aiohttp
import base64
from typing import List, Dict, Any

from app.trend_detector.config import GOOGLE_VISION_API_KEY


class VisionAnalyzer:
    """Analyze images using Google Cloud Vision API"""

    VISION_URL = "https://vision.googleapis.com/v1/images:annotate"

    def is_configured(self) -> bool:
        return bool(GOOGLE_VISION_API_KEY)

    async def analyze_image_url(self, image_url: str) -> str:
        """
        Analyze an image by URL using Google Vision API.
        Returns extracted text + labels as a combined string.
        """
        if not self.is_configured() or not image_url:
            return ""

        payload = {
            "requests": [
                {
                    "image": {"source": {"imageUri": image_url}},
                    "features": [
                        {"type": "TEXT_DETECTION", "maxResults": 5},
                        {"type": "LABEL_DETECTION", "maxResults": 10},
                    ],
                }
            ]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.VISION_URL}?key={GOOGLE_VISION_API_KEY}",
                    json=payload,
                ) as resp:
                    if resp.status != 200:
                        print(f"[VisionAnalyzer] API error: {resp.status}")
                        return ""

                    data = await resp.json()
                    responses = data.get("responses", [])
                    if not responses:
                        return ""

                    result = responses[0]
                    parts = []

                    # Extract text
                    text_annotations = result.get("textAnnotations", [])
                    if text_annotations:
                        full_text = text_annotations[0].get("description", "")
                        if full_text:
                            parts.append(full_text.strip())

                    # Extract labels
                    label_annotations = result.get("labelAnnotations", [])
                    labels = [
                        label.get("description", "")
                        for label in label_annotations
                        if label.get("score", 0) > 0.7
                    ]
                    if labels:
                        parts.append("Labels: " + ", ".join(labels))

                    return " | ".join(parts) if parts else ""

        except Exception as e:
            print(f"[VisionAnalyzer] Error analyzing image: {e}")
            return ""

    async def process_signals(self, raw_signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a list of raw signal dicts.
        For signals with has_media=True and a media_url, analyze the image
        and populate media_text field.
        
        Signals without media pass through unchanged.
        """
        if not self.is_configured():
            # Pass through without modification
            return raw_signals

        analyzed_count = 0
        for signal in raw_signals:
            if signal.get("has_media") and signal.get("media_url") and not signal.get("media_text"):
                media_url = signal["media_url"]
                # Only analyze image URLs (skip video URLs)
                if self._is_image_url(media_url):
                    text = await self.analyze_image_url(media_url)
                    if text:
                        signal["media_text"] = text
                        analyzed_count += 1

        if analyzed_count:
            print(f"[VisionAnalyzer] Analyzed {analyzed_count} images from {len(raw_signals)} signals")

        return raw_signals

    def _is_image_url(self, url: str) -> bool:
        """Check if URL likely points to an image"""
        if not url:
            return False
        url_lower = url.lower()
        image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
        if any(url_lower.endswith(ext) for ext in image_extensions):
            return True
        # Common image hosting patterns
        image_hosts = ("i.redd.it", "i.imgur.com", "pbs.twimg.com", "preview.redd.it")
        if any(host in url_lower for host in image_hosts):
            return True
        return False
