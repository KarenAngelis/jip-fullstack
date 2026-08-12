# app/models/pauta.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float
from sqlalchemy.sql import func

# ✅ use a MESMA Base do engine/SessionLocal
from app.database.database import Base


class Pauta(Base):
    __tablename__ = "pautas"

    id = Column(Integer, primary_key=True, index=True)
    tema = Column(String(200), nullable=False, index=True)
    duracao_min = Column(Integer, nullable=False)
    status = Column(String(50), default="ativo")  # ativo, arquivado, excluido

    # Dados estruturados
    resumo_executivo = Column(JSON)       # List[str]
    titulos_sugeridos = Column(JSON)      # List[str]
    perguntas_sugeridas = Column(JSON)    # List[str]
    artigos_referencia = Column(JSON)     # List[ArtigoRef]
    trends_detalhadas = Column(JSON)      # TrendsDetalhadas
    deep_research = Column(JSON)          # DeepResearch
    roteiro_estruturado = Column(JSON)    # RoteiroEstruturado

    # Métricas para busca e ordenação
    volume_busca_mensal = Column(Integer, default=0)
    popularidade_score = Column(Integer, default=0)
    crescimento_30_dias = Column(Float, default=0.0)
    tendencia = Column(String(20))  # crescendo, estável, declinando

    # Metadados
    user_id = Column(Integer, nullable=True)  # futuro: multiuser
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Pauta(id={self.id}, tema='{self.tema}', duracao={self.duracao_min}min)>"
