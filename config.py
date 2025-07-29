import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot API Token
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    # Telegram API Credentials
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")

    # MongoDB Connection URI
    MONGO_URI = os.getenv("MONGO_URI")

    # Bot Owner's Telegram User ID
    OWNER_ID = int(os.getenv("OWNER_ID"))
