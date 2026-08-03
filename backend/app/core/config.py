import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    PROJECT_NAME: str = "Taxor Eval Framework"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./taxor_eval.db")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Zoho Books Credentials
    ZOHO_ACCESS_TOKEN: str = os.getenv("ZOHO_ACCESS_TOKEN", "")
    ZOHO_ORG_ID: str = os.getenv("ZOHO_ORG_ID", "")
    ZOHO_CLIENT_ID: str = os.getenv("ZOHO_CLIENT_ID", "")
    ZOHO_CLIENT_SECRET: str = os.getenv("ZOHO_CLIENT_SECRET", "")
    ZOHO_REFRESH_TOKEN: str = os.getenv("ZOHO_REFRESH_TOKEN", "")


settings = Settings()
