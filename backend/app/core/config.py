import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


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


settings = Settings()
