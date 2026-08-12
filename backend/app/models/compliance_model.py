# app/models/compliance_model.py
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from ..database.database import Base

class ComplianceAnalysisLog(Base):
    __tablename__ = "compliance_analysis_logs"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # dados da requisição
    request_id = sa.Column(UUID(as_uuid=True), nullable=False, index=True)
    content = sa.Column(sa.Text, nullable=False)
    context_area = sa.Column(sa.String(120), nullable=False, default="geral")
    specific_laws = sa.Column(JSONB, nullable=True)
    company_info = sa.Column(JSONB, nullable=True)

    # resultado
    status = sa.Column(sa.String(50), nullable=False)                 # ex.: "compliant", "non_compliant", "needs_review"
    confidence_score = sa.Column(sa.Float, nullable=True)
    risk_level = sa.Column(sa.String(50), nullable=True)              # ex.: "low", "medium", "high"
    summary = sa.Column(sa.Text, nullable=True)

    violations = sa.Column(JSONB, nullable=True, default=list)        # lista de strings/objetos
    recommendations = sa.Column(JSONB, nullable=True, default=list)
    detailed_analysis = sa.Column(JSONB, nullable=True)
    legal_sources = sa.Column(JSONB, nullable=True)                   # lista de dicts

    created_at = sa.Column(sa.DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        sa.Index("ix_compliance_user_created_at", "user_id", "created_at"),
        sa.Index("ix_compliance_request_id", "request_id"),
    )

    def __repr__(self) -> str:
        return f"<ComplianceAnalysisLog id={self.id} user_id={self.user_id} status={self.status}>"
