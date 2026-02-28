from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base
import json


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    profile_picture = Column(String(500), nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with X accounts
    x_accounts = relationship("XAccount", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class XAccount(Base):
    __tablename__ = "x_accounts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    username = Column(String(255), nullable=False, index=True)
    encrypted_credentials = Column(Text, nullable=True)
    status = Column(String(50), default="active")  # active, inactive, suspended
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with User
    user = relationship("User", back_populates="x_accounts")
    
    def __repr__(self):
        return f"<XAccount(id={self.id}, username={self.username}, status={self.status})>"


class SocialAccount(Base):
    """حسابات وسائل التواصل الاجتماعي - دعم منصات متعددة"""
    __tablename__ = "social_accounts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform = Column(String(50), nullable=False, index=True)  # x, instagram, facebook, linkedin, tiktok
    username = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    account_label = Column(String(255), nullable=True)  # اسم مخصص للحساب
    cookie_filename = Column(String(255), nullable=True)  # اسم ملف الكوكيز
    status = Column(String(50), default="active")  # active, inactive, expired, error
    last_login = Column(DateTime, nullable=True)
    last_used = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    extra_metadata = Column(Text, nullable=True)  # JSON لمعلومات إضافية
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SocialAccount(id={self.id}, platform={self.platform}, username={self.username}, status={self.status})>"


class Conversation(Base):
    """محادثة مع المستخدم"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(255), nullable=True, index=True)
    title = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with messages
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title={self.title})>"


class Message(Base):
    """رسالة في المحادثة"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    confidence = Column(String(10), nullable=True)
    agent = Column(String(100), nullable=True)
    extra_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with conversation
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, content={self.content[:50]}...)>"


class ScheduleEvent(Base):
    """حدث مجدول للنشر على وسائل التواصل الاجتماعي"""
    __tablename__ = "schedule_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    schedule_event_id = Column(String(64), unique=True, index=True, nullable=False)
    platform = Column(String(50), nullable=False)
    username = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    run_at = Column(DateTime, nullable=False)
    intent_time = Column(String(50), nullable=False)
    mood = Column(String(50), nullable=False)
    status = Column(String(50), default="SCHEDULED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        from zoneinfo import ZoneInfo
        ksa = ZoneInfo("Asia/Riyadh")
        run_at_ksa = self.run_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(ksa) if self.run_at else None
        return {
            "schedule_event_id": self.schedule_event_id,
            "platform": self.platform,
            "username": self.username,
            "category": self.category,
            "content": self.content,
            "run_at": run_at_ksa.isoformat() if run_at_ksa else None,
            "intent_time": self.intent_time,
            "mood": self.mood,
            "status": self.status,
        }

    def __repr__(self):
        return f"<ScheduleEvent(id={self.schedule_event_id}, status={self.status}, run_at={self.run_at})>"
