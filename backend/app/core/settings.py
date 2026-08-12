import os
from dotenv import load_dotenv

# Carrega variáveis do .env uma única vez
load_dotenv()

class Settings:
    def __init__(self):
        # Variáveis padrão do projeto
        self.JIP_DEFAULT_GEO = os.getenv("JIP_DEFAULT_GEO", "BR")
        self.JIP_DEFAULT_TIMEFRAME = os.getenv("JIP_DEFAULT_TIMEFRAME", "now 7-d")

        # Provedor de LLM (mock, openai, etc.)
        self.JIP_LLM_PROVIDER = os.getenv("JIP_LLM_PROVIDER", "mock")

        # Chaves de APIs externas
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.CORE_API_KEY = os.getenv("CORE_API_KEY")
        self.YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

        # Banco de dados e segurança
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jip_api.db")
        self.SECRET_KEY = os.getenv("SECRET_KEY", "changeme")

        # Validação rápida para debug
        if not self.OPENAI_API_KEY:
            print("⚠️  Atenção: OPENAI_API_KEY não encontrada no .env")
        else:
            print("✅ OPENAI_API_KEY carregada com sucesso.")

# Instância global de settings
settings = Settings()
