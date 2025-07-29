from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = input("Please enter your API ID: ")
API_HASH = input("Please enter your API HASH: ")

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("Your session string is:", client.session.save())