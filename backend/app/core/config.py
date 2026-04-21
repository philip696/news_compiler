import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class Settings:
    app_name: str = os.getenv("APP_NAME", "Personalized News Aggregation MVP")
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    learning_rate: float = float(os.getenv("LEARNING_RATE", "0.02"))
    decay_factor: float = float(os.getenv("DECAY_FACTOR", "0.995"))
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
    top_n_stories: int = int(os.getenv("TOP_N_STORIES", "30"))
    dataset_path: str = os.getenv("DATASET_PATH", str(Path(__file__).parent.parent.parent / "data" / "webhose_sample" / "news.jsonl"))
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # AI Service (DeepSeek — OpenAI-compatible chat API)
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    # WeChat OAuth Configuration
    WECHAT_APP_ID: str = os.getenv("WECHAT_APP_ID", "")
    WECHAT_APP_SECRET: str = os.getenv("WECHAT_APP_SECRET", "")
    OAUTH_CALLBACK_URL: str = os.getenv("OAUTH_CALLBACK_URL", "http://localhost:8000/api/wechat-auth/callback")
    OAUTH_STATE_TTL: int = int(os.getenv("OAUTH_STATE_TTL", "600"))  # 10 minutes
    TOKEN_REFRESH_BUFFER: int = int(os.getenv("TOKEN_REFRESH_BUFFER", "1800"))  # 30 minutes
    TOKEN_REFRESH_INTERVAL: int = int(os.getenv("TOKEN_REFRESH_INTERVAL", "3600"))  # 1 hour
    
    # RSS Service Configuration
    WEWE_RSS_URL: str = os.getenv("WEWE_RSS_URL", "http://localhost:4000")
    WEWE_RSS_AUTH_CODE: str = os.getenv("WEWE_RSS_AUTH_CODE", "")


settings = Settings()
