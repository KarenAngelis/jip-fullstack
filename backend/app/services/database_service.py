# app/services/database_service.py

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional, Dict  # ← ADICIONE Dict AQUI
from datetime import datetime, timedelta
import time

from ..models.busca_model import BuscaArtigos
from ..schemas.busca_schema import BuscaArtigosCreate, BuscaArtigosResponse, BuscaHistoricoResponse

class DatabaseService:
    """Serviço para operações do banco de dados"""
    
    @staticmethod
    def salvar_busca(db: Session, busca_data: BuscaArtigosCreate) -> BuscaArtigos:
        """Salva uma nova busca no banco"""
        try:
            db_busca = BuscaArtigos(
                tema=busca_data.tema,
                usuario_ip=busca_data.usuario_ip,
                tendencias_data=busca_data.tendencias_data,
                noticias_data=busca_data.noticias_data,
                resumo_ia=busca_data.resumo_ia,
                artigos_gerados=busca_data.artigos_gerados,
                total_artigos=busca_data.total_artigos,
                status_processamento=busca_data.status_processamento,
                tempo_processamento=busca_data.tempo_processamento
            )
            
            db.add(db_busca)
            db.commit()
            db.refresh(db_busca)
            
            print(f"✅ Busca salva no banco: ID {db_busca.id}")
            return db_busca
            
        except Exception as e:
            print(f"❌ Erro ao salvar busca: {e}")
            db.rollback()
            raise e
    
    @staticmethod
    def buscar_cache(db: Session, tema: str, horas_validas: int = 24) -> Optional[BuscaArtigos]:
        """Verifica se existe busca em cache (últimas X horas)"""
        try:
            tempo_limite = datetime.utcnow() - timedelta(hours=horas_validas)
            
            busca_cache = db.query(BuscaArtigos).filter(
                BuscaArtigos.tema.ilike(f"%{tema}%"),
                BuscaArtigos.data_busca >= tempo_limite,
                BuscaArtigos.status_processamento == "sucesso"
            ).order_by(desc(BuscaArtigos.data_busca)).first()
            
            if busca_cache:
                print(f"🎯 Cache encontrado para '{tema}': ID {busca_cache.id}")
                return busca_cache
            
            return None
            
        except Exception as e:
            print(f"❌ Erro ao buscar cache: {e}")
            return None
    
    @staticmethod
    def obter_historico(db: Session, limite: int = 20) -> List[BuscaArtigos]:
        """Obtém histórico de buscas"""
        try:
            historico = db.query(BuscaArtigos).order_by(
                desc(BuscaArtigos.data_busca)
            ).limit(limite).all()
            
            return historico
            
        except Exception as e:
            print(f"❌ Erro ao obter histórico: {e}")
            return []
    
    @staticmethod
    def obter_temas_populares(db: Session, dias: int = 30, limite: int = 10) -> List[Dict]:
        """Obtém temas mais populares"""
        try:
            tempo_limite = datetime.utcnow() - timedelta(days=dias)
            
            populares = db.query(
                BuscaArtigos.tema,
                func.count(BuscaArtigos.id).label('total_buscas'),
                func.max(BuscaArtigos.data_busca).label('ultima_busca')
            ).filter(
                BuscaArtigos.data_busca >= tempo_limite,
                BuscaArtigos.status_processamento == "sucesso"
            ).group_by(BuscaArtigos.tema).order_by(
                desc('total_buscas')
            ).limit(limite).all()
            
            resultado = []
            for tema, total, ultima in populares:
                resultado.append({
                    "tema": tema,
                    "total_buscas": total,
                    "ultima_busca": ultima
                })
            
            return resultado
            
        except Exception as e:
            print(f"❌ Erro ao obter temas populares: {e}")
            return []

# Funções helper
def criar_busca_dados(tema: str, artigos_data: List[Dict], tendencias=None, noticias=None, resumo=None, tempo_ms=None, ip=None) -> BuscaArtigosCreate:
    """Cria objeto BuscaArtigosCreate"""
    return BuscaArtigosCreate(
        tema=tema,
        usuario_ip=ip,
        tendencias_data=tendencias,
        noticias_data=noticias,
        resumo_ia=resumo,
        artigos_gerados=artigos_data,
        total_artigos=len(artigos_data),
        tempo_processamento=tempo_ms
    )