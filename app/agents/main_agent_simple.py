#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
الوكيل الرئيسي - نسخة مبسطة بدون autogen
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from .tools import detect_user_intent
from .x_agent_simple import XAgent
from .trend_agent import TrendAgent
from app.services.memory_service import memory_service


class MainAgent:
    """الوكيل الرئيسي المبسط"""
    
    TREND_INTENTS = {"get_trends", "get_hot_trends", "search_trends", "run_trends", "trend_detail"}
    
    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config
        self.x_agent = XAgent(llm_config)
        self.trend_agent = TrendAgent(llm_config)
    
    def process_message(
        self, 
        message: str, 
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        db: Optional[Session] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """معالجة رسالة من المستخدم"""
        
        conversation_id = None
        
        # إنشاء أو الحصول على المحادثة
        if db:
            try:
                conversation = memory_service.get_or_create_conversation(
                    db=db, user_id=user_id, session_id=session_id
                )
                conversation_id = conversation.id
                
                # إضافة رسالة المستخدم
                memory_service.add_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="user",
                    content=message
                )
            except Exception as e:
                print(f"Warning: Memory service error: {str(e)}")
        
        try:
            # تحليل النية
            intent_result = detect_user_intent(message)
            intent = intent_result.get("intent")
            platform = intent_result.get("platform")
            entities = intent_result.get("entities", {})
            confidence = intent_result.get("confidence", 0)
            
            print(f"[DEBUG MainAgent] message='{message[:80]}' intent={intent} platform={platform} confidence={confidence} entities={entities}")
            
            if confidence < 0.5:
                print(f"[DEBUG MainAgent] LOW confidence ({confidence}) — falling back to AI")
                # لا ترجع رد تلقائي - دع الوكيل يتعامل مع الطلب
                return None
            
            # توجيه للوكيل المناسب
            if intent in self.TREND_INTENTS:
                trend_context = {
                    "intent": intent,
                    "entities": entities,
                    "raw_text": message,
                }
                trend_response = self.trend_agent.process_request(message, trend_context, db)
                
                if trend_response:
                    if db and conversation_id:
                        try:
                            memory_service.add_message(
                                db=db, conversation_id=conversation_id,
                                role="assistant", content=trend_response,
                                intent=intent, confidence=confidence, agent="Trend_Agent"
                            )
                        except: pass
                    
                    return {
                        "success": True,
                        "message": trend_response,
                        "intent_result": intent_result,
                        "agent": "Trend_Agent",
                        "conversation_id": conversation_id
                    }
            
            elif intent == "generate_identity":
                identity_response = self._handle_generate_identity(message, entities)
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db, conversation_id=conversation_id,
                            role="assistant", content=identity_response,
                            intent=intent, confidence=confidence, agent="Identity_Agent"
                        )
                    except: pass
                return {
                    "success": True,
                    "message": identity_response,
                    "intent_result": intent_result,
                    "agent": "Identity_Agent",
                    "conversation_id": conversation_id
                }

            elif platform in ["twitter", "x"] or intent in ["add_account", "create_post", "schedule_post", "delete_post", "remove_account", "update_profile", "like_post", "repost", "share_post", "follow_user", "unfollow_user", "reply_to_comment", "bookmark_post"]:
                context = {
                    "intent": intent,
                    "entities": entities,
                    "platform": platform,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                }
                
                x_response = self.x_agent.process_request(message, context)
                
                # إذا لم يرجع X_Agent رد
                if not x_response:
                    print(f"[DEBUG] X_Agent returned no response for intent: {intent}")
                    return {
                        "success": False,
                        "message": None,  # لا رد تلقائي
                        "intent_result": intent_result
                    }
                
                # حفظ الرد
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db,
                            conversation_id=conversation_id,
                            role="assistant",
                            content=x_response,
                            intent=intent,
                            confidence=confidence,
                            agent="X_Agent",
                            metadata={"platform": platform, "entities": entities}
                        )
                    except Exception as e:
                        print(f"Warning: Failed to save message: {str(e)}")
                
                return {
                    "success": True,
                    "message": x_response,
                    "intent_result": intent_result,
                    "agent": "X_Agent",
                    "conversation_id": conversation_id
                }
            
            elif intent == "help":
                help_message = """🤖 **أنا موج — مساعدك لإدارة منصات التواصل**

هذي كل الأوامر اللي أفهمها مع مثال على كل واحد:

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 **إدارة الحسابات**
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **إضافة حساب** (بالكوكيز أو يوزر/باسورد):
• `اضف حساب وارفق ملف الكوكيز`
• `سجل دخول الحساب myuser الباسورد mypass`

🔹 **عرض الحسابات:**
• `اعرض حساباتي`
• `كم حساب عندي`

🔹 **حذف حساب:**
• `احذف حساب test_user`

━━━━━━━━━━━━━━━━━━━━━━━━━━━
✍️ **النشر والمحتوى**
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **نشر تغريدة:**
• `انشر تغريدة "مرحباً بالجميع"`
• `غرد "صباح الخير" من حساب myuser`
• `انشر "نص" مع الصورة https://example.com/pic.jpg`

🔹 **جدولة تغريدة:**
• `جدول تغريدة "تذكير" بكرا الساعة 9`
• `جدول بعد 3 ساعات "اجتماع مهم"`
• `انشر الساعة 14:30 "النص"`

🔹 **حذف تغريدة:**
• `احذف تغريدة 1234567890123456789`

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 **توليد هويات وهمية (AI)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **هوية عشوائية كاملة:**
• `ولّد هوية عشوائية`
• `اصنع لي شخصية`

🔹 **بمعايير محددة:**
• `ولّد هوية سعودي رجل تقني`
• `ولّد شخصية امرأة كويتية ساخرة`
• `ولّد هوية مصري رياضي بايو قصير`

🔹 **بدون صور (أسرع):**
• `ولّد هوية بدون صور`

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎭 **تعديل هوية الحساب**
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **تغيير الاسم:**
• `غيّر اسم الحساب إلى خالد`

🔹 **تغيير البايو:**
• `عدّل البايو إلى "مطور برمجيات"`

🔹 **تغيير الصورة الشخصية:**
• `غيّر صورة الحساب https://example.com/avatar.jpg`

🔹 **تغيير الغلاف:**
• `غيّر الغلاف https://example.com/banner.jpg`

🔹 **تعديل كامل:**
• `حدّث بروفايل حساب myuser: الاسم "أحمد" البايو "كاتب" الموقع "الرياض"`

━━━━━━━━━━━━━━━━━━━━━━━━━━━
❤️ **التفاعل مع التغريدات**
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **إعجاب (لايك):**
• `لايك https://x.com/user/status/123456`

🔹 **إعادة نشر (ريتويت):**
• `أعد نشر https://x.com/user/status/123456`

🔹 **رد:**
• `رد على https://x.com/user/status/123456 "نص الرد"`

🔹 **حفظ (بوكمارك):**
• `احفظ تغريدة https://x.com/user/status/123456`

🔹 **متابعة / إلغاء متابعة:**
• `تابع @username`
• `الغ متابعة @username`

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **الترندات**
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **نظرة عامة:**
• `وش الترند اليوم؟`
• `آخر الترندات`

🔹 **الترندات النشطة:**
• `ترندات نشطة`
• `أعلى ترند`

🔹 **بحث بكلمة:**
• `ترند السعودية`
• `ابحث ترند الذكاء الاصطناعي`
• `هل يتصدر الهلال؟`

🔹 **تفاصيل ترند:**
• انسخ سطر من قائمة الترندات وأرسله
• أو اكتب: `تفاصيل ترند [العنوان]`

🔹 **تشغيل جمع الترندات يدوياً:**
• `شغل ترند`
• `اجمع ترندات`

━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 **نصائح**
━━━━━━━━━━━━━━━━━━━━━━━━━━━

• لو ما حددت حساب، أستخدم أول حساب مسجّل عندك
• لإظهار المتصفح أثناء التنفيذ: أضف `بشكل ظاهر`
• الجدولة بتوقيت السعودية تلقائياً
• كل صور البروفايل لازم تكون روابط مباشرة (مش Pinterest)

اكتب أي أمر من فوق وأنا أساعدك! 🚀"""
                
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db, conversation_id=conversation_id,
                            role="assistant", content=help_message,
                            intent=intent, confidence=confidence, agent="Main_Agent"
                        )
                    except: pass
                
                return {
                    "success": True,
                    "message": help_message,
                    "intent_result": intent_result,
                    "agent": "Main_Agent",
                    "conversation_id": conversation_id
                }
            
            elif intent == "greeting":
                greeting_msg = "مرحباً! 👋 أنا **موج**، مساعدك الذكي لإدارة حساباتك على منصات التواصل الاجتماعي.\n\nيمكنني مساعدتك في:\n📎 رفع كوكيز وإضافة حسابات X\n✍️ نشر تغريدات وإعادة نشر\n❤️ إعجاب ومتابعة وحفظ\n💬 الرد على التغريدات\n📊 متابعة الترندات\n🗑️ حذف تغريدات وحسابات\n\nكيف يمكنني مساعدتك اليوم؟"
                
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db, conversation_id=conversation_id,
                            role="assistant", content=greeting_msg,
                            intent=intent, confidence=confidence, agent="Main_Agent"
                        )
                    except: pass
                
                return {
                    "success": True,
                    "message": greeting_msg,
                    "intent_result": intent_result,
                    "agent": "Main_Agent",
                    "conversation_id": conversation_id
                }
            
            elif intent == "list_accounts":
                # عرض حسابات المستخدم النشطة من قاعدة البيانات + مجلد الكوكيز
                accounts_msg = ""
                db_accounts = []
                
                if db and user_id:
                    try:
                        from app.services.account_service import account_service
                        
                        # الحصول على الحسابات النشطة فقط
                        db_accounts = account_service.get_user_accounts(
                            db=db,
                            user_id=user_id,
                            status="active"
                        ) or []
                    except Exception as e:
                        print(f"Error fetching accounts from DB: {e}")
                
                # فحص مجلد الكوكيز كفولباك
                from pathlib import Path
                cookies_dir = Path(__file__).parent.parent / "x" / "cookies"
                cookie_usernames = set()
                if cookies_dir.exists():
                    for f in sorted(cookies_dir.glob("*.json")):
                        cookie_usernames.add(f.stem)
                
                # دمج: حسابات قاعدة البيانات + حسابات الكوكيز غير الموجودة بالقاعدة
                db_usernames = {a.username for a in db_accounts} if db_accounts else set()
                extra_cookie_accounts = cookie_usernames - db_usernames
                
                if db_accounts or extra_cookie_accounts:
                    accounts_msg = f"📋 **حساباتك النشطة:**\n\n"
                    
                    if db_accounts:
                        # تجميع الحسابات حسب المنصة
                        platforms = {}
                        for account in db_accounts:
                            platform_name = account.platform
                            if platform_name == "x":
                                platform_name = "X (Twitter)"
                            elif platform_name == "instagram":
                                platform_name = "Instagram"
                            elif platform_name == "facebook":
                                platform_name = "Facebook"
                            elif platform_name == "linkedin":
                                platform_name = "LinkedIn"
                            elif platform_name == "tiktok":
                                platform_name = "TikTok"
                            
                            if platform_name not in platforms:
                                platforms[platform_name] = []
                            platforms[platform_name].append(account)
                        
                        # عرض الحسابات مجمعة حسب المنصة
                        for platform_name, platform_accounts in platforms.items():
                            accounts_msg += f"\n🌐 **{platform_name}:**\n"
                            for account in platform_accounts:
                                accounts_msg += f"  • 👤 {account.username}"
                                if account.last_used:
                                    from datetime import datetime
                                    last_used = account.last_used.strftime("%Y-%m-%d")
                                    accounts_msg += f" (آخر استخدام: {last_used})"
                                accounts_msg += "\n"
                    
                    if extra_cookie_accounts:
                        accounts_msg += f"\n🌐 **X (Twitter) — من الكوكيز:**\n"
                        for uname in sorted(extra_cookie_accounts):
                            accounts_msg += f"  • 👤 {uname}\n"
                    
                    total = len(db_accounts) + len(extra_cookie_accounts)
                    accounts_msg += f"\n✅ لديك {total} حساب نشط"
                else:
                    accounts_msg = "⚠️ لا توجد حسابات محفوظة حالياً.\n\nيمكنك إضافة حساب بقول: سجل دخول اليوزر [username] الباسورد [password]"
                
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db, conversation_id=conversation_id,
                            role="assistant", content=accounts_msg,
                            intent=intent, confidence=confidence, agent="Main_Agent"
                        )
                    except: pass
                
                return {
                    "success": True,
                    "message": accounts_msg,
                    "intent_result": intent_result,
                    "agent": "Main_Agent",
                    "conversation_id": conversation_id
                }
            
            else:
                # ميزة غير متاحة
                print(f"[DEBUG] Feature not available: {intent}")
                return {
                    "success": False,
                    "message": None,  # لا رد تلقائي
                    "intent_result": intent_result
                }
        
        except Exception as e:
            # في حالة الخطأ، سجل الخطأ
            print(f"[ERROR] Main Agent error: {str(e)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": None,  # لا رد تلقائي
                "error": str(e)
            }

    # ─────────────────── توليد الهوية الوهمية ───────────────────
    def _handle_generate_identity(self, message: str, entities: Dict[str, Any]) -> str:
        """ينشئ هوية وهمية عبر سيرفر app/identity"""
        from app.services import identity_bridge

        # تأكد أن السيرفر شغّال
        try:
            identity_bridge.start_identity_server()
        except Exception as e:
            return f"⚠️ فشل تشغيل سيرفر توليد الهويات: {e}"

        # هل المستخدم يبي صور؟ (افتراضي: نعم)
        with_images = entities.get("with_images")
        if with_images is None:
            # لو ما حدد، نفترض نعم (الميزة الكاملة)
            with_images = True

        # حدّد لو هو طلب عشوائي بحت أو محدد
        has_specifics = any(entities.get(k) for k in
                            ["gender", "nationality", "orientation",
                             "bio_length", "skin_tone"])

        try:
            if not has_specifics:
                # طلب عشوائي
                if with_images:
                    result = identity_bridge.generate_random_profile_with_images()
                else:
                    result = identity_bridge.generate_random_profile()
            else:
                # طلب بمعايير
                params = {
                    "description": message[:200],
                    "nationality": entities.get("nationality", "سعودي"),
                    "orientation": entities.get("orientation", "عام"),
                    "bioLength": entities.get("bio_length", "متوسط"),
                    "imageType": "شخص",
                    "headerImageType": "طبيعة",
                    "gender": entities.get("gender", "رجل"),
                    "skinTone": entities.get("skin_tone", "حنطي"),
                    "headerText": "",
                    "bioStyle": "فصحى",
                    "useCustomPrompts": False,
                    "customProfilePicPrompt": "",
                    "customHeaderImagePrompt": "",
                }
                result = identity_bridge.generate_profile(params, with_images=with_images)
        except Exception as e:
            return f"⚠️ فشل توليد الهوية: {e}"

        if not result.get("success"):
            return f"⚠️ فشل توليد الهوية: {result.get('error', 'خطأ غير معروف')}"

        data = result.get("data", {})

        # بناء الرد
        lines = ["✅ **تم توليد هوية وهمية جديدة:**", ""]
        if data.get("name"):
            lines.append(f"👤 **الاسم:** {data['name']}")
        if data.get("username"):
            lines.append(f"🆔 **اليوزرنيم:** @{data['username']}")
        if data.get("bio"):
            lines.append(f"📝 **البايو:** {data['bio']}")
        if data.get("location"):
            lines.append(f"📍 **الموقع:** {data['location']}")
        if data.get("website"):
            lines.append(f"🔗 **الويبسايت:** {data['website']}")
        if data.get("bornDate"):
            lines.append(f"🎂 **تاريخ الميلاد:** {data['bornDate']}")
        if data.get("joinDate"):
            lines.append(f"📅 **تاريخ الانضمام:** {data['joinDate']}")

        followers = data.get("followers")
        following = data.get("following")
        if followers is not None or following is not None:
            lines.append(f"👥 **المتابعون:** {followers:,} | **يتابع:** {following:,}")

        if data.get("profilePictureUrl"):
            lines.append(f"🖼️ **الصورة الشخصية:** {data['profilePictureUrl']}")
        if data.get("headerImageUrl"):
            lines.append(f"🎨 **صورة الغلاف:** {data['headerImageUrl']}")

        lines.append("")
        lines.append("💡 لتطبيق هذه الهوية على حساب X مسجّل لديك، اكتب:")
        if data.get("name") and data.get("bio"):
            lines.append(
                f"`غيّر الاسم إلى \"{data['name']}\" والبايو إلى \"{data['bio'][:60]}...\"`"
            )

        return "\n".join(lines)
