import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    TIINGO_API_KEY: str = os.getenv("TIINGO_API_KEY", "")
    FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))
    CORS_ORIGINS: list = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "*").split(",")
    ]
    PORT: int = int(os.getenv("PORT", "8000"))

    @classmethod
    def validate(cls) -> list[str]:
        issues = []
        if not cls.TIINGO_API_KEY:
            issues.append("TIINGO_API_KEY not set")
        if not cls.FRED_API_KEY:
            issues.append("FRED_API_KEY not set")
        return issues
