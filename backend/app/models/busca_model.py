# app/models/busca_model.py

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from ..database.database import Base

class BuscaArtigos(Base):
    __tablename__ = "buscas_artigos"
    
    id = Column(Integer, primary_key=True, index=True)
    tema = Column(String, index=True, nullable=False)
    usuario_ip = Column(String, nullable=True)  # Para analytics
    data_busca = Column(DateTime(timezone=True), server_default=func.now())
    
    # Armazenar dados das tendências
    tendencias_data = Column(JSON, nullable=True)
    noticias_data = Column(JSON, nullable=True)
    resumo_ia = Column(Text, nullable=True)
    
    # Resultados gerados
    artigos_gerados = Column(JSON, nullable=False)
    total_artigos = Column(Integer, default=0)
    
    # Status e metadata
    status_processamento = Column(String, default="sucesso")  # sucesso, erro, cache
    tempo_processamento = Column(Integer, nullable=True)  # em milissegundos
    
    class Config:
        from_attributes = True