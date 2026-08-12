# app/models/title_generation_model.py

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, Boolean
from sqlalchemy.sql import func
from ..database.database import Base

class TitleGeneration(Base):
    __tablename__ = "title_generations"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True, nullable=False)
    usuario_ip = Column(String, nullable=True)  # Para analytics
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Parâmetros da geração (compatível com TitleGenerationRequest)
    audience = Column(String, nullable=False)  # iniciantes, intermediario, avancado, geral
    content_type = Column(String, nullable=False)  # tutorial, lista, guia, review, etc
    tone = Column(String, nullable=False)  # divertido, profissional, casual, inspirador, provocativo
    quantity = Column(Integer, default=5)
    max_length = Column(Integer, default=60)
    
    # Flags de configuração
    use_trends = Column(Boolean, default=True)
    include_numbers = Column(Boolean, default=True)
    include_power_words = Column(Boolean, default=True)
    
    # Resultados gerados (array de objetos GeneratedTitle)
    # Formato: [{"title": "...", "scores": {...}, "trends_used": [...], "power_words": [...]}]
    titles_generated = Column(JSON, nullable=False)
    total_titles = Column(Integer, default=0)
    
    # Trends encontradas (array de strings)
    trends_found = Column(JSON, nullable=True)
    
    # Melhor título (o com maior overall score)
    best_title = Column(Text, nullable=True)
    best_score = Column(Integer, nullable=True)
    
    # Métricas de tokens e performance
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    generation_time = Column(Float, nullable=True)  # em segundos
    
    # Status
    status = Column(String, default="success")  # success, error, partial
    error_message = Column(Text, nullable=True)
    
    class Config:
        from_attributes = True