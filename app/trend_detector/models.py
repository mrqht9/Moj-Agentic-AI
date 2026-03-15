"""
Trend Detector Database Models
Tables: signals, candidates, x_validation, classifications, watchlist, scoring_config
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Boolean, Float, JSON
)
from datetime import datetime
from app.db.database import Base


class Signal(Base):
    """Raw signal collected from any platform before processing"""
    __tablename__ = "td_signals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    platform = Column(String(50), nullable=False, index=True)       # reddit, x, google_trends, tiktok
    source_id = Column(String(500), nullable=True, index=True)      # Original post/trend ID on the platform
    title = Column(String(1000), nullable=True)
    content = Column(Text, nullable=True)
    url = Column(String(2000), nullable=True)
    media_url = Column(String(2000), nullable=True)                 # Image/video URL if present
    media_text = Column(Text, nullable=True)                        # Text extracted from media via Vision API
    keywords = Column(Text, nullable=True)                          # Comma-separated keywords
    author = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    reshares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    raw_data = Column(JSON, nullable=True)                          # Full raw response from API
    has_media = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False, index=True)       # Whether it passed through normalizer
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Signal(id={self.id}, platform={self.platform}, title={self.title[:50] if self.title else ''})>"


class Candidate(Base):
    """Normalized, deduplicated signal ready for scoring and validation"""
    __tablename__ = "td_candidates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fingerprint = Column(String(64), unique=True, index=True)       # SHA-256 hash for dedup
    title = Column(String(1000), nullable=False)
    content = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)                          # Comma-separated
    url = Column(String(2000), nullable=True)                       # Best/primary URL
    media_url = Column(String(2000), nullable=True)
    platforms = Column(String(500), nullable=True)                  # Comma-separated platforms where seen
    source_signal_ids = Column(String(500), nullable=True)          # Comma-separated Signal IDs merged into this
    first_seen_at = Column(DateTime, nullable=True)
    views_total = Column(Integer, default=0)
    likes_total = Column(Integer, default=0)
    reshares_total = Column(Integer, default=0)
    comments_total = Column(Integer, default=0)
    platform_count = Column(Integer, default=1)                     # Number of platforms signal appears on
    score = Column(Float, default=0.0, index=True)                  # Score from scoring engine
    status = Column(String(50), default="pending", index=True)      # pending, validated, hot, early, not_yet, expired
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Candidate(id={self.id}, score={self.score}, status={self.status}, title={self.title[:50]})>"


class XValidation(Base):
    """Results from X platform validation checks"""
    __tablename__ = "td_x_validation"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    candidate_id = Column(Integer, nullable=False, index=True)
    search_query = Column(String(500), nullable=True)               # What was searched on X
    post_count = Column(Integer, default=0)                         # Number of recent posts found
    unique_authors = Column(Integer, default=0)                     # Distinct authors
    total_engagement = Column(Integer, default=0)                   # Sum of likes+retweets+replies
    post_density_per_hour = Column(Float, default=0.0)              # Posts per hour
    verdict = Column(String(50), nullable=False, index=True)        # HOT, EARLY, NOT_YET
    raw_data = Column(JSON, nullable=True)                          # Full search results
    checked_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<XValidation(id={self.id}, candidate_id={self.candidate_id}, verdict={self.verdict})>"


class Classification(Base):
    """LLM-based classification and enrichment results"""
    __tablename__ = "td_classifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    candidate_id = Column(Integer, nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)      # سياسي, رياضة, etc.
    subcategory = Column(String(100), nullable=True)
    sensitivity = Column(String(50), default="low")                 # low, medium, high, critical
    risk_notes = Column(Text, nullable=True)                        # Why it's sensitive
    extracted_keywords = Column(Text, nullable=True)                # LLM-extracted keywords
    entities = Column(Text, nullable=True)                          # Names, places, teams (JSON string)
    summary_ar = Column(Text, nullable=True)                        # Arabic summary
    summary_en = Column(Text, nullable=True)                        # English summary
    classified_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Classification(id={self.id}, candidate_id={self.candidate_id}, category={self.category})>"


class Watchlist(Base):
    """EARLY signals being monitored for re-validation"""
    __tablename__ = "td_watchlist"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    candidate_id = Column(Integer, nullable=False, index=True)
    check_count = Column(Integer, default=0)                        # How many times re-checked
    max_checks = Column(Integer, default=6)                         # Max before expiry
    next_check_at = Column(DateTime, nullable=False, index=True)    # When to re-check
    last_checked_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)           # False when graduated or expired
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Watchlist(id={self.id}, candidate_id={self.candidate_id}, checks={self.check_count}/{self.max_checks})>"


class ScoringConfig(Base):
    """Configurable scoring weights and thresholds (editable via admin)"""
    __tablename__ = "td_scoring_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    metric = Column(String(100), nullable=False, unique=True, index=True)   # views, likes, reshares, etc.
    weight = Column(Float, default=1.0)                                      # Points awarded
    platform = Column(String(50), nullable=True)                             # Platform-specific or null for global
    threshold = Column(Float, default=0.0)                                   # Value must exceed this
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ScoringConfig(metric={self.metric}, platform={self.platform}, weight={self.weight})>"
