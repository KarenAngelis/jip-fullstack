# app/services/threads_database_service.py
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import logging

from app.database.database import get_db
from app.models.threads_model import ThreadsSearch, ThreadsPost, ThreadsTrend

logger = logging.getLogger(__name__)

class ThreadsDatabaseService:
    
    def __init__(self, db: Session):
        self.db = db
    
    # === HISTÓRICO DE BUSCAS ===
    
    def save_search(self, query: str, search_type: str, user_id: Optional[str] = None, 
                   results_count: int = 0, limit_requested: int = 10) -> ThreadsSearch:
        """Salva uma busca no histórico"""
        
        search = ThreadsSearch(
            query=query,
            search_type=search_type,
            user_id=user_id,
            limit_requested=limit_requested,
            results_count=results_count
        )
        
        self.db.add(search)
        self.db.commit()
        self.db.refresh(search)
        
        logger.info(f"Busca salva: {query} ({search_type})")
        return search
    
    def get_recent_searches(self, limit: int = 10, search_type: Optional[str] = None) -> List[ThreadsSearch]:
        """Busca as pesquisas mais recentes"""
        
        query = self.db.query(ThreadsSearch)
        
        if search_type:
            query = query.filter(ThreadsSearch.search_type == search_type)
        
        return query.order_by(ThreadsSearch.created_at.desc()).limit(limit).all()
    
    def get_popular_searches(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """Busca os termos mais populares dos últimos dias"""
        
        since_date = datetime.now() - timedelta(days=days)
        
        results = self.db.query(
            ThreadsSearch.query,
            self.db.func.count(ThreadsSearch.query).label('count')
        ).filter(
            ThreadsSearch.created_at >= since_date
        ).group_by(
            ThreadsSearch.query
        ).order_by(
            self.db.func.count(ThreadsSearch.query).desc()
        ).limit(limit).all()
        
        return [{"query": r.query, "count": r.count} for r in results]
    
    # === CACHE DE POSTS ===
    
    def save_posts(self, posts: List[Dict[str, Any]]) -> List[ThreadsPost]:
        """Salva posts no banco (com upsert)"""
        
        saved_posts = []
        
        for post_data in posts:
            # Verifica se já existe
            existing = self.db.query(ThreadsPost).filter(
                ThreadsPost.thread_id == post_data.get('id')
            ).first()
            
            if existing:
                # Atualiza métricas
                existing.like_count = post_data.get('like_count', 0)
                existing.reply_count = post_data.get('reply_count', 0)
                existing.quotes_count = post_data.get('quotes_count', 0)
                existing.engagement_rate = post_data.get('engagement_rate', 0.0)
                existing.updated_at = datetime.now()
                saved_posts.append(existing)
            else:
                # Cria novo
                new_post = ThreadsPost(
                    thread_id=post_data.get('id'),
                    username=post_data.get('username'),
                    text=post_data.get('text'),
                    media_type=post_data.get('media_type'),
                    media_url=post_data.get('media_url'),
                    permalink=post_data.get('permalink'),
                    like_count=post_data.get('like_count', 0),
                    reply_count=post_data.get('reply_count', 0),
                    quotes_count=post_data.get('quotes_count', 0),
                    engagement_rate=post_data.get('engagement_rate', 0.0),
                    is_reply=post_data.get('is_reply', False),
                    thread_timestamp=post_data.get('timestamp'),
                    extra_data=post_data
                )
                
                self.db.add(new_post)
                saved_posts.append(new_post)
        
        self.db.commit()
        logger.info(f"Salvos {len(saved_posts)} posts no banco")
        
        return saved_posts
    
    def get_cached_posts(self, query: str, hours: int = 1, limit: int = 10) -> List[ThreadsPost]:
        """Busca posts em cache (recentes)"""
        
        since_time = datetime.now() - timedelta(hours=hours)
        
        # Busca posts que contenham o termo no texto
        return self.db.query(ThreadsPost).filter(
            ThreadsPost.text.contains(query),
            ThreadsPost.created_at >= since_time
        ).order_by(ThreadsPost.engagement_rate.desc()).limit(limit).all()
    
    def get_top_posts(self, hours: int = 24, limit: int = 10) -> List[ThreadsPost]:
        """Busca posts com maior engagement"""
        
        since_time = datetime.now() - timedelta(hours=hours)
        
        return self.db.query(ThreadsPost).filter(
            ThreadsPost.created_at >= since_time
        ).order_by(ThreadsPost.engagement_rate.desc()).limit(limit).all()
    
    # === TRENDING TOPICS ===
    
    def save_trending_topic(self, topic: str, category: Optional[str] = None, 
                          posts_count: int = 0, engagement_score: float = 0.0,
                          keywords: List[str] = None) -> ThreadsTrend:
        """Salva/atualiza um trending topic"""
        
        # Verifica se já existe hoje
        today = datetime.now().date()
        existing = self.db.query(ThreadsTrend).filter(
            ThreadsTrend.topic == topic,
            self.db.func.date(ThreadsTrend.trend_date) == today
        ).first()
        
        if existing:
            # Atualiza
            existing.posts_count = posts_count
            existing.engagement_score = engagement_score
            existing.related_keywords = keywords
            existing.is_active = True
            trend = existing
        else:
            # Cria novo
            trend = ThreadsTrend(
                topic=topic,
                category=category,
                posts_count=posts_count,
                engagement_score=engagement_score,
                related_keywords=keywords
            )
            self.db.add(trend)
        
        self.db.commit()
        self.db.refresh(trend)
        
        return trend
    
    def get_trending_topics(self, days: int = 1, limit: int = 10) -> List[ThreadsTrend]:
        """Busca trending topics"""
        
        since_date = datetime.now() - timedelta(days=days)
        
        return self.db.query(ThreadsTrend).filter(
            ThreadsTrend.trend_date >= since_date,
            ThreadsTrend.is_active == True
        ).order_by(ThreadsTrend.engagement_score.desc()).limit(limit).all()
    
    # === ANALYTICS ===
    
    def get_search_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Analytics das buscas"""
        
        since_date = datetime.now() - timedelta(days=days)
        
        total_searches = self.db.query(ThreadsSearch).filter(
            ThreadsSearch.created_at >= since_date
        ).count()
        
        search_types = self.db.query(
            ThreadsSearch.search_type,
            self.db.func.count(ThreadsSearch.search_type).label('count')
        ).filter(
            ThreadsSearch.created_at >= since_date
        ).group_by(ThreadsSearch.search_type).all()
        
        popular_queries = self.get_popular_searches(days, 5)
        
        return {
            "total_searches": total_searches,
            "search_types": [{"type": s.search_type, "count": s.count} for s in search_types],
            "popular_queries": popular_queries,
            "period_days": days
        }

# Função helper para usar nos endpoints
def get_threads_db_service(db: Session = None) -> ThreadsDatabaseService:
    """Retorna instância do serviço de banco"""
    if db is None:
        db = next(get_db())
    return ThreadsDatabaseService(db)