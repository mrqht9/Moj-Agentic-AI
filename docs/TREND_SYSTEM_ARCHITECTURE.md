# نظام تحليل الترندات — التوثيق الكامل
# Trend Detection & Analysis System — Full Documentation

---

## Flowchart — خوارزمية النظام الكاملة

```
┌─────────────────────────────────────────────────────────────────────┐
│                    APScheduler (Background)                         │
│  X: كل 10 دقائق | Google Trends: كل 30 دقيقة | Watchlist: كل 15   │
└─────────────┬───────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  المرحلة 1: COLLECT (جمع البيانات)       │
│                                         │
│  ┌──────────────┐  ┌─────────────────┐  │
│  │ XCollector    │  │ GoogleTrends    │  │
│  │ POST /search  │  │ SerpAPI         │  │
│  │ GET /top_posts│  │ Trending Now    │  │
│  └──────┬───────┘  └──────┬──────────┘  │
│         │                  │             │
│         └────────┬─────────┘             │
│                  ▼                       │
│         raw_signals: List[Dict]          │
│         {platform, source_id, title,     │
│          content, views, likes, ...}     │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  المرحلة 1.5: MEDIA ANALYSIS (اختياري)  │
│                                         │
│  VisionAnalyzer                         │
│  - Google Cloud Vision API              │
│  - TEXT_DETECTION → نص من الصورة         │
│  - LABEL_DETECTION → تصنيف الصورة       │
│  - يملأ حقل media_text في الإشارة       │
│  - يتجاهل الفيديو، يحلل الصور فقط      │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  المرحلة 2: NORMALIZE (تطبيع وحفظ)      │
│                                         │
│  Normalizer.process()                   │
│  - يحول raw_signals → Signal DB rows    │
│  - يتجاهل التكرارات (platform+source_id)│
│  - يحفظ في جدول td_signals              │
│  - يرجع فقط الإشارات الجديدة            │
│                                         │
│  ⛔ لو كلها تكرارات → يتوقف هنا         │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  المرحلة 3: DEDUP & MERGE (دمج)         │
│                                         │
│  Deduplicator.process()                 │
│  لكل signal جديد:                       │
│                                         │
│  ┌─ 1. Exact fingerprint match?         │
│  │     SHA-256(normalized_title+keywords)│
│  │     ✅ نعم → دمج في Candidate موجود  │
│  │                                      │
│  ├─ 2. Word overlap >= 0.6?             │
│  │     Jaccard similarity بين العناوين   │
│  │     ✅ نعم → دمج في أقرب Candidate   │
│  │                                      │
│  └─ 3. لا تطابق → إنشاء Candidate جديد │
│                                         │
│  عند الدمج:                              │
│  - تجميع التفاعلات (views+likes+...)    │
│  - تحديث قائمة المنصات                   │
│  - إضافة signal_id للمصادر               │
│                                         │
│  Output → List[Candidate]               │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  المرحلة 4: SCORE (تقييم)                │
│                                         │
│  ScoringEngine._score_candidate()       │
│                                         │
│  النقاط (من 0 إلى ~22):                 │
│  ┌─────────────────────────────────────┐│
│  │ المعيار          │ النقاط │ الحد    ││
│  ├─────────────────────────────────────┤│
│  │ views > threshold │  +3   │ X:10K   ││
│  │ likes > threshold │  +4   │ X:1K    ││
│  │ reshares > thresh │  +3   │ X:500   ││
│  │ comments > thresh │  +2   │ X:300   ││
│  │ cross_platform≥2  │  +5   │ —       ││
│  │ trending_source   │  +6   │ Google  ││
│  │ has_media         │  +1   │ —       ││
│  └─────────────────────────────────────┘│
│                                         │
│  الحدود تختلف حسب المنصة:               │
│  - X: views>10K, likes>1K, reshares>500 │
│  - Reddit: views>5K, likes>1K           │
│  - TikTok: views>50K, likes>5K          │
│  - Google Trends: تلقائي +6 (trending)  │
│                                         │
│  Output → scored candidates sorted desc │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  المرحلة 5: VALIDATE (تحقق X)           │
│                                         │
│  XValidator.validate()                  │
│                                         │
│  Pre-filter:                            │
│  - score < 6 → NOT_YET (بدون API call)  │
│  - max 15 candidate per batch           │
│                                         │
│  لكل candidate مؤهل:                    │
│  1. _build_search_query()               │
│     → أول 6 كلمات من العنوان             │
│  2. _search_x() → POST /api/search      │
│     → Latest tweets, 3 pages            │
│  3. _analyze_results()                  │
│     → post_count                        │
│     → unique_authors (كتّاب مختلفين)    │
│     → total_engagement (likes+RT+reply) │
│     → density (tweets/hour آخر 4 ساعات) │
│  4. _decide_verdict()                   │
│                                         │
│  ┌─────────────────────────────────────┐│
│  │         قرار الحكم (Verdict)         ││
│  ├─────────────────────────────────────┤│
│  │ 🔥 HOT — مسار عادي:                 ││
│  │   score >= 8                        ││
│  │   AND unique_authors >= 8           ││
│  │   AND density >= 4/hour             ││
│  │                                     ││
│  │ 🔥 HOT — مسار فيروسي:              ││
│  │   score >= 8                        ││
│  │   AND engagement >= 10,000          ││
│  │   AND unique_authors >= 3           ││
│  │                                     ││
│  │ ⏳ EARLY:                           ││
│  │   score >= 6                        ││
│  │   AND (authors >= 2 OR eng >= 1000) ││
│  │                                     ││
│  │ 📌 NOT_YET:                         ││
│  │   كل شي ثاني                        ││
│  └─────────────────────────────────────┘│
│                                         │
│  بعد الحكم:                              │
│  - HOT → يكمل للتصنيف (المرحلة 6)      │
│  - EARLY → يضاف لقائمة المراقبة         │
│  - NOT_YET → ينتظر الدورة القادمة       │
│                                         │
│  يحفظ سجل في td_x_validation            │
└──────────────────┬──────────────────────┘
                   │
          ┌────────┴────────┐
          │                 │
     HOT ▼            EARLY ▼
┌──────────────┐  ┌──────────────────────┐
│ المرحلة 6:    │  │ WATCHLIST (مراقبة)    │
│ CLASSIFY     │  │                      │
│              │  │ _add_to_watchlist()   │
│              │  │ - max 6 checks       │
│              │  │ - interval يزداد:    │
│              │  │   15min, 30min, 45min │
│              │  │                      │
│              │  │ _recheck_watchlist()  │
│              │  │ كل 15 دقيقة:         │
│              │  │ - re-score           │
│              │  │ - re-validate        │
│              │  │ - HOT? → classify ✅  │
│              │  │ - max checks? → expire│
│              │  │ - else → wait more   │
└──────┬───────┘  └──────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  المرحلة 6: CLASSIFY (تصنيف)            │
│                                         │
│  Classifier.classify()                  │
│                                         │
│  ┌─ OpenAI متوفر؟                       │
│  │  ✅ → _classify_with_openai()        │
│  │     يرسل العنوان + المحتوى + التفاعل │
│  │     يرجع JSON:                       │
│  │     {category, subcategory,          │
│  │      sensitivity, risk_notes,        │
│  │      keywords, entities,             │
│  │      summary_ar, summary_en}         │
│  │                                      │
│  └─ ❌ → _fallback_classify()           │
│        keyword matching بسيط:           │
│        "سياس" → سياسي                   │
│        "كرة" → رياضة                    │
│        "ai" → تقنية                     │
│                                         │
│  التصنيفات:                              │
│  سياسي | اجتماعي | رياضة | ترفيه        │
│  اقتصاد | تقنية | تاريخي | ثقافي        │
│  صحة | أخرى                             │
│                                         │
│  مستويات الحساسية:                       │
│  low | medium | high | critical         │
│                                         │
│  يحفظ في td_classifications             │
└──────────────────┬──────────────────────┘
                   │
                   ▼
        ✅ الترند جاهز في قاعدة البيانات
           status = "hot"
           مع التصنيف والتحليل


═══════════════════════════════════════════
          طبقة العرض (Chatbot)
═══════════════════════════════════════════

┌─────────────────────────────────────────┐
│  المستخدم يكتب في الشات                 │
│  "وش الترندات؟"                         │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  detect_user_intent()                   │
│  intent_service.detect_intent(text)     │
│                                         │
│  النوايا المتعلقة بالترندات:            │
│  - get_trends → نظرة عامة               │
│  - get_hot_trends → الحارة فقط          │
│  - search_trends → بحث بكلمة            │
│  - trend_detail → تفاصيل ترند معين     │
│  - run_trends → حالة النظام             │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  MainAgent.process_message()            │
│                                         │
│  intent ∈ TREND_INTENTS?                │
│  ✅ → trend_agent.process_request()     │
│  ❌ → X_Agent أو fallback              │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  TrendAgent.process_request()           │
│                                         │
│  1. _gather_data(intent, message, db)   │
│     → يقرأ من DB حسب النية              │
│     → يجهز formatted fallback           │
│                                         │
│  2. _ask_llm() (OpenAI)                 │
│     → يرسل البيانات + سؤال المستخدم     │
│     → يرجع تحليل طبيعي بالعربي          │
│     → لو فشل → يستخدم formatted         │
│                                         │
│  3. Return response → Chat              │
└─────────────────────────────────────────┘
```

---

## هيكل الملفات

```
app/trend_detector/
├── config.py                  # إعدادات النظام (أوزان، حدود، APIs)
├── models.py                  # جداول قاعدة البيانات (6 جداول)
├── collectors/
│   ├── base.py               # BaseCollector — الواجهة الأساسية
│   ├── x_collector.py        # جمع من X (تويتر) عبر Custom API
│   ├── google_trends.py      # جمع من Google Trends عبر SerpAPI
│   ├── reddit.py             # جمع من Reddit (غير مفعّل حالياً)
│   └── tiktok.py             # جمع من TikTok (غير مفعّل حالياً)
├── media/
│   └── vision_analyzer.py    # تحليل الصور بـ Google Vision
├── pipeline/
│   ├── normalizer.py         # تطبيع وحفظ الإشارات
│   ├── deduplicator.py       # إزالة التكرار ودمج المتشابهات
│   ├── scoring.py            # تقييم بالنقاط
│   └── validator.py          # تحقق على X + حكم HOT/EARLY/NOT_YET
├── classifier/
│   └── classifier.py         # تصنيف بـ OpenAI أو fallback
└── scheduler/
    └── scheduler.py          # المنسق الرئيسي (APScheduler)

app/agents/
├── trend_agent.py            # وكيل الترندات (طبقة العرض في الشات)
├── main_agent_simple.py      # الوكيل الرئيسي (توجيه النوايا)
└── tools.py                  # detect_user_intent + أدوات X
```

---

## جداول قاعدة البيانات (6 جداول)

### 1. `td_signals` — الإشارات الخام
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | PK | معرف |
| platform | String | المنصة (x, google_trends, reddit, tiktok) |
| source_id | String | معرف المنشور الأصلي على المنصة |
| title | String(1000) | العنوان |
| content | Text | المحتوى الكامل |
| url | String | رابط المنشور |
| media_url | String | رابط الصورة/الفيديو |
| media_text | Text | نص مستخرج من الصورة (Vision API) |
| keywords | Text | كلمات مفتاحية (comma-separated) |
| author | String | الكاتب |
| published_at | DateTime | تاريخ النشر |
| views, likes, reshares, comments | Integer | التفاعلات |
| raw_data | JSON | البيانات الخام الكاملة |
| has_media | Boolean | هل يحتوي على وسائط |
| is_processed | Boolean | هل تمت معالجته |

### 2. `td_candidates` — المرشحين (بعد الدمج)
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | PK | معرف |
| fingerprint | String(64) | بصمة SHA-256 فريدة |
| title, content, keywords | Text | المحتوى |
| platforms | String | المنصات (comma-separated) |
| source_signal_ids | String | معرفات الإشارات المدمجة |
| views_total, likes_total, ... | Integer | مجموع التفاعلات |
| platform_count | Integer | عدد المنصات |
| score | Float | النقاط |
| status | String | الحالة: pending, hot, early, not_yet, expired |

### 3. `td_x_validation` — نتائج التحقق على X
| العمود | النوع | الوصف |
|--------|-------|-------|
| candidate_id | FK | المرشح |
| search_query | String | استعلام البحث المستخدم |
| post_count | Integer | عدد التغريدات |
| unique_authors | Integer | كتّاب مختلفين |
| total_engagement | Integer | إجمالي التفاعل |
| post_density_per_hour | Float | كثافة النشر بالساعة |
| verdict | String | الحكم: HOT, EARLY, NOT_YET |

### 4. `td_classifications` — التصنيفات
| العمود | النوع | الوصف |
|--------|-------|-------|
| candidate_id | FK | المرشح |
| category | String | التصنيف (سياسي، رياضة، ...) |
| subcategory | String | تصنيف فرعي |
| sensitivity | String | الحساسية (low → critical) |
| summary_ar, summary_en | Text | ملخصات |
| entities | Text/JSON | أسماء، أماكن، فرق |

### 5. `td_watchlist` — قائمة المراقبة (EARLY signals)
| العمود | النوع | الوصف |
|--------|-------|-------|
| candidate_id | FK | المرشح |
| check_count | Integer | عدد مرات الفحص |
| max_checks | Integer | الحد الأقصى (6) |
| next_check_at | DateTime | موعد الفحص التالي |
| is_active | Boolean | نشط أم منتهي |

### 6. `td_scoring_config` — إعدادات التقييم (admin)

---

## تفصيل كل Function

### المرحلة 1: Collectors (الجمع)

#### `BaseCollector` (`collectors/base.py`)
| Function | الوصف |
|----------|-------|
| `collect()` | **abstract** — كل collector يجمع بيانات بطريقته ويرجع `List[Dict]` بنفس الشكل |
| `is_configured()` | يتحقق إذا API keys موجودة |
| `_make_signal()` | helper لتوحيد شكل الإشارة الخام |

#### `XCollector` (`collectors/x_collector.py`)
| Function | الوصف |
|----------|-------|
| `collect()` | يجمع من X عبر Custom API Server (`http://108.181.169.216:5321`) |
| `_search_tweets(session, query)` | `POST /api/search` — يبحث بعبارات عربية مثل "ترند السعودية", "عاجل السعودية" |
| `_get_top_posts(session, country)` | `GET /api/top_posts?country=SAU` — المنشورات الأكثر رواجاً |
| `_parse_tweet(tweet, source)` | يحول تغريدة من API format إلى signal dict موحد |

**استعلامات البحث:**
- `"ترند السعودية"` (Top, 3 pages)
- `"عاجل السعودية"` (Latest, 2 pages)
- `"هاشتاق ترند"` (Top, 2 pages)
- `"اكثر شي متداول"` (Latest, 2 pages)
- Top posts: SAU, ar

#### `GoogleTrendsCollector` (`collectors/google_trends.py`)
| Function | الوصف |
|----------|-------|
| `collect()` | يجمع من SerpAPI Google Trends Trending Now |

**المناطق:** SA (عربي), US (إنجليزي) — آخر 24 ساعة

---

### المرحلة 1.5: Media Analysis

#### `VisionAnalyzer` (`media/vision_analyzer.py`)
| Function | الوصف |
|----------|-------|
| `analyze_image_url(url)` | يرسل صورة لـ Google Vision → TEXT_DETECTION + LABEL_DETECTION |
| `process_signals(raw_signals)` | يمر على كل signal فيه صورة ويحلله → يملأ `media_text` |
| `_is_image_url(url)` | يتحقق إذا الرابط صورة (jpg, png, etc.) أو من مواقع صور معروفة |

---

### المرحلة 2: Normalize

#### `Normalizer` (`pipeline/normalizer.py`)
| Function | الوصف |
|----------|-------|
| `process(raw_signals, db)` | يحول List[Dict] → Signal DB rows. يتخطى الموجود (بـ platform+source_id). يرجع الجديد فقط. |

---

### المرحلة 3: Dedup & Merge

#### `Deduplicator` (`pipeline/deduplicator.py`)
| Function | الوصف |
|----------|-------|
| `process(signals, db, threshold=0.6)` | المنطق الرئيسي — يدمج signals متشابهة في candidates |
| `_normalize_text(text)` | تنظيف النص: lowercase, إزالة علامات الترقيم |
| `_fingerprint(title, keywords)` | SHA-256 hash من النص المنظف — للتطابق التام |
| `_word_overlap_ratio(a, b)` | Jaccard similarity (تقاطع الكلمات ÷ اتحادها) — للتطابق التقريبي |

**خوارزمية الدمج:**
```
لكل signal:
  1. fp = SHA256(normalize(title + keywords))
  2. candidate = DB.find(fingerprint == fp)
  3. if not found:
       for each existing candidate:
         score = word_overlap(signal.title, candidate.title)
         if score >= 0.6: candidate = best_match
  4. if candidate exists:
       candidate.views += signal.views  (وباقي التفاعلات)
       candidate.platforms += signal.platform
       candidate.source_signal_ids += signal.id
  5. else:
       candidate = new Candidate(from signal)
  6. signal.is_processed = True
```

---

### المرحلة 4: Score

#### `ScoringEngine` (`pipeline/scoring.py`)
| Function | الوصف |
|----------|-------|
| `process(candidates, db)` | يقيّم كل candidate ويحفظ النتيجة. يرتب تنازلياً. |
| `_score_candidate(candidate)` | حساب النقاط — كل معيار يتجاوز الحد يضيف نقاط |
| `_get_thresholds(platform)` | يرجع حدود المنصة المحددة |

**جدول النقاط:**
```
views > حد المنصة     → +3 نقاط
likes > حد المنصة     → +4 نقاط
reshares > حد المنصة  → +3 نقاط
comments > حد المنصة  → +2 نقاط
منصتين أو أكثر        → +5 نقاط (cross-platform bonus)
مصدر trending (Google) → +6 نقاط
فيه صورة/فيديو        → +1 نقطة
──────────────────────
الحد الأقصى النظري    ≈ 24 نقطة
```

---

### المرحلة 5: Validate

#### `XValidator` (`pipeline/validator.py`)
| Function | الوصف |
|----------|-------|
| `validate(candidates, db)` | المحرك الرئيسي — يتحقق من كل candidate على X |
| `_search_x(query, session)` | `POST /api/search` — بحث في تويتر عن العنوان |
| `_build_search_query(candidate)` | يأخذ أول 6 كلمات من العنوان كاستعلام بحث |
| `_analyze_results(tweets)` | يحسب: post_count, unique_authors, total_engagement, density |
| `_decide_verdict(metrics, score)` | القرار النهائي: HOT / EARLY / NOT_YET |
| `_add_to_watchlist(candidate, db)` | يضيف EARLY candidate للمراقبة |

**حساب الكثافة (density):**
```python
recent_tweets = tweets from last 4 hours
density = count(recent_tweets) / 4.0  # tweets per hour
```

**شروط HOT (مساران):**
```
المسار العادي:
  score >= 8 AND authors >= 8 AND density >= 4/hour

المسار الفيروسي:
  score >= 8 AND engagement >= 10,000 AND authors >= 3
```

**شروط EARLY:**
```
  score >= 6 AND (authors >= 2 OR engagement >= 1,000)
```

---

### المرحلة 6: Classify

#### `Classifier` (`classifier/classifier.py`)
| Function | الوصف |
|----------|-------|
| `classify(candidates, db)` | يصنف HOT candidates — OpenAI أو fallback |
| `_classify_with_openai(prompt)` | يرسل للذكاء الاصطناعي → JSON (category, sensitivity, summary, entities) |
| `_build_user_prompt(candidate)` | يجهز prompt من العنوان + المحتوى + التفاعلات |
| `_fallback_classify(candidate)` | تصنيف بسيط بالكلمات المفتاحية لو OpenAI غير متوفر |

---

### Scheduler (المنسق)

#### `TrendDetectorScheduler` (`scheduler/scheduler.py`)
| Function | الوصف |
|----------|-------|
| `start()` | يبدأ كل الجداول الزمنية (APScheduler) |
| `stop()` | يوقف الجدولة |
| `_run_collector_pipeline(collector)` | **Pipeline كامل:** Collect → Vision → Normalize → Dedup → Score → Validate → Classify |
| `_recheck_watchlist()` | يعيد فحص EARLY signals — ممكن تترقى لـ HOT أو تنتهي |
| `run_pipeline_once(platform)` | تشغيل يدوي مرة واحدة (للاختبار أو API trigger) |

**الجدول الزمني:**
```
X Collector:       كل 10 دقائق
Google Trends:     كل 30 دقيقة
Watchlist Recheck: كل 15 دقيقة
Reddit:            كل 15 دقيقة (غير مفعّل)
TikTok:            كل 60 دقيقة (غير مفعّل)
```

---

### Chatbot Layer (طبقة الشات)

#### `TrendAgent` (`agents/trend_agent.py`)
| Function | الوصف |
|----------|-------|
| `process_request(message, context, db)` | نقطة الدخول — يجمع البيانات ويرد على المستخدم |
| `_gather_data(intent, message, context, db)` | يقرأ من DB حسب النية ويجهز الرد |
| `_get_stats(db)` | إحصائيات عامة (عدد signals, candidates, hot, early, watchlist) |
| `_get_hot_list(db)` | قائمة الترندات الحارة (HOT) |
| `_get_early_list(db, limit)` | قائمة الترندات المبكرة (EARLY) |
| `_get_top_arabic(db, limit)` | أعلى الترندات مرتبة بالنقاط (مع فلتر الفارسي) |
| `_search_db(db, query)` | بحث في العناوين + المحتوى + الكلمات المفتاحية |
| `_get_trend_detail(message, db)` | بحث fuzzy عن ترند محدد (3 استراتيجيات) |
| `_extract_title_fragment(message)` | تنظيف رسالة المستخدم لاستخراج عنوان الترند |
| `_filter_arabic(candidates)` | يفلتر المحتوى الفارسي (يبقي العربي والإنجليزي) |
| `_candidate_to_dict(c, db)` | يحول Candidate DB object → dict مع التصنيف والتحقق |
| `_ask_llm(message, trend_data)` | يرسل البيانات + سؤال المستخدم لـ OpenAI |
| `_generate_context(t)` | يولّد سطر سياق مختصر لترند (فئة + تفاعل + نوع) |
| `_build_analysis(d)` | **تحليل مفصل:** ليش صار ترند + كيف وصل + درجة + حساسية + توصية |
| `_trend_line(t, idx)` | يفرمت سطر واحد لترند (أيقونة + عنوان + تفاعل) |
| `_format_overview(data)` | فرمتة النظرة العامة (HOT + TOP + إحصائيات) |
| `_format_hot(data)` | فرمتة الترندات الحارة فقط |
| `_format_search(data)` | فرمتة نتائج البحث |
| `_format_detail(data)` | **فرمتة التفاصيل الكاملة** لترند واحد مع كل البيانات والتحليل |
| `_format_run(data)` | فرمتة حالة النظام |

#### `_get_trend_detail` — خوارزمية البحث الذكي (3 استراتيجيات):
```
1. البحث بالنص الكامل في title + content
2. تقصير تدريجي: 5 كلمات → 4 → 3 → 2
3. أطول كلمة مهمة (>= 4 أحرف) في title + content
```

#### `_build_analysis` — خوارزمية التحليل (5 أقسام):
```
القسم 1: ليش صار ترند؟
  → تحليل الموضوع (بيان رسمي, حدث أمني, خبر عاجل, إيران, السعودية, خليجي)
  → أو تحليل من التصنيف (سياسي, رياضي, ترفيهي, ...)

القسم 2: كيف وصل ترند؟
  → عمر الترند (طازج, زخم, مستمر, ثابت)
  → تفصيل التفاعل (شافوه X | أعجب Y | أعاد نشره Z)
  → نسبة إعادة النشر/الإعجاب (مؤشر الانتشار)
  → تفاصيل X: عدد التغريدات, كتّاب, كثافة, حكم
  → انتشار عبر المنصات

القسم 3: درجة الترند (X/10)
  → تقييم وشرح الدرجة

القسم 4: تنبيه حساسية
  → لو مصنف medium/high/critical

القسم 5: توصية عملية
  → حسب الحالة (HOT/EARLY/NOT_YET)
  → حسب نوع الموضوع (أمني → دقة, بيان → اقتباس)
  → حسب التفاعل (كبير → فرصة وصول)
```

---

## مخطط تدفق البيانات (Data Flow)

```
[X API Server] ──POST /search──→ raw tweets ─┐
[X API Server] ──GET /top_posts─→ raw tweets ─┤
[SerpAPI]      ──Google Trends──→ raw trends ─┤
                                              │
                              ┌───────────────┘
                              ▼
                    ┌─────────────────┐
                    │   raw_signals   │  List[Dict] — شكل موحد
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ VisionAnalyzer  │  تحليل صور → media_text
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Normalizer    │  → td_signals (DB)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Deduplicator   │  → td_candidates (DB)
                    │  fingerprint +  │
                    │  word overlap   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ ScoringEngine   │  score = weighted sum
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  XValidator     │  → td_x_validation (DB)
                    │  POST /search   │
                    │  HOT/EARLY/NOT  │
                    └───┬────────┬────┘
                        │        │
                   HOT  │   EARLY│
                        │        │
                   ┌────▼──┐  ┌──▼───────────┐
                   │Classif│  │  Watchlist    │
                   │  ier  │  │  (re-check)  │
                   └───┬───┘  └──────────────┘
                       │
              ┌────────▼────────┐
              │ td_classifications│  → category, sensitivity, summary
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │   TrendAgent    │  → chatbot response
              │  _gather_data() │
              │  _build_analysis│
              │  _format_detail │
              └─────────────────┘
```

---

## ملخص الأرقام الرئيسية

| المعيار | القيمة |
|---------|--------|
| عدد الجداول | 6 |
| عدد الـ Collectors | 4 (2 مفعّل: X + Google Trends) |
| دورة جمع X | كل 10 دقائق |
| دورة جمع Google | كل 30 دقيقة |
| دورة مراقبة Watchlist | كل 15 دقيقة |
| حد HOT (score) | >= 8 |
| حد HOT (authors) | >= 8 |
| حد HOT (density) | >= 4/hour |
| حد EARLY (score) | >= 6 |
| حد الفيروسي (engagement) | >= 10,000 |
| max watchlist checks | 6 |
| similarity threshold | 0.6 (Jaccard) |
| max validations/batch | 15 |
