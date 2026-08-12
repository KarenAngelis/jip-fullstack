# app/models/episode_suggestion_model.py
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.database import Base

class EpisodeSuggestionBatch(Base):
    """Batch de geração de episódios (1 request = 1 batch = 12 episódios)"""
    __tablename__ = "episode_suggestions_batches"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)  # futuro: FK para users
    user_ip = Column(String, nullable=True)
    
    # Request original
    request_title = Column(String(200), nullable=False, index=True)
    request_context = Column(Text, nullable=True)
    request_personal_input = Column(Text, nullable=True)
    request_target_audience = Column(String(50), default="geral")
    request_episode_format = Column(String(50), default="entrevista")
    
    # Métricas gerais do batch
    total_suggestions = Column(Integer, default=12)
    overall_trend_score = Column(Float, default=0.0)
    market_opportunity = Column(String(200), nullable=True)
    recommended_timing = Column(String(100), nullable=True)
    
    # Performance
    processing_time_ms = Column(Float, default=0.0)
    status = Column(String(20), default="success")  # success, error, partial
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamento
    episodes = relationship("EpisodeSuggestion", back_populates="batch", cascade="all, delete-orphan")
    
    class Config:
        from_attributes = True


class EpisodeSuggestion(Base):
    """Episódio individual gerado"""
    __tablename__ = "episode_suggestions"
    
    # PK é o UUID gerado pelo service
    id = Column(String(36), primary_key=True, index=True)  # UUID
    batch_id = Column(Integer, ForeignKey("episode_suggestions_batches.id"), nullable=False, index=True)
    
    # Dados básicos
    title = Column(String(250), nullable=False)
    short_description = Column(Text, nullable=False)
    keywords = Column(JSON, nullable=False)  # List[str]
    
    # Métricas
    success_probability = Column(Float, default=0.0)
    estimated_duration = Column(Integer, default=45)
    difficulty_level = Column(String(50), default="intermediário")
    target_audience = Column(String(50), default="geral")
    
    # Análises JIP (JSON completo)
    jip_trend_analysis = Column(JSON, nullable=False)
    jip_legal_analysis = Column(JSON, nullable=False)
    jip_market_analysis = Column(JSON, nullable=False)
    
    # Sugestões e notícias (JSON arrays)
    guest_suggestions = Column(JSON, nullable=True)  # List[GuestSuggestion]
    episode_news = Column(JSON, nullable=True)  # List[EpisodeNews]
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamento
    batch = relationship("EpisodeSuggestionBatch", back_populates="episodes")
    
    class Config:
        from_attributes = True