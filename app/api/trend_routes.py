"""
Trend Detector REST API
Pure API endpoints for collecting, searching, filtering, and managing trend signals.

Endpoints:
  GET  /api/trends/search         — Full-text search across candidates
  GET  /api/trends/candidates     — List/filter candidates
  GET  /api/trends/candidates/:id — Get candidate full detail
  GET  /api/trends/hot            — Quick list of HOT trends only
  GET  /api/trends/signals        — List raw signals
  GET  /api/trends/stats          — Aggregated statistics
  GET  /api/trends/categories     — List all classification categories
  GET  /api/trends/watchlist      — Active watchlist entries
  POST /api/trends/run            — Manually trigger collection pipeline
  POST /api/trends/run/all        — Trigger all configured collectors
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.db.database import get_db
from app.auth.dependencies import require_current_user
from app.db.models import User
from app.trend_detector.models import (
    Signal, Candidate, XValidation, Classification, Watchlist
)
from app.trend_detector.scheduler.scheduler import trend_scheduler

router = APIRouter(prefix="/api/trends", tags=["Trend Detector"])


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _serialize_candidate(c: Candidate, classification: Classification = None) -> dict:
    """Serialize a Candidate to a dict"""
    result = {
        "id": c.id,
        "title": c.title,
        "content": (c.content or "")[:500],
        "keywords": c.keywords,
        "url": c.url,
        "media_url": c.media_url,
        "platforms": c.platforms,
        "platform_count": c.platform_count,
        "score": c.score,
        "status": c.status,
        "views_total": c.views_total,
        "likes_total": c.likes_total,
        "reshares_total": c.reshares_total,
        "comments_total": c.comments_total,
        "first_seen_at": c.first_seen_at.isoformat() if c.first_seen_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
    if classification:
        result["classification"] = {
            "category": classification.category,
            "subcategory": classification.subcategory,
            "sensitivity": classification.sensitivity,
            "risk_notes": classification.risk_notes,
            "summary_ar": classification.summary_ar,
            "summary_en": classification.summary_en,
            "entities": classification.entities,
            "extracted_keywords": classification.extracted_keywords,
        }
    else:
        result["classification"] = None
    return result


def _serialize_signal(s: Signal) -> dict:
    """Serialize a Signal to a dict"""
    return {
        "id": s.id,
        "platform": s.platform,
        "source_id": s.source_id,
        "title": s.title,
        "content": (s.content or "")[:500],
        "url": s.url,
        "media_url": s.media_url,
        "media_text": (s.media_text or "")[:300],
        "keywords": s.keywords,
        "author": s.author,
        "views": s.views,
        "likes": s.likes,
        "reshares": s.reshares,
        "comments": s.comments,
        "has_media": s.has_media,
        "is_processed": s.is_processed,
        "published_at": s.published_at.isoformat() if s.published_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# ─── Search ────────────────────────────────────────────────────────────────────

@router.get("/search")
async def search_trends(
    q: str = Query(..., min_length=1, description="Search query — matches title, content, keywords"),
    status: Optional[str] = Query(None, description="Filter: hot, early, not_yet, pending, expired"),
    category: Optional[str] = Query(None, description="Filter by classification category"),
    platform: Optional[str] = Query(None, description="Filter by source platform"),
    sensitivity: Optional[str] = Query(None, description="Filter: low, medium, high, critical"),
    min_score: Optional[float] = Query(None, description="Minimum score threshold"),
    sort_by: str = Query("score", description="Sort by: score, date, likes, views, reshares"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """
    Full-text search across trend candidates.
    Searches title, content, and keywords. Supports filtering and sorting.
    """
    search_term = f"%{q}%"
    query = db.query(Candidate).filter(
        or_(
            Candidate.title.ilike(search_term),
            Candidate.content.ilike(search_term),
            Candidate.keywords.ilike(search_term),
        )
    )

    if status:
        query = query.filter(Candidate.status == status)
    if platform:
        query = query.filter(Candidate.platforms.ilike(f"%{platform}%"))
    if min_score is not None:
        query = query.filter(Candidate.score >= min_score)

    # Category/sensitivity filtering requires join with Classification
    if category or sensitivity:
        classified_ids = db.query(Classification.candidate_id)
        if category:
            classified_ids = classified_ids.filter(Classification.category == category)
        if sensitivity:
            classified_ids = classified_ids.filter(Classification.sensitivity == sensitivity)
        query = query.filter(Candidate.id.in_(classified_ids.subquery()))

    # Sorting
    sort_map = {
        "score": Candidate.score.desc(),
        "date": Candidate.created_at.desc(),
        "likes": Candidate.likes_total.desc(),
        "views": Candidate.views_total.desc(),
        "reshares": Candidate.reshares_total.desc(),
    }
    query = query.order_by(sort_map.get(sort_by, Candidate.score.desc()))

    total = query.count()
    candidates = query.offset(offset).limit(limit).all()

    results = []
    for c in candidates:
        clf = db.query(Classification).filter(Classification.candidate_id == c.id).first()
        results.append(_serialize_candidate(c, clf))

    return {"query": q, "total": total, "offset": offset, "limit": limit, "results": results}


# ─── List Candidates ───────────────────────────────────────────────────────────

@router.get("/candidates")
async def list_candidates(
    status: Optional[str] = Query(None, description="Filter: hot, early, not_yet, pending, expired"),
    category: Optional[str] = Query(None, description="Filter by classification category"),
    platform: Optional[str] = Query(None, description="Filter by source platform"),
    min_score: Optional[float] = Query(None, description="Minimum score"),
    hours: Optional[int] = Query(None, description="Only trends from last N hours"),
    sort_by: str = Query("score", description="Sort: score, date, likes, views"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """List trend candidates with filters, sorting, and pagination"""
    query = db.query(Candidate)

    if status:
        query = query.filter(Candidate.status == status)
    if platform:
        query = query.filter(Candidate.platforms.ilike(f"%{platform}%"))
    if min_score is not None:
        query = query.filter(Candidate.score >= min_score)
    if hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = query.filter(Candidate.created_at >= cutoff)

    if category:
        classified_ids = (
            db.query(Classification.candidate_id)
            .filter(Classification.category == category)
        )
        query = query.filter(Candidate.id.in_(classified_ids.subquery()))

    sort_map = {
        "score": Candidate.score.desc(),
        "date": Candidate.created_at.desc(),
        "likes": Candidate.likes_total.desc(),
        "views": Candidate.views_total.desc(),
    }
    query = query.order_by(sort_map.get(sort_by, Candidate.score.desc()))

    total = query.count()
    candidates = query.offset(offset).limit(limit).all()

    results = []
    for c in candidates:
        clf = db.query(Classification).filter(Classification.candidate_id == c.id).first()
        results.append(_serialize_candidate(c, clf))

    return {"total": total, "offset": offset, "limit": limit, "candidates": results}


# ─── Quick HOT Trends ─────────────────────────────────────────────────────────

@router.get("/hot")
async def list_hot_trends(
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Quick endpoint: returns only HOT classified trends, sorted by score"""
    query = db.query(Candidate).filter(Candidate.status == "hot")

    if category:
        classified_ids = (
            db.query(Classification.candidate_id)
            .filter(Classification.category == category)
        )
        query = query.filter(Candidate.id.in_(classified_ids.subquery()))

    query = query.order_by(Candidate.score.desc())
    candidates = query.limit(limit).all()

    results = []
    for c in candidates:
        clf = db.query(Classification).filter(Classification.candidate_id == c.id).first()
        results.append(_serialize_candidate(c, clf))

    return {"count": len(results), "trends": results}


# ─── Candidate Detail ─────────────────────────────────────────────────────────

@router.get("/candidates/{candidate_id}")
async def get_candidate_detail(
    candidate_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Get full detail for a single candidate including validation history and source signals"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    classification = (
        db.query(Classification)
        .filter(Classification.candidate_id == candidate_id)
        .first()
    )

    validations = (
        db.query(XValidation)
        .filter(XValidation.candidate_id == candidate_id)
        .order_by(XValidation.checked_at.desc())
        .all()
    )

    signal_ids = (candidate.source_signal_ids or "").split(",")
    signal_ids = [int(sid) for sid in signal_ids if sid.strip().isdigit()]
    signals = db.query(Signal).filter(Signal.id.in_(signal_ids)).all() if signal_ids else []

    result = _serialize_candidate(candidate, classification)
    result["fingerprint"] = candidate.fingerprint
    result["content"] = candidate.content  # Full content, not truncated
    result["validations"] = [
        {
            "id": v.id,
            "search_query": v.search_query,
            "post_count": v.post_count,
            "unique_authors": v.unique_authors,
            "total_engagement": v.total_engagement,
            "post_density_per_hour": v.post_density_per_hour,
            "verdict": v.verdict,
            "checked_at": v.checked_at.isoformat() if v.checked_at else None,
        }
        for v in validations
    ]
    result["source_signals"] = [_serialize_signal(s) for s in signals]
    return result


# ─── Raw Signals ───────────────────────────────────────────────────────────────

@router.get("/signals")
async def list_signals(
    platform: Optional[str] = Query(None, description="Filter: reddit, x, google_trends, tiktok"),
    has_media: Optional[bool] = Query(None, description="Filter by media presence"),
    processed: Optional[bool] = Query(None, description="Filter by processed status"),
    hours: Optional[int] = Query(None, description="Only signals from last N hours"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """List raw collected signals with filters"""
    query = db.query(Signal)
    if platform:
        query = query.filter(Signal.platform == platform)
    if has_media is not None:
        query = query.filter(Signal.has_media == has_media)
    if processed is not None:
        query = query.filter(Signal.is_processed == processed)
    if hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = query.filter(Signal.created_at >= cutoff)

    query = query.order_by(Signal.created_at.desc())
    total = query.count()
    signals = query.offset(offset).limit(limit).all()

    return {"total": total, "offset": offset, "limit": limit, "signals": [_serialize_signal(s) for s in signals]}


# ─── Statistics ────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_trend_stats(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Aggregated trend detector statistics"""
    total_signals = db.query(Signal).count()
    total_candidates = db.query(Candidate).count()

    status_counts = {}
    for s in ["hot", "early", "not_yet", "pending", "expired"]:
        status_counts[s] = db.query(Candidate).filter(Candidate.status == s).count()

    # Signals per platform
    platform_counts = {}
    for row in db.query(Signal.platform, func.count(Signal.id)).group_by(Signal.platform).all():
        platform_counts[row[0]] = row[1]

    # Category distribution (from classifications)
    category_counts = {}
    for row in db.query(Classification.category, func.count(Classification.id)).group_by(Classification.category).all():
        category_counts[row[0]] = row[1]

    watchlist_active = db.query(Watchlist).filter(Watchlist.is_active == True).count()
    total_classifications = db.query(Classification).count()

    # Last 24h activity
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    signals_24h = db.query(Signal).filter(Signal.created_at >= cutoff_24h).count()
    hot_24h = db.query(Candidate).filter(
        Candidate.status == "hot", Candidate.updated_at >= cutoff_24h
    ).count()

    return {
        "total_signals": total_signals,
        "total_candidates": total_candidates,
        "total_classifications": total_classifications,
        "watchlist_active": watchlist_active,
        "by_status": status_counts,
        "by_platform": platform_counts,
        "by_category": category_counts,
        "last_24h": {
            "signals_collected": signals_24h,
            "hot_trends": hot_24h,
        },
    }


# ─── Categories ────────────────────────────────────────────────────────────────

@router.get("/categories")
async def list_categories(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """List all classification categories with counts"""
    rows = (
        db.query(Classification.category, func.count(Classification.id))
        .group_by(Classification.category)
        .order_by(func.count(Classification.id).desc())
        .all()
    )
    return {
        "categories": [
            {"name": row[0], "count": row[1]}
            for row in rows
        ]
    }


# ─── Watchlist ─────────────────────────────────────────────────────────────────

@router.get("/watchlist")
async def list_watchlist(
    active_only: bool = Query(True, description="Show only active entries"),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """List watchlist entries (EARLY signals being monitored)"""
    query = db.query(Watchlist)
    if active_only:
        query = query.filter(Watchlist.is_active == True)
    query = query.order_by(Watchlist.next_check_at.asc())
    entries = query.all()

    results = []
    for w in entries:
        candidate = db.query(Candidate).filter(Candidate.id == w.candidate_id).first()
        results.append({
            "id": w.id,
            "candidate_id": w.candidate_id,
            "candidate_title": candidate.title if candidate else None,
            "candidate_score": candidate.score if candidate else None,
            "check_count": w.check_count,
            "max_checks": w.max_checks,
            "next_check_at": w.next_check_at.isoformat() if w.next_check_at else None,
            "last_checked_at": w.last_checked_at.isoformat() if w.last_checked_at else None,
            "is_active": w.is_active,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        })

    return {"count": len(results), "watchlist": results}


# ─── Pipeline Triggers ─────────────────────────────────────────────────────────

@router.post("/run")
async def trigger_pipeline(
    platform: str = Query("reddit", description="Platform: reddit, google_trends, x, tiktok"),
    current_user: User = Depends(require_current_user),
):
    """Manually trigger the trend detection pipeline for a specific platform"""
    result = await trend_scheduler.run_pipeline_once(platform=platform)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/run/all")
async def trigger_all_pipelines(
    current_user: User = Depends(require_current_user),
):
    """Trigger pipeline for ALL configured collectors sequentially"""
    platforms = ["reddit", "google_trends", "x", "tiktok"]
    results = {}
    for p in platforms:
        result = await trend_scheduler.run_pipeline_once(platform=p)
        results[p] = result
    return {"results": results}
