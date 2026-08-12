from sqlalchemy import Column, Integer, String, DateTime, func
from app.database.database import Base

class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(255), index=True, nullable=False)      # título do tópico
    source = Column(String(50), default="google_trends")          # origem
    region = Column(String(10), default="BR")                     # país
    rank = Column(Integer, nullable=True)                         # posição (se houver)
    score = Column(Integer, nullable=True)                        # pontuação relativa (se houver)
    captured_at = Column(DateTime, server_default=func.now(), nullable=False)
