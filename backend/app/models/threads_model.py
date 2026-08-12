# app/models/threads_model.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.sql import func
from app.database.database import Base

class ThreadsSearch(Base):
    """Histórico de buscas no Threads"""
    __tablename__ = "threads_searches"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(255), nullable=False, index=True)
    search_type = Column(String(50), nullable=False)  # trending, user, search
    user_id = Column(String(100), nullable=True)  # ID do usuário que fez a busca
    limit_requested = Column(Integer, default=10)
    results_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ThreadsPost(Base):
    """Posts do Threads salvos no banco"""
    __tablename__ = "threads_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(100), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False, index=True)
    text = Column(Text, nullable=True)
    media_type = Column(String(20), nullable=True)
    media_url = Column(Text, nullable=True)
    permalink = Column(Text, nullable=False)
    
    # Métricas de engagement
    like_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    quotes_count = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    
    # Metadados
    is_reply = Column(Boolean, default=False)
    thread_timestamp = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # CORREÇÃO: mudou de 'metadata' para 'extra_data'
    extra_data = Column(JSON, nullable=True)

class ThreadsTrend(Base):
    """Trending topics do Threads"""
    __tablename__ = "threads_trends"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=True)  # ai, tech, startup, etc.
    posts_count = Column(Integer, default=0)
    engagement_score = Column(Float, default=0.0)
    trend_date = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Dados do trending
    related_keywords = Column(JSON, nullable=True)  # ["ai", "chatgpt", "machine learning"]
    sample_posts = Column(JSON, nullable=True)  # IDs de posts exemplo