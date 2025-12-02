import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

    # MongoDB
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    MONGODB_DB = os.getenv('MONGODB_DB', 'badminton_tracker')

    # OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://copilot-api.hungtuan.me')

    # App settings
    DEFAULT_COURT_PRICE_PER_HOUR = int(os.getenv('DEFAULT_COURT_PRICE_PER_HOUR', 139000))
    DEFAULT_SHUTTLECOCK_PRICE = int(os.getenv('DEFAULT_SHUTTLECOCK_PRICE', 25000))

    # VietQR Payment Configuration
    VIETQR_BANK_ID = os.getenv('VIETQR_BANK_ID', 'TPB')
    VIETQR_ACCOUNT_NUMBER = os.getenv('VIETQR_ACCOUNT_NUMBER', '03365790401')
    VIETQR_ACCOUNT_NAME = os.getenv('VIETQR_ACCOUNT_NAME', 'Nguyen Nha Hung Tuan')
    VIETQR_BANK_NAME = os.getenv('VIETQR_BANK_NAME', 'TPBank')
    VIETQR_TEMPLATE = os.getenv('VIETQR_TEMPLATE', 'compact2')
