
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from os.path import join, dirname, abspath

# Load the .env file
env_file = join(dirname(abspath(__file__)), "..", ".env")  
load_dotenv(env_file, override=True)  
class Settings(BaseSettings):
    """
    Use this class for adding constants from .env file
    """
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    SMTP_SERVER: str
    SMTP_PORT: int
    GMAIL_USERNAME: str
    GMAIL_PASSWORD: str
    PORT: int = 8000  # Default port if not defined in .env
    SERVER_TIMEOUT: int = 60  # Default timeout if not defined in .env
    PAYPAL_CLIENT_ID: str
    PAYPAL_CLIENT_SECRET: str
    PAYPAL_API_BASE_URL: str

    class Config:
        env_file = env_file  # Specify the .env file to load

settings = Settings()

