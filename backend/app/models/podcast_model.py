# app/models/podcast_model.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.database import Base

class PodcastScript(Base):
    """Roteiros de podcast gerados"""
    __tablename__ = "podcast_scripts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    subtitle = Column(String(500), nullable=True)
    duration_minutes = Column(Integer, default=30)  # Duração estimada
    
    # Estrutura do roteiro
    introduction = Column(Text, nullable=False)
    main_topics = Column(JSON, nullable=False)  # Lista de tópicos principais
    discussion_points = Column(JSON, nullable=False)  # Pontos de discussão
    conclusion = Column(Text, nullable=False)
    
    # Metadados
    target_audience = Column(String(100), nullable=True)  # tech, business, general
    difficulty_level = Column(String(20), default="intermediate")  # beginner, intermediate, advanced
    keywords = Column(JSON, nullable=True)  # Palavras-chave SEO
    
    # Dados das tendências usadas
    trending_topics_used = Column(JSON, nullable=True)  # IDs dos trending topics
    search_terms_used = Column(JSON, nullable=True)  # Termos de busca utilizados
    
    # Status e métricas
    status = Column(String(20), default="draft")  # draft, published, archived
    engagement_score = Column(Float, default=0.0)  # Score baseado nas trends
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<PodcastScript(title='{self.title}', duration={self.duration_minutes}min)>"

class PodcastEpisode(Base):
    """Episódios de podcast baseados em roteiros"""
    __tablename__ = "podcast_episodes"
    
    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("podcast_scripts.id"), nullable=False)
    
    # Dados do episódio
    episode_number = Column(Integer, nullable=True)
    season_number = Column(Integer, default=1)
    published_date = Column(DateTime(timezone=True), nullable=True)
    
    # Métricas de performance
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    
    # Plataformas
    platforms_published = Column(JSON, nullable=True)  # ["spotify", "youtube", "apple"]
    
    # Feedback e análise
    listener_feedback = Column(JSON, nullable=True)
    performance_metrics = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamento
    script = relationship("PodcastScript", backref="episodes")

class PodcastTemplate(Base):
    """Templates de roteiro reutilizáveis"""
    __tablename__ = "podcast_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Estrutura do template
    template_structure = Column(JSON, nullable=False)  # Estrutura base
    default_duration = Column(Integer, default=30)
    
    # Configurações
    category = Column(String(50), nullable=False)  # tech_news, interview, analysis
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TrendingTopicPodcast(Base):
    """Análise de trending topics para podcasts"""
    __tablename__ = "trending_topic_podcasts"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(255), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    
    # Análise do tópico
    relevance_score = Column(Float, default=0.0)  # 0-100
    podcast_potential = Column(Float, default=0.0)  # Potencial para podcast
    audience_interest = Column(Float, default=0.0)  # Interesse estimado da audiência
    
    # Dados das trends
    mentions_count = Column(Integer, default=0)
    engagement_total = Column(Integer, default=0)
    trend_velocity = Column(Float, default=0.0)  # Velocidade de crescimento
    
    # Análise de conteúdo
    key_discussion_points = Column(JSON, nullable=True)
    related_topics = Column(JSON, nullable=True)
    expert_sources = Column(JSON, nullable=True)  # Possíveis convidados/fontes
    
    # Histórico
    first_detected = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    is_trending = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<TrendingTopicPodcast(topic='{self.topic}', score={self.relevance_score})>"