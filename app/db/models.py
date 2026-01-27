from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


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
    category = Column(String(100), nullable=True, index=True)  # ترفيهي، سياسي، اقتصادي، تقني، رياضي، إخباري، فني، تعليمي
    nationality = Column(String(100), nullable=True, index=True)  # الجنسية: سعودي، مصري، إماراتي، أمريكي، إلخ
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
