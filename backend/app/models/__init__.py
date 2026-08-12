from .busca_model import BuscaArtigos
from .user_model import User
from .title_generation_model import TitleGeneration
from .episode_suggestion_model import EpisodeSuggestionBatch, EpisodeSuggestion
from .account_settings_model import AccountSettings, PersonType  # ← NOVO

__all__ = [
    "BuscaArtigos",
    "User",
    "TitleGeneration",
    "EpisodeSuggestionBatch",
    "EpisodeSuggestion",
    "AccountSettings",           # ← NOVO
    "PersonType",                # ← NOVO
]
