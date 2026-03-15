"""
Classifier Service
LLM-based classification + entity/keyword enrichment for HOT candidates.
"""
import json
from typing import List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.trend_detector.models import Candidate, Classification
from app.trend_detector.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    CLASSIFIER_CATEGORIES,
    SENSITIVITY_LEVELS,
)


class Classifier:
    """Classify candidates using OpenAI LLM"""

    SYSTEM_PROMPT = """أنت محلل محتوى متخصص في تصنيف الترندات والمحتوى الرائج.
مهمتك تصنيف المحتوى التالي وتحليله.

أجب بصيغة JSON فقط بدون أي نص إضافي:
{
    "category": "التصنيف الرئيسي",
    "subcategory": "تصنيف فرعي إن وجد",
    "sensitivity": "مستوى الحساسية: low أو medium أو high أو critical",
    "risk_notes": "ملاحظات عن المخاطر إن وجدت",
    "keywords": ["كلمة1", "كلمة2", "كلمة3"],
    "entities": {"names": [], "places": [], "teams": [], "brands": []},
    "summary_ar": "ملخص قصير بالعربي",
    "summary_en": "Short summary in English"
}

التصنيفات المتاحة: """ + ", ".join(CLASSIFIER_CATEGORIES) + """
مستويات الحساسية: """ + ", ".join(SENSITIVITY_LEVELS)

    def is_configured(self) -> bool:
        return bool(OPENAI_API_KEY)

    def _build_user_prompt(self, candidate: Candidate) -> str:
        """Build the user message for classification"""
        parts = []
        if candidate.title:
            parts.append(f"العنوان: {candidate.title}")
        if candidate.content:
            # Truncate long content
            content = candidate.content[:1500]
            parts.append(f"المحتوى: {content}")
        if candidate.keywords:
            parts.append(f"كلمات دلالية: {candidate.keywords}")
        if candidate.platforms:
            parts.append(f"المنصات: {candidate.platforms}")

        parts.append(f"التفاعلات: مشاهدات={candidate.views_total}, لايكات={candidate.likes_total}, مشاركات={candidate.reshares_total}, تعليقات={candidate.comments_total}")

        return "\n".join(parts)

    async def _classify_with_openai(self, prompt: str) -> dict:
        """Call OpenAI API for classification"""
        import aiohttp

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 800,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    print(f"[Classifier] OpenAI error {resp.status}: {error}")
                    return {}

                data = await resp.json()

                # Safely extract content from response
                try:
                    content = data["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError):
                    print(f"[Classifier] Unexpected OpenAI response structure: {str(data)[:300]}")
                    return {}

                # Parse JSON from response
                try:
                    # Handle potential markdown code blocks
                    if "```" in content:
                        content = content.split("```")[1]
                        if content.startswith("json"):
                            content = content[4:]
                    return json.loads(content.strip())
                except json.JSONDecodeError:
                    print(f"[Classifier] Failed to parse LLM response: {content[:200]}")
                    return {}

    def _fallback_classify(self, candidate: Candidate) -> dict:
        """Simple keyword-based fallback when OpenAI is unavailable"""
        title_lower = (candidate.title or "").lower()
        keywords_lower = (candidate.keywords or "").lower()
        combined = f"{title_lower} {keywords_lower}"

        category = "أخرى"
        keyword_map = {
            "سياسي": ["politics", "election", "government", "سياس", "انتخاب", "حكوم"],
            "رياضة": ["sport", "football", "soccer", "nba", "fifa", "رياض", "كرة", "دوري"],
            "ترفيه": ["entertainment", "movie", "music", "game", "ترفيه", "فيلم", "موسيقى", "لعب"],
            "تقنية": ["tech", "ai", "software", "apple", "google", "تقني", "ذكاء اصطناعي"],
            "اقتصاد": ["economy", "stock", "market", "crypto", "bitcoin", "اقتصاد", "سوق", "أسهم"],
            "صحة": ["health", "medical", "covid", "disease", "صح", "طب", "مرض"],
            "اجتماعي": ["social", "community", "trend", "viral", "اجتماع", "مجتمع"],
        }

        for cat, keywords in keyword_map.items():
            for kw in keywords:
                if kw in combined:
                    category = cat
                    break
            if category != "أخرى":
                break

        return {
            "category": category,
            "subcategory": None,
            "sensitivity": "low",
            "risk_notes": None,
            "keywords": (candidate.keywords or "").split(",")[:5],
            "entities": {"names": [], "places": [], "teams": [], "brands": []},
            "summary_ar": candidate.title or "",
            "summary_en": candidate.title or "",
        }

    async def classify(self, candidates: List[Candidate], db: Session) -> List[Classification]:
        """
        Classify HOT candidates.
        Uses OpenAI if available, falls back to keyword matching.
        Returns list of Classification records.
        """
        classifications = []

        for candidate in candidates:
            # Skip already classified candidates
            existing = (
                db.query(Classification)
                .filter(Classification.candidate_id == candidate.id)
                .first()
            )
            if existing:
                classifications.append(existing)
                continue

            if self.is_configured():
                prompt = self._build_user_prompt(candidate)
                result = await self._classify_with_openai(prompt)
            else:
                result = {}

            # Fallback if LLM failed or not configured
            if not result:
                print(f"[Classifier] Using fallback for candidate {candidate.id}")
                result = self._fallback_classify(candidate)

            classification = Classification(
                candidate_id=candidate.id,
                category=result.get("category", "أخرى"),
                subcategory=result.get("subcategory"),
                sensitivity=result.get("sensitivity", "low"),
                risk_notes=result.get("risk_notes"),
                extracted_keywords=",".join(result.get("keywords", [])) if isinstance(result.get("keywords"), list) else result.get("keywords", ""),
                entities=json.dumps(result.get("entities", {}), ensure_ascii=False),
                summary_ar=result.get("summary_ar"),
                summary_en=result.get("summary_en"),
                classified_at=datetime.now(timezone.utc),
            )
            db.add(classification)
            classifications.append(classification)

            # Update candidate status to fully processed
            candidate.status = "hot"

        if classifications:
            db.commit()

        print(f"[Classifier] Classified {len(classifications)} candidates")
        return classifications
