#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
خدمة إدارة الحسابات الاجتماعية
Social Accounts Management Service
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from pathlib import Path
import json

from app.db.models import SocialAccount, User
from app.db.database import get_db


class AccountService:
    """خدمة إدارة حسابات وسائل التواصل الاجتماعي"""
    
    @staticmethod
    def create_account(
        db: Session,
        user_id: int,
        platform: str,
        username: str,
        display_name: Optional[str] = None,
        account_label: Optional[str] = None,
        cookie_filename: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> SocialAccount:
        """
        إنشاء حساب جديد
        
        Args:
            db: جلسة قاعدة البيانات
            user_id: معرف المستخدم
            platform: المنصة (x, instagram, facebook, etc.)
            username: اسم المستخدم
            display_name: الاسم المعروض
            account_label: تسمية مخصصة
            cookie_filename: اسم ملف الكوكيز
            metadata: معلومات إضافية
            
        Returns:
            الحساب المُنشأ
        """
        account = SocialAccount(
            user_id=user_id,
            platform=platform.lower(),
            username=username,
            display_name=display_name or username,
            account_label=account_label or username,
            cookie_filename=cookie_filename,
            status="active",
            last_login=datetime.utcnow(),
            extra_metadata=json.dumps(metadata) if metadata else None
        )
        
        db.add(account)
        db.commit()
        db.refresh(account)
        
        return account
    
    @staticmethod
    def get_account_by_id(db: Session, account_id: int) -> Optional[SocialAccount]:
        """الحصول على حساب بواسطة المعرف"""
        return db.query(SocialAccount).filter(SocialAccount.id == account_id).first()
    
    @staticmethod
    def get_user_accounts(
        db: Session,
        user_id: int,
        platform: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[SocialAccount]:
        """
        الحصول على حسابات المستخدم
        
        Args:
            db: جلسة قاعدة البيانات
            user_id: معرف المستخدم
            platform: تصفية حسب المنصة (اختياري)
            status: تصفية حسب الحالة (اختياري)
            
        Returns:
            قائمة الحسابات
        """
        query = db.query(SocialAccount).filter(SocialAccount.user_id == user_id)
        
        if platform:
            query = query.filter(SocialAccount.platform == platform.lower())
        
        if status:
            query = query.filter(SocialAccount.status == status)
        
        return query.order_by(desc(SocialAccount.created_at)).all()
    
    @staticmethod
    def get_account_by_username(
        db: Session,
        user_id: int,
        platform: str,
        username: str
    ) -> Optional[SocialAccount]:
        """الحصول على حساب بواسطة اسم المستخدم"""
        return db.query(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            SocialAccount.platform == platform.lower(),
            SocialAccount.username == username
        ).first()
    
    @staticmethod
    def update_account(
        db: Session,
        account_id: int,
        **kwargs
    ) -> Optional[SocialAccount]:
        """
        تحديث معلومات الحساب
        
        Args:
            db: جلسة قاعدة البيانات
            account_id: معرف الحساب
            **kwargs: الحقول المراد تحديثها
            
        Returns:
            الحساب المحدث
        """
        account = db.query(SocialAccount).filter(SocialAccount.id == account_id).first()
        
        if not account:
            return None
        
        for key, value in kwargs.items():
            if hasattr(account, key):
                setattr(account, key, value)
        
        account.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(account)
        
        return account
    
    @staticmethod
    def update_account_status(
        db: Session,
        account_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[SocialAccount]:
        """تحديث حالة الحساب"""
        return AccountService.update_account(
            db,
            account_id,
            status=status,
            error_message=error_message,
            updated_at=datetime.utcnow()
        )
    
    @staticmethod
    def mark_account_used(db: Session, account_id: int) -> Optional[SocialAccount]:
        """تحديث وقت آخر استخدام للحساب"""
        return AccountService.update_account(
            db,
            account_id,
            last_used=datetime.utcnow()
        )
    
    @staticmethod
    def delete_account(db: Session, account_id: int, user_id: int) -> bool:
        """
        حذف حساب
        
        Args:
            db: جلسة قاعدة البيانات
            account_id: معرف الحساب
            user_id: معرف المستخدم (للتحقق من الصلاحية)
            
        Returns:
            True إذا تم الحذف بنجاح
        """
        print(f"[DEBUG] delete_account called: account_id={account_id}, user_id={user_id}")
        
        account = db.query(SocialAccount).filter(
            SocialAccount.id == account_id,
            SocialAccount.user_id == user_id
        ).first()
        
        if not account:
            print(f"[ERROR] Account not found: account_id={account_id}, user_id={user_id}")
            return False
        
        print(f"[DEBUG] Found account to delete: id={account.id}, username={account.username}, platform={account.platform}")
        
        # حذف ملف الكوكيز إذا كان موجوداً
        if account.cookie_filename:
            try:
                cookie_path = Path(__file__).parent.parent / "x" / "cookies" / account.cookie_filename
                if cookie_path.exists():
                    cookie_path.unlink()
                    print(f"[DEBUG] Deleted cookie file: {account.cookie_filename}")
            except Exception as e:
                print(f"[WARNING] Failed to delete cookie file: {e}")
        
        # حذف من قاعدة البيانات
        print(f"[DEBUG] Deleting account from database...")
        db.delete(account)
        db.commit()
        print(f"[DEBUG] Account deleted and committed successfully")
        
        return True
    
    @staticmethod
    def get_all_accounts_admin(
        db: Session,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        الحصول على جميع الحسابات (للإدارة)
        
        Args:
            db: جلسة قاعدة البيانات
            platform: تصفية حسب المنصة
            status: تصفية حسب الحالة
            limit: الحد الأقصى للنتائج
            
        Returns:
            قائمة الحسابات مع معلومات المستخدمين
        """
        query = db.query(SocialAccount, User).join(
            User, SocialAccount.user_id == User.id
        )
        
        if platform:
            query = query.filter(SocialAccount.platform == platform.lower())
        
        if status:
            query = query.filter(SocialAccount.status == status)
        
        results = query.order_by(desc(SocialAccount.created_at)).limit(limit).all()
        
        accounts = []
        for account, user in results:
            accounts.append({
                "id": account.id,
                "user_id": account.user_id,
                "user_email": user.email,
                "user_name": user.name,
                "platform": account.platform,
                "username": account.username,
                "display_name": account.display_name,
                "account_label": account.account_label,
                "status": account.status,
                "last_login": account.last_login.isoformat() if account.last_login else None,
                "last_used": account.last_used.isoformat() if account.last_used else None,
                "error_message": account.error_message,
                "created_at": account.created_at.isoformat(),
                "updated_at": account.updated_at.isoformat()
            })
        
        return accounts
    
    @staticmethod
    def get_account_stats(db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        الحصول على إحصائيات الحسابات
        
        Args:
            db: جلسة قاعدة البيانات
            user_id: معرف المستخدم (اختياري، للإحصائيات الشخصية)
            
        Returns:
            إحصائيات الحسابات
        """
        query = db.query(SocialAccount)
        
        if user_id:
            query = query.filter(SocialAccount.user_id == user_id)
        
        total = query.count()
        active = query.filter(SocialAccount.status == "active").count()
        inactive = query.filter(SocialAccount.status == "inactive").count()
        expired = query.filter(SocialAccount.status == "expired").count()
        error = query.filter(SocialAccount.status == "error").count()
        
        # إحصائيات حسب المنصة
        platforms = {}
        for platform in ["x", "instagram", "facebook", "linkedin", "tiktok"]:
            count = query.filter(SocialAccount.platform == platform).count()
            if count > 0:
                platforms[platform] = count
        
        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "expired": expired,
            "error": error,
            "by_platform": platforms
        }


# إنشاء instance عام
account_service = AccountService()
