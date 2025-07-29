import asyncio
import logging
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from app.db.database import sessions_collection, rules_collection
from config import Config

# Enable logging
logger = logging.getLogger(__name__)

async def start_client(session_data):
    """Initializes and runs a single Telegram client."""
    session_string = session_data["session_string"]
    user_id = session_data["user_id"]
    logger.info(f"Initializing client for user_id: {user_id}")

    client = TelegramClient(
        StringSession(session_string), Config.API_ID, Config.API_HASH
    )

    try:
        logger.info(f"Connecting client for user_id: {user_id}...")
        await client.connect()
        if not await client.is_user_authorized():
            logger.warning(f"Session for user_id: {user_id} is not authorized. Skipping.")
            return
        logger.info(f"Client connected successfully for user_id: {user_id}")
        
        # Fetch all dialogs to ensure the client is aware of all chats, including private ones
        logger.info(f"Fetching dialogs for user_id: {user_id}...")
        await client.get_dialogs()
        logger.info(f"Dialogs fetched successfully for user_id: {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to connect or fetch dialogs for user_id: {user_id}. Error: {e}")
        return

    # Load rules for the user
    user_rules = list(rules_collection.find({"user_id": user_id, "enabled": True}))
    if not user_rules:
        logger.warning(f"No active rules found for user_id: {user_id}. Client will run but do nothing.")
    else:
        logger.info(f"Found {len(user_rules)} active rules for user_id: {user_id}")

    source_chats = [chat for rule in user_rules for chat in rule["source_chats"]]
    logger.info(f"Listening on source chats for user_id {user_id}: {source_chats}")

    @client.on(events.NewMessage(chats=source_chats))
    async def handler(event):
        logger.info(f"EVENT: New message received for user {user_id} from chat {event.chat_id}")
        
        # Re-fetch rules on every new message to ensure they are up-to-date
        current_rules = list(rules_collection.find({"user_id": user_id, "enabled": True}))
        
        for rule in current_rules:
            if event.chat_id in rule["source_chats"]:
                destination = rule["destination_chat"]
                style = rule["forwarding_style"]
                content_type = rule.get("content_type", "both")
                
                # Content type filtering
                has_media = event.message.media is not None
                has_text = event.message.text is not None
                
                if content_type == "media" and not has_media:
                    logger.info(f"Skipping text-only message for media-only rule for user {user_id}")
                    continue
                if content_type == "text" and not has_text:
                    logger.info(f"Skipping media message for text-only rule for user {user_id}")
                    continue

                logger.info(f"MATCH: Rule matched for user {user_id}. Forwarding from {event.chat_id} to {destination}.")
                
                try:
                    if style == "forwarded" and not event.message.noforwards:
                        await event.forward_to(destination)
                    else:
                        # Handle protected content by downloading and re-uploading
                        if has_media:
                            # Skip stickers and GIFs
                            if event.message.sticker or event.message.gif:
                                logger.info(f"Skipping sticker/GIF for user {user_id}")
                                continue
                            
                            logger.info(f"Downloading media from protected message for user {user_id}...")
                            file_path = await event.message.download_media(file="temp/")
                            await client.send_file(destination, file_path, caption=event.message.text if has_text else None)
                            os.remove(file_path)
                            logger.info(f"Successfully re-uploaded media for user {user_id}")
                        elif has_text:
                            await client.send_message(destination, event.message.text)
                        else:
                            logger.warning(f"Message type not supported for re-uploading for user {user_id}")

                    logger.info(f"SUCCESS: Processed message for {destination} with style '{style}' for user {user_id}")
                except Exception as e:
                    logger.error(f"FAILURE: Could not process message for {destination} for user {user_id}. Error: {e}")

    logger.info(f"Starting event listener for user {user_id}...")
    try:
        await client.run_until_disconnected()
    except asyncio.CancelledError:
        logger.info(f"Client for user_id: {user_id} was cancelled.")
    finally:
        if client.is_connected():
            await client.disconnect()
            logger.info(f"Client for user_id: {user_id} disconnected.")

async def main(forwarder_tasks):
    """The main entry point for the forwarder."""
    logger.info("Starting forwarder service...")
    
    # Start a client for each user with a session
    sessions = list(sessions_collection.find())
    for session in sessions:
        user_id = session["user_id"]
        task = asyncio.create_task(start_client(session))
        forwarder_tasks[user_id] = task
        
    # Keep the main forwarder service running indefinitely
    while True:
        await asyncio.sleep(3600) # Sleep for an hour, or until the process is stopped
