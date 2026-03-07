#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
وكيل الترندات - Trend Agent
يتعامل مع استفسارات المستخدم عن الترندات من خلال الشات
يستخدم OpenAI لتحليل البيانات وتقديمها بشكل محادثة طبيعية
"""

import re
import json
import requests as http_requests
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta

from app.trend_detector.models import Signal, Candidate, Classification, Watchlist, XValidation
from app.core.config import settings

# Farsi-specific characters not used in Arabic
_FARSI_CHARS = re.compile(r'[\u06AF\u0686\u067E\u0698\u06A9]')  # گ چ پ ژ ک


def _is_farsi(text: str) -> bool:
    """Detect Farsi text by checking for Farsi-specific characters"""
    return bool(text and _FARSI_CHARS.search(text))


class TrendAgent:
    """وكيل الترندات — يحلل الترندات ويتحدث عنها بشكل طبيعي مع المستخدم"""

    SYSTEM_PROMPT = """أنت "موج" — محلل ترندات ذكي متخصص في تحليل المحتوى الرائج على منصات التواصل الاجتماعي في السعودية والعالم العربي.

مهمتك:
- تحلل بيانات الترندات المقدمة لك وتقدمها للمستخدم بأسلوب سهل وواضح
- تتحدث بالعربية (لهجة سعودية خفيفة مقبولة)
- تشرح للمستخدم ليش هالترند مهم أو رائج
- تعطي رأيك وتحليلك للترندات
- إذا سأل عن ترند معين، ابحث في البيانات وأعطه تحليل مفصل
- لا تكرر البيانات الخام — حللها وقدمها بشكل إنساني
- إذا ما فيه نتائج، اقترح عليه يسأل بطريقة ثانية
- إذا سأل عن مواضيع للكتابة أو تغريد، اقترح له بناءً على الترندات الحالية

أسلوبك:
- ودود ومختصر
- استخدم إيموجي بشكل خفيف
- ركز على المعلومة المفيدة
- إذا الترند سياسي أو حساس، كن محايد"""

    def __init__(self, llm_config: Dict[str, Any] = None):
        self.llm_config = llm_config
        self.openai_key = settings.OPENAI_API_KEY
        self.openai_model = settings.OPENAI_MODEL or "gpt-4"

    def process_request(self, message: str, context: Dict[str, Any], db: Session = None) -> Optional[str]:
        """معالجة طلب المستخدم المتعلق بالترندات"""
        if not db:
            return "⚠️ لا يمكن الوصول لقاعدة البيانات حالياً."

        intent = context.get("intent", "get_trends")

        # Gather data based on intent
        trend_data = self._gather_data(intent, message, context, db)

        # Try to use OpenAI for natural response
        if self.openai_key:
            try:
                result = self._ask_llm(message, trend_data)
                if result:
                    return result
            except Exception as e:
                print(f"[TrendAgent] LLM error: {e}")

        # Fallback to well-formatted conversational response
        return trend_data.get("formatted", "عذراً، ما قدرت أجيب بيانات الترندات حالياً.")

    def _gather_data(self, intent: str, message: str, context: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """جمع البيانات من قاعدة البيانات حسب نوع الطلب"""
        data: Dict[str, Any] = {"intent": intent, "user_message": message}
        data["stats"] = self._get_stats(db)

        if intent == "trend_detail":
            data["detail"] = self._get_trend_detail(message, db)
            data["formatted"] = self._format_detail(data)
        elif intent == "get_hot_trends":
            data["hot_trends"] = self._get_hot_list(db)
            data["early_trends"] = self._get_early_list(db, 5)
            data["formatted"] = self._format_hot(data)
        elif intent == "search_trends":
            query = self._extract_search_query(message, context)
            data["search_query"] = query
            data["search_results"] = self._search_db(db, query) if query else []
            data["formatted"] = self._format_search(data)
        elif intent == "run_trends":
            data["run_info"] = self._get_run_info(db)
            data["formatted"] = self._format_run(data)
        else:  # get_trends — overview
            data["top_trends"] = self._get_top_arabic(db, 10)
            data["hot_trends"] = self._get_hot_list(db)
            data["formatted"] = self._format_overview(data)

        return data

    # ── Data gathering helpers ─────────────────────────────────

    def _filter_arabic(self, candidates: List[Candidate]) -> List[Candidate]:
        """Filter out Farsi content, keep Arabic/English only"""
        return [c for c in candidates if not _is_farsi(c.title) and not _is_farsi(c.content)]

    def _get_stats(self, db: Session) -> Dict[str, Any]:
        cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        return {
            "total_signals": db.query(Signal).count(),
            "total_candidates": db.query(Candidate).count(),
            "hot": db.query(Candidate).filter(Candidate.status == "hot").count(),
            "early": db.query(Candidate).filter(Candidate.status == "early").count(),
            "not_yet": db.query(Candidate).filter(Candidate.status == "not_yet").count(),
            "watchlist": db.query(Watchlist).filter(Watchlist.is_active == True).count(),
            "signals_24h": db.query(Signal).filter(Signal.created_at >= cutoff_24h).count(),
            "validations": db.query(XValidation).count(),
            "platforms": {
                row[0]: row[1]
                for row in db.query(Signal.platform, func.count(Signal.id)).group_by(Signal.platform).all()
            },
        }

    def _get_hot_list(self, db: Session) -> List[Dict]:
        raw = db.query(Candidate).filter(Candidate.status == "hot").order_by(Candidate.score.desc()).limit(40).all()
        arabic = self._filter_arabic(raw)
        return [self._candidate_to_dict(c, db) for c in arabic[:20]]

    def _get_early_list(self, db: Session, limit: int = 5) -> List[Dict]:
        raw = db.query(Candidate).filter(Candidate.status == "early").order_by(Candidate.score.desc()).limit(limit * 3).all()
        arabic = self._filter_arabic(raw)
        return [self._candidate_to_dict(c, db) for c in arabic[:limit]]

    def _get_top_arabic(self, db: Session, limit: int = 10) -> List[Dict]:
        """Get top candidates, filtering out Farsi content"""
        raw = db.query(Candidate).order_by(Candidate.score.desc()).limit(limit * 3).all()
        arabic = self._filter_arabic(raw)
        return [self._candidate_to_dict(c, db) for c in arabic[:limit]]

    def _search_db(self, db: Session, query: str) -> List[Dict]:
        if not query:
            return []
        term = f"%{query}%"
        raw = (
            db.query(Candidate)
            .filter(
                (Candidate.title.ilike(term))
                | (Candidate.content.ilike(term))
                | (Candidate.keywords.ilike(term))
            )
            .order_by(Candidate.score.desc())
            .limit(30)
            .all()
        )
        arabic = self._filter_arabic(raw)
        return [self._candidate_to_dict(c, db) for c in arabic[:10]]

    def _get_run_info(self, db: Session) -> Dict[str, Any]:
        latest = db.query(Signal).order_by(Signal.created_at.desc()).first()
        return {
            "last_signal_time": latest.created_at.isoformat() if latest and latest.created_at else None,
            "total_validations": db.query(XValidation).count(),
        }

    def _candidate_to_dict(self, c: Candidate, db: Session) -> Dict:
        clf = db.query(Classification).filter(Classification.candidate_id == c.id).first()
        val = db.query(XValidation).filter(XValidation.candidate_id == c.id).order_by(XValidation.id.desc()).first()
        # Clean title — remove t.co URLs and excess whitespace
        title = (c.title or "").strip()
        title = re.sub(r'https?://t\.co/\S+', '', title).strip()
        title = re.sub(r'\s+', ' ', title)
        return {
            "title": title,
            "score": c.score,
            "status": c.status,
            "platforms": c.platforms,
            "category": clf.category if clf else None,
            "keywords": c.keywords,
            "engagement": {
                "views": c.views_total,
                "likes": c.likes_total,
                "reshares": c.reshares_total,
                "comments": c.comments_total,
            },
            "x_validation": {
                "post_count": val.post_count,
                "unique_authors": val.unique_authors,
                "total_engagement": val.total_engagement,
                "density": val.post_density_per_hour,
                "verdict": val.verdict,
            } if val else None,
        }

    def _extract_search_query(self, message: str, context: Dict[str, Any]) -> str:
        """استخراج كلمة البحث من رسالة المستخدم"""
        raw = context.get("raw_text", message).strip()
        prefixes = [
            "ابحث عن ترند", "ابحث ترند", "بحث ترند", "بحث عن ترند",
            "هل يتصدر", "هل ترند", "search trend", "search trends",
            "ترند ", "ترندات ",
        ]
        lower = raw
        for p in prefixes:
            if lower.startswith(p):
                return lower[len(p):].strip()
        stop_words = {"وش", "ايش", "شو", "عن", "في", "هل", "ترند", "ترندات", "الترند", "الترندات", "ابحث", "بحث", "الان", "الحين", "اليوم"}
        words = [w for w in raw.split() if w not in stop_words]
        return " ".join(words).strip()

    # ── Trend detail ─────────────────────────────────────────────

    def _extract_title_fragment(self, message: str) -> str:
        """Extract the trend title fragment from user's message for detail lookup"""
        text = message.strip()
        # Remove numbering prefix like "9. 🔥" or "2. 🔄" (handle all emoji)
        text = re.sub(r'^\d+\.\s*', '', text)
        # Remove leading emoji (any Unicode emoji character)
        text = re.sub(r'^[\U0001F300-\U0001FAD6\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u27BF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\u200d\ufe0f]+\s*', '', text)
        # Remove engagement suffix like "— ❤️ 54,470 🔁 20,947" or "— 📊 28,471 تفاعل على X"
        text = re.sub(r'\s*—\s*.*$', '', text)
        # Remove hashtag prefix #
        text = re.sub(r'^#', '', text)
        # Remove common question prefixes/suffixes
        for phrase in ["هذا الخبر تقدر تكمله لي", "تقدر تكمله لي", "هذا الخبر", "كمل لي", "تكمله لي",
                        "اكمل لي", "فصل لي", "هذا الترند", "هذي التغريده", "هذي التغريدة",
                        "عن هذا", "وش يعني", "تفاصيل", "شرح", "تحليل", "فصل", "كمل",
                        "عطني تفاصيل عن", "وش قصة", "ابي تفاصيل", "؟", "?"]:
            text = text.replace(phrase, "")
        # Remove t.co URLs
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _get_trend_detail(self, message: str, db: Session) -> Optional[Dict]:
        """Find a specific trend by fuzzy title match and return full details"""
        fragment = self._extract_title_fragment(message)
        if not fragment or len(fragment) < 3:
            return None

        candidate = None

        # Strategy 1: search full fragment in title or content
        term = f"%{fragment[:80]}%"
        candidate = (
            db.query(Candidate)
            .filter(
                (Candidate.title.ilike(term)) | (Candidate.content.ilike(term))
            )
            .order_by(Candidate.score.desc())
            .first()
        )

        # Strategy 2: try progressively shorter word windows
        if not candidate:
            words = fragment.split()
            for length in [5, 4, 3, 2]:
                if len(words) >= length:
                    short_term = f"%{' '.join(words[:length])}%"
                    candidate = (
                        db.query(Candidate)
                        .filter(
                            (Candidate.title.ilike(short_term)) | (Candidate.content.ilike(short_term))
                        )
                        .order_by(Candidate.score.desc())
                        .first()
                    )
                    if candidate:
                        break

        # Strategy 3: try each significant word individually (at least 4 chars)
        if not candidate:
            words = fragment.split()
            sig_words = [w for w in words if len(w) >= 4 and w not in {'عاجل', 'بيان', 'تعلن', 'أعلن', 'أعلنت'}]
            if sig_words:
                # Use the longest significant word
                longest = max(sig_words, key=len)
                candidate = (
                    db.query(Candidate)
                    .filter(
                        (Candidate.title.ilike(f"%{longest}%")) | (Candidate.content.ilike(f"%{longest}%"))
                    )
                    .order_by(Candidate.score.desc())
                    .first()
                )

        if not candidate:
            return None

        # Get full details
        clf = db.query(Classification).filter(Classification.candidate_id == candidate.id).first()
        val = db.query(XValidation).filter(XValidation.candidate_id == candidate.id).order_by(XValidation.id.desc()).first()

        # Get source signals for this candidate
        source_signals = []
        if candidate.source_signal_ids:
            sig_ids = [int(x.strip()) for x in candidate.source_signal_ids.split(",") if x.strip().isdigit()]
            if sig_ids:
                signals = db.query(Signal).filter(Signal.id.in_(sig_ids)).all()
                for s in signals:
                    source_signals.append({
                        "platform": s.platform,
                        "author": s.author,
                        "title": (s.title or ""),
                        "content": (s.content or ""),
                        "url": s.url,
                        "published_at": s.published_at.isoformat() if s.published_at else None,
                        "likes": s.likes,
                        "reshares": s.reshares,
                        "comments": s.comments,
                        "views": s.views,
                    })

        # Full title and content (not truncated)
        full_title = re.sub(r'\s+', ' ', (candidate.title or "")).strip()
        full_content = re.sub(r'\s+', ' ', (candidate.content or "")).strip()

        return {
            "id": candidate.id,
            "title": full_title,
            "content": full_content,
            "keywords": candidate.keywords,
            "url": candidate.url,
            "platforms": candidate.platforms,
            "score": candidate.score,
            "status": candidate.status,
            "first_seen": candidate.first_seen_at.isoformat() if candidate.first_seen_at else None,
            "engagement": {
                "views": candidate.views_total or 0,
                "likes": candidate.likes_total or 0,
                "reshares": candidate.reshares_total or 0,
                "comments": candidate.comments_total or 0,
            },
            "classification": {
                "category": clf.category if clf else None,
                "subcategory": clf.subcategory if clf else None,
                "sensitivity": clf.sensitivity if clf else None,
                "summary_ar": clf.summary_ar if clf else None,
                "summary_en": clf.summary_en if clf else None,
                "entities": clf.entities if clf else None,
            } if clf else None,
            "x_validation": {
                "post_count": val.post_count,
                "unique_authors": val.unique_authors,
                "total_engagement": val.total_engagement,
                "density": val.post_density_per_hour,
                "verdict": val.verdict,
            } if val else None,
            "source_signals": source_signals,
        }

    # ── OpenAI integration ─────────────────────────────────────

    def _ask_llm(self, user_message: str, trend_data: Dict[str, Any]) -> Optional[str]:
        """إرسال البيانات للذكاء الاصطناعي ليحللها ويرد بشكل طبيعي"""
        data_summary = json.dumps(trend_data, ensure_ascii=False, default=str)
        if len(data_summary) > 6000:
            data_summary = data_summary[:6000] + "..."

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"بيانات الترندات:\n```json\n{data_summary}\n```\n\nسؤال المستخدم: {user_message}"},
        ]

        try:
            resp = http_requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.openai_model,
                    "messages": messages,
                    "max_tokens": 1000,
                    "temperature": 0.7,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                print(f"[TrendAgent] OpenAI error {resp.status_code}: {resp.text[:200]}")
                return None
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[TrendAgent] OpenAI request failed: {e}")
            return None

    # ── Conversational formatters (fallback when OpenAI unavailable) ─────

    def _generate_context(self, t: Dict) -> str:
        """Generate a brief contextual analysis line for a trend based on its data"""
        hints = []
        cat = t.get("category") or ""
        keywords = (t.get("keywords") or "").lower()
        title = (t.get("title") or "").lower()
        status = t.get("status", "")
        eng = t.get("engagement", {})
        total_eng = (eng.get("likes", 0) or 0) + (eng.get("reshares", 0) or 0) + (eng.get("comments", 0) or 0)
        xval = t.get("x_validation")
        if xval:
            total_eng = max(total_eng, xval.get("total_engagement", 0) or 0)

        # Category-based context
        if cat:
            cat_labels = {
                "politics": "سياسي", "sports": "رياضي", "entertainment": "ترفيهي",
                "technology": "تقني", "economy": "اقتصادي", "social": "اجتماعي",
                "religion": "ديني", "health": "صحي", "education": "تعليمي",
                "security": "أمني", "military": "عسكري",
            }
            label = cat_labels.get(cat.lower(), cat)
            hints.append(f"📂 {label}")

        # Engagement-based context
        if total_eng >= 50000:
            hints.append("انتشار واسع جداً")
        elif total_eng >= 20000:
            hints.append("تفاعل كبير")
        elif total_eng >= 5000:
            hints.append("تفاعل ملحوظ")

        # Keyword/title-based context hints
        if any(w in title for w in ["عاجل", "عاجلة", "breaking"]):
            hints.append("خبر عاجل")
        if any(w in title for w in ["بيان", "تصريح", "أعلن", "تعلن"]):
            hints.append("بيان رسمي")
        if any(w in title for w in ["هجوم", "اعتداء", "استهداف", "مسيّر", "مسيرة", "صاروخ"]):
            hints.append("حدث أمني")
        if any(w in title for w in ["إدانة", "رفض", "استنكار", "يدين", "ترفض"]):
            hints.append("موقف دبلوماسي")
        if any(w in title for w in ["السعودية", "المملكة", "سعودي"]):
            hints.append("يخص المملكة")

        # X validation context
        if xval:
            authors = xval.get("unique_authors", 0) or 0
            density = xval.get("density", 0) or 0
            if authors >= 20:
                hints.append(f"{authors} كاتب مختلف")
            if density >= 10:
                hints.append(f"نشر مكثف ({density:.0f}/ساعة)")

        if status == "hot":
            hints.append("🔥 حار الحين")

        return " · ".join(hints[:4]) if hints else ""

    def _trend_line(self, t: Dict, idx: int) -> str:
        """Format a single trend as a readable line"""
        icon = {"hot": "🔥", "early": "⏳", "not_yet": "📌", "pending": "🔄"}.get(t["status"], "📌")
        title = t["title"][:80]
        # Add engagement info if available
        eng = t.get("engagement", {})
        likes = eng.get("likes", 0) or 0
        reshares = eng.get("reshares", 0) or 0
        eng_str = ""
        if likes + reshares > 0:
            eng_str = f" — ❤️ {likes:,} 🔁 {reshares:,}"
        xval = t.get("x_validation")
        if xval and xval.get("total_engagement", 0) > 0:
            eng_str = f" — 📊 {xval['total_engagement']:,} تفاعل على X"
        return f"{idx}. {icon} {title}{eng_str}"

    def _format_overview(self, data: Dict) -> str:
        s = data["stats"]
        top = data.get("top_trends", [])
        hots = data.get("hot_trends", [])

        msg = f"هلا! هذي آخر الترندات اللي رصدناها 👇\n\n"

        if hots:
            msg += f"🔥 **ترندات حارة الحين ({len(hots)}):**\n"
            for i, t in enumerate(hots[:5], 1):
                msg += self._trend_line(t, i) + "\n"
                ctx = self._generate_context(t)
                if ctx:
                    msg += f"   ↳ {ctx}\n"
            msg += "\n"

        if top:
            shown = top[:7] if not hots else top[:5]
            msg += f"📋 **أبرز المواضيع المتداولة:**\n"
            for i, t in enumerate(shown, 1):
                msg += self._trend_line(t, i) + "\n"
                ctx = self._generate_context(t)
                if ctx:
                    msg += f"   ↳ {ctx}\n"
            msg += "\n"

        msg += f"📡 رصدنا {s['signals_24h']:,} إشارة آخر 24 ساعة من {len(s['platforms'])} مصادر\n"
        msg += f"👁 {s['watchlist']} ترند تحت المراقبة\n\n"
        msg += "💡 تقدر تسألني:\n"
        msg += "• \"ترند السعودية\" — بحث محدد\n"
        msg += "• \"ترندات حارة\" — الأكثر رواجاً\n"
        msg += "• انسخ أي ترند من القائمة وأرسله — أعطيك تفاصيل وتحليل"
        return msg

    def _format_hot(self, data: Dict) -> str:
        hots = data.get("hot_trends", [])
        early = data.get("early_trends", [])

        if not hots and not early:
            return "🔥 ما فيه ترندات حارة حالياً. النظام يراقب باستمرار — أعطيني دقايق وارجع اسألني."

        msg = ""
        if hots:
            msg += f"🔥 **الترندات الحارة ({len(hots)}):**\n\n"
            for i, t in enumerate(hots, 1):
                msg += self._trend_line(t, i) + "\n"
        else:
            msg += "🔥 ما فيه ترندات وصلت مرحلة HOT بعد.\n\n"

        if early:
            msg += f"\n⏳ **قريب توصل HOT:**\n"
            for i, t in enumerate(early, 1):
                msg += self._trend_line(t, i) + "\n"
            msg += "\n� هذي تحت المراقبة — لو زاد التفاعل عليها بتصير حارة"

        return msg

    def _format_search(self, data: Dict) -> str:
        q = data.get("search_query", "")
        results = data.get("search_results", [])

        if not q:
            return "🔍 وش تبي تبحث عنه؟ اكتب مثلاً: \"ترند الرياض\" أو \"ابحث ترند رمضان\""

        if not results:
            return f"🔍 ما لقيت شي عن \"{q}\" في الترندات الحالية.\n\n💡 جرب:\n• كلمة أقصر أو مختلفة\n• النظام يجمع ترندات جديدة كل 10 دقائق"

        msg = f"🔍 **لقيت {len(results)} نتيجة عن \"{q}\":**\n\n"
        for i, t in enumerate(results, 1):
            msg += self._trend_line(t, i) + "\n"
        return msg

    def _format_detail(self, data: Dict) -> str:
        """Format full trend detail in a conversational way with analysis"""
        d = data.get("detail")
        if not d:
            return "🔍 ما قدرت ألقى هالترند في قاعدة البيانات. جرب تنسخ عنوانه أو كلمة رئيسية منه."

        icon = {"hot": "🔥", "early": "⏳", "not_yet": "📌", "pending": "🔄"}.get(d["status"], "📌")
        eng = d.get("engagement", {})

        msg = f"{icon} **تفاصيل الترند:**\n\n"
        msg += f"📌 **العنوان:**\n{d['title']}\n\n"

        if d.get("content") and d["content"] != d["title"]:
            msg += f"📝 **المحتوى الكامل:**\n{d['content']}\n\n"

        # ── Analysis section ──
        analysis = self._build_analysis(d)
        if analysis:
            msg += f"🧠 **التحليل:**\n{analysis}\n\n"

        msg += f"📊 **الأرقام:**\n"
        msg += f"• النقاط: {d['score']}\n"
        msg += f"• الحالة: {d['status'].upper()}\n"
        views = eng.get("views", 0) or 0
        likes = eng.get("likes", 0) or 0
        reshares = eng.get("reshares", 0) or 0
        comments = eng.get("comments", 0) or 0
        if views > 0:
            msg += f"• 👁 المشاهدات: {views:,}\n"
        if likes > 0:
            msg += f"• ❤️ الإعجابات: {likes:,}\n"
        if reshares > 0:
            msg += f"• 🔁 إعادة النشر: {reshares:,}\n"
        if comments > 0:
            msg += f"• 💬 التعليقات: {comments:,}\n"

        xval = d.get("x_validation")
        if xval:
            msg += f"\n🔍 **تحقق X:**\n"
            msg += f"• عدد التغريدات: {xval['post_count']}\n"
            msg += f"• كتّاب مختلفين: {xval['unique_authors']}\n"
            msg += f"• إجمالي التفاعل: {xval['total_engagement']:,}\n"
            msg += f"• كثافة النشر: {xval['density']}/ساعة\n"
            msg += f"• الحكم: {xval['verdict']}\n"

        clf = d.get("classification")
        if clf:
            if clf.get("category"):
                msg += f"\n📂 **التصنيف:** {clf['category']}"
                if clf.get("subcategory"):
                    msg += f" > {clf['subcategory']}"
                msg += "\n"
            if clf.get("sensitivity") and clf["sensitivity"] != "low":
                msg += f"⚠️ **الحساسية:** {clf['sensitivity']}\n"
            if clf.get("summary_ar"):
                msg += f"\n📋 **الملخص:**\n{clf['summary_ar']}\n"

        if d.get("keywords"):
            msg += f"\n🏷 **كلمات مفتاحية:** {d['keywords']}\n"

        if d.get("url"):
            msg += f"\n🔗 **الرابط:** {d['url']}\n"

        if d.get("platforms"):
            msg += f"📡 **المنصات:** {d['platforms']}\n"

        # Source signals — show all
        sources = d.get("source_signals", [])
        if sources:
            msg += f"\n📰 **المصادر ({len(sources)}):**\n"
            for i, s in enumerate(sources, 1):
                author = s.get("author") or "مجهول"
                plat = s.get("platform") or "?"
                msg += f"  {i}. @{author} ({plat})"
                s_likes = s.get("likes", 0) or 0
                s_reshares = s.get("reshares", 0) or 0
                s_views = s.get("views", 0) or 0
                if s_likes + s_reshares + s_views > 0:
                    msg += f" — 👁 {s_views:,} ❤️ {s_likes:,} 🔁 {s_reshares:,}"
                if s.get("content"):
                    msg += f"\n     📝 {s['content']}"
                if s.get("url"):
                    msg += f"\n     🔗 {s['url']}"
                if s.get("published_at"):
                    msg += f"\n     🕐 {s['published_at']}"
                msg += "\n"

        msg += "\n💡 تقدر تسألني عن أي ترند ثاني أو تقول \"وش الترندات\" لعرض القائمة"
        return msg

    def _build_analysis(self, d: Dict) -> str:
        """Build a comprehensive analysis explaining HOW and WHY this post became a trend"""
        title = (d.get("title") or "")
        title_lower = title.lower()
        status = d.get("status", "")
        eng = d.get("engagement", {})
        views = eng.get("views", 0) or 0
        likes = eng.get("likes", 0) or 0
        reshares = eng.get("reshares", 0) or 0
        comments = eng.get("comments", 0) or 0
        total_eng = likes + reshares + comments
        xval = d.get("x_validation")
        clf = d.get("classification")
        first_seen = d.get("first_seen")
        score = d.get("score", 0)
        sources = d.get("source_signals", [])
        platforms = d.get("platforms", "")
        keywords = d.get("keywords", "")

        sections = []

        # ═══ Section 1: WHY did this become a trend? ═══
        why_lines = []

        # Topic analysis
        topic_type = None
        if any(w in title_lower for w in ["بيان", "تعرب", "تدين", "تستنكر", "إدانة", "رفض", "استنكار"]):
            topic_type = "official_statement"
            why_lines.append("هذا بيان رسمي حكومي — البيانات الرسمية تنتشر بسرعة لأنها تعكس موقف الدولة وتأتي كردة فعل على أحداث مهمة تشغل الرأي العام.")
        if any(w in title_lower for w in ["هجوم", "اعتداء", "استهداف", "مسيّر", "مسيرة", "صاروخ", "اعتراض", "سفارة", "مصفاة"]):
            topic_type = "security"
            why_lines.append("حدث أمني/عسكري — الأخبار الأمنية تولّد تفاعل عالي جداً لأنها تمس أمن المواطنين مباشرة وتستدعي متابعة فورية من الجمهور والإعلام.")
        if any(w in title_lower for w in ["عاجل", "عاجلة", "breaking"]):
            why_lines.append("تم تصنيفه كخبر عاجل — الأخبار العاجلة تنتشر كالنار في الهشيم لأن الناس تتسابق لمشاركتها ومعرفة تفاصيلها.")
        if any(w in title_lower for w in ["إيران", "ايران", "إيراني", "الإيراني"]):
            why_lines.append("الموضوع يتعلق بإيران — القضايا الإيرانية حساسة إقليمياً وتثير نقاش واسع خصوصاً في الخليج العربي.")
        if any(w in title_lower for w in ["السعودية", "المملكة", "سعودي", "الرياض"]):
            why_lines.append("يخص المملكة العربية السعودية — المواضيع السعودية تحظى باهتمام كبير من الجمهور العربي على منصات التواصل.")
        if any(w in title_lower for w in ["الكويت", "كويتي", "البحرين", "بحريني", "الإمارات", "إماراتي", "قطر", "عمان"]):
            why_lines.append("يتعلق بدول الخليج — المواضيع الخليجية المشتركة تحظى بتفاعل عابر للحدود.")

        if not why_lines:
            # Generic topic analysis from keywords/category
            if clf and clf.get("category"):
                cat = clf["category"]
                cat_explanations = {
                    "politics": "موضوع سياسي — السياسة دائماً تجذب نقاش واسع وآراء متباينة.",
                    "sports": "موضوع رياضي — الرياضة تحرك مشاعر الجمهور وتولّد تفاعل كبير.",
                    "entertainment": "موضوع ترفيهي — المحتوى الترفيهي ينتشر بسرعة لأن الناس تحب مشاركته.",
                    "technology": "موضوع تقني — الأخبار التقنية تجذب شريحة واسعة من المهتمين.",
                    "economy": "موضوع اقتصادي — الأخبار الاقتصادية تهم شريحة كبيرة لتأثيرها المباشر على الحياة.",
                    "social": "موضوع اجتماعي — القضايا الاجتماعية تثير النقاش والتعاطف.",
                    "security": "موضوع أمني — يمس أمن الناس مباشرة ويستدعي متابعة.",
                }
                why_lines.append(cat_explanations.get(cat.lower(), f"مصنف كموضوع ({cat}) — يلامس اهتمامات شريحة واسعة."))

        if why_lines:
            sections.append("**ليش صار ترند:**\n" + "\n".join(f"• {l}" for l in why_lines))

        # ═══ Section 2: HOW did it spread? ═══
        how_lines = []

        # Timing
        if first_seen:
            try:
                dt = datetime.fromisoformat(first_seen)
                age = datetime.now(timezone.utc) - dt
                hours = age.total_seconds() / 3600
                if hours < 1:
                    how_lines.append(f"أول رصد: من أقل من ساعة — طالع توه وصاعد بقوة.")
                elif hours < 3:
                    how_lines.append(f"أول رصد: من {hours:.0f} ساعة تقريباً — خبر طازج والتفاعل في ذروته.")
                elif hours < 12:
                    how_lines.append(f"أول رصد: من {hours:.0f} ساعات — ما زال يتصدر يعني عنده زخم حقيقي مو مجرد موجة عابرة.")
                elif hours < 24:
                    how_lines.append(f"أول رصد: من {hours:.0f} ساعة — ترند مستمر لأكثر من نصف يوم، يعني الموضوع مهم فعلاً.")
                else:
                    days = hours / 24
                    how_lines.append(f"أول رصد: من {days:.1f} يوم — ترند ثابت، الموضوع ما راح يروح بسرعة.")
            except:
                pass

        # Engagement breakdown
        if total_eng > 0 or views > 0:
            eng_parts = []
            if views > 0:
                eng_parts.append(f"شافوه {views:,} شخص")
            if likes > 0:
                eng_parts.append(f"أعجب {likes:,}")
            if reshares > 0:
                eng_parts.append(f"أعاد نشره {reshares:,}")
            if comments > 0:
                eng_parts.append(f"علّق عليه {comments:,}")
            how_lines.append("التفاعل: " + " | ".join(eng_parts) + ".")

            # Explain the engagement pattern
            if reshares > 0 and likes > 0:
                ratio = reshares / likes if likes > 0 else 0
                if ratio > 0.5:
                    how_lines.append(f"نسبة إعادة النشر للإعجابات عالية ({ratio:.1f}) — يعني الناس مو بس معجبين، هم يبون ينشرونه وهذا اللي يخلي الترند ينتشر.")
                elif ratio > 0.2:
                    how_lines.append(f"نسبة المشاركة جيدة — الناس تتفاعل وتعيد نشره.")

        # X validation details
        if xval:
            authors = xval.get("unique_authors", 0) or 0
            density = xval.get("density", 0) or 0
            x_eng = xval.get("total_engagement", 0) or 0
            post_count = xval.get("post_count", 0) or 0
            verdict = xval.get("verdict", "")

            if post_count > 0:
                how_lines.append(f"على X (تويتر): لقينا {post_count} تغريدة من {authors} كاتب مختلف — ")
                if authors >= 20:
                    how_lines[-1] += "تنوع الكتّاب كبير يعني الموضوع وصل لشرائح مختلفة مو بس حسابات معينة."
                elif authors >= 8:
                    how_lines[-1] += "عدد كتّاب جيد يدل على انتشار حقيقي."
                elif authors >= 3:
                    how_lines[-1] += "بداية انتشار بين كتّاب مختلفين."
                else:
                    how_lines[-1] += "عدد الكتّاب قليل لكن التفاعل عوّض ذلك."

            if density > 0:
                if density >= 10:
                    how_lines.append(f"كثافة النشر: {density:.1f} تغريدة/ساعة — نشر مكثف جداً، الموضوع يسيطر على التايملاين.")
                elif density >= 4:
                    how_lines.append(f"كثافة النشر: {density:.1f} تغريدة/ساعة — معدل نشر عالي يدل على اهتمام مستمر.")
                elif density >= 1:
                    how_lines.append(f"كثافة النشر: {density:.1f} تغريدة/ساعة — نشر منتظم.")

            if verdict == "HOT":
                how_lines.append("حكم النظام: HOT 🔥 — وصل لكل معايير الترند الحار (تفاعل + تنوع كتّاب + كثافة نشر).")
            elif verdict == "EARLY":
                how_lines.append("حكم النظام: EARLY ⏳ — بوادر ترند لكن ما وصل بعد لمرحلة HOT.")

        # Platform spread
        if platforms:
            plat_list = [p.strip() for p in platforms.split(",") if p.strip()]
            if len(plat_list) > 1:
                how_lines.append(f"الانتشار عبر المنصات: موجود على {', '.join(plat_list)} — الترند اللي ينتشر على أكثر من منصة يكون أقوى وأكثر ثباتاً.")

        if how_lines:
            sections.append("**كيف وصل ترند:**\n" + "\n".join(f"• {l}" for l in how_lines))

        # ═══ Section 3: Score explanation ═══
        if score > 0:
            score_line = f"**درجة الترند: {score}/10**\n"
            if score >= 9:
                score_line += "درجة عالية جداً — هذا من أقوى الترندات الحالية."
            elif score >= 7:
                score_line += "درجة عالية — ترند قوي ويستحق المتابعة."
            elif score >= 5:
                score_line += "درجة متوسطة — موضوع متداول لكن مو من الأقوى."
            else:
                score_line += "درجة منخفضة — لسه ما وصل لمرحلة ترند قوي."
            sections.append(score_line)

        # ═══ Section 4: Sensitivity & Classification ═══
        if clf:
            if clf.get("sensitivity") and clf["sensitivity"] not in ["low", None]:
                sections.append(f"⚠️ **تنبيه:** الموضوع مصنف حساسية \"{clf['sensitivity']}\" — ينصح بالحذر عند كتابة محتوى عنه أو التفاعل معه.")

        # ═══ Section 5: Recommendation ═══
        rec_lines = []
        if status == "hot":
            rec_lines.append("هالترند حار الحين — لو تبي تكتب محتوى عنه أو تتفاعل معه، هذا أفضل وقت.")
            if topic_type == "security":
                rec_lines.append("بما إنه حدث أمني، ركّز على نقل المعلومة بدقة من مصادر رسمية.")
            elif topic_type == "official_statement":
                rec_lines.append("بما إنه بيان رسمي، ممكن تقتبس منه مباشرة وتضيف تحليلك.")
            if total_eng >= 20000:
                rec_lines.append("التفاعل كبير — لو نزّلت محتوى الحين فيه فرصة يوصل لجمهور واسع.")
        elif status == "early":
            rec_lines.append("هالترند في بداياته — لو تبي تسبق غيرك هذا الوقت المثالي.")
            rec_lines.append("راقبه — لو زاد التفاعل خلال الساعات الجاية بيصير HOT.")
        elif status == "not_yet":
            rec_lines.append("الموضوع متداول لكن ما وصل لمرحلة ترند بعد — ممكن تراقبه.")

        if rec_lines:
            sections.append("**💡 توصية:**\n" + "\n".join(f"• {l}" for l in rec_lines))

        return "\n\n".join(sections) if sections else ""

    def _format_run(self, data: Dict) -> str:
        s = data["stats"]
        r = data.get("run_info", {})
        last = r.get("last_signal_time", "")
        if last:
            try:
                dt = datetime.fromisoformat(last)
                last = dt.strftime("%I:%M %p")
            except:
                pass

        return f"""⚙️ **النظام شغال ويراقب!**

📊 جمعنا {s['total_signals']:,} إشارة من {len(s['platforms'])} منصة
🔍 سوينا {s['validations']:,} عملية تحقق على X
🔥 {s['hot']} ترند حار — ⏳ {s['early']} مبكر
👁 {s['watchlist']} ترند تحت المراقبة
📡 آخر جمع بيانات: {last or 'جاري...'}

⏱ **الجدول الآلي:**
• X: كل 10 دقائق
• Google Trends: كل 30 دقيقة
• إعادة فحص: كل 15 دقيقة"""
