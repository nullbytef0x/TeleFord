import logging
import asyncio
import os
import os
from functools import wraps
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
from app.bot.keyboards import (
    main_menu_keyboard, back_keyboard, session_management_keyboard,
    content_type_keyboard, my_rules_keyboard, forwarding_style_keyboard,
    edit_rule_keyboard, forwarding_style_keyboard_for_edit, content_type_keyboard_for_edit,
    owner_menu_keyboard, content_filters_keyboard
)
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors.rpcerrorlist import PhoneCodeExpiredError
from config import Config
from app.db.database import authorized_users_collection
from app.db.models import authorized_user_model

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation
SOURCE, DESTINATION, STYLE, CONTENT_TYPE, LOGIN_SESSION, BATCH_SOURCE, BATCH_DESTINATION, BATCH_START_DATE, BATCH_END_DATE, BATCH_STYLE, DELETE_RULE_NUMBER, EDIT_RULE_NUMBER, EDIT_RULE_MENU, CHOOSE_EDIT_STYLE, CHOOSE_EDIT_CONTENT, ADD_USER_ID, REMOVE_USER_ID, BATCH_CONTENT_TYPE, FORWARD_BY_LINK_LINK, FORWARD_BY_LINK_DESTINATION, ADD_TO_BLOCKLIST_LINK = range(21)

# --- Authorization Decorators ---
def is_owner(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != Config.OWNER_ID:
            await update.message.reply_text("You are not authorized to use this command.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

def is_authorized(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != Config.OWNER_ID and not authorized_users_collection.find_one({"user_id": user_id}):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


@is_authorized
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command by showing the main menu."""
    user = update.effective_user
    # Ensure user is in the database
    from app.db.database import users_collection
    from app.db.models import user_model
    if not users_collection.find_one({"user_id": user.id}):
        users_collection.insert_one(user_model(user.id))

    await show_main_menu(update, context)

@is_authorized
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int = None) -> None:
    """Displays the main menu."""
    text = "Welcome to the Telegram Forwarder Bot! Please choose an option:"
    reply_markup = main_menu_keyboard(update.effective_user.id)
    
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif message_id:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /menu command by showing the main menu."""
    await show_main_menu(update, context)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles main menu button presses."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'login':
        return await login(update, context)
    elif query.data == 'new_rule':
        return await new_rule(update, context)
    elif query.data == 'my_rules':
        return await my_rules(update, context)
    elif query.data == 'batch_forward':
        return await batch_forward(update, context)
    elif query.data == 'help':
        return await help_command(update, context)
    elif query.data == 'session_management':
        return await session_management(update, context)
    elif query.data == 'owner_menu':
        return await owner_menu(update, context)
    elif query.data == 'forward_by_link':
        return await forward_by_link_start(update, context)
    elif query.data == 'content_filters':
        return await content_filters_menu(update, context)

@is_authorized
async def batch_forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the batch forward conversation."""
    query = update.callback_query
    await query.edit_message_text(
        text="Let's start a batch forward. First, send me the source chat ID.",
        reply_markup=back_keyboard('main_menu')
    )
    return BATCH_SOURCE

@is_authorized
async def new_rule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the new rule conversation."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Let's set up a new rule.\n\nPlease send me the source chat IDs, separated by commas.",
        reply_markup=back_keyboard('main_menu')
    )
    return SOURCE

@is_authorized
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user for their session string."""
    query = update.callback_query
    await query.edit_message_text(
        text="Please send me your Telethon session string. "
             "You can generate one by running a script locally. "
             "See the README for instructions.",
        reply_markup=back_keyboard('main_menu')
    )
    return LOGIN_SESSION

async def session_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the session string, validates it, and saves it."""
    session_string = update.message.text
    user_id = update.effective_user.id

    # Validate the session string by trying to connect
    try:
        client = TelegramClient(StringSession(session_string), Config.API_ID, Config.API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            await update.message.reply_text("The session string is invalid or has expired. Please generate a new one.")
            return ConversationHandler.END
        
        # Save session to database
        from app.db.database import sessions_collection
        from app.db.models import session_model
        sessions_collection.update_one(
            {"user_id": user_id},
            {"$set": session_model(user_id, session_string)},
            upsert=True
        )
        
        me = await client.get_me()
        await update.message.reply_text(f"Successfully logged in as {me.first_name}! Your session has been saved.")
        await client.disconnect()
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error validating session string for user {user_id}: {e}")
        await update.message.reply_text("There was an error validating your session string. Please ensure it is correct and try again.")
        return ConversationHandler.END

@is_authorized
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels any active conversation and returns to the main menu."""
    if context.user_data:
        context.user_data.clear()
        await update.message.reply_text("Operation canceled.")
    else:
        await update.message.reply_text("Nothing to cancel.")
    
    await show_main_menu(update, context)
    return ConversationHandler.END

async def source_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the source chat IDs."""
    try:
        source_chats = [int(chat_id.strip()) for chat_id in update.message.text.split(',')]
        context.user_data["source_chats"] = source_chats
        await update.message.reply_text("Great. Now, send me the destination chat ID.")
        return DESTINATION
    except ValueError:
        await update.message.reply_text("Invalid format. Please send a comma-separated list of chat IDs (numbers).")
        return SOURCE

async def destination_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the destination chat ID."""
    try:
        destination_chat = int(update.message.text)
        context.user_data["destination_chat"] = destination_chat
        await update.message.reply_text(
            "Got it. How should I forward messages?",
            reply_markup=forwarding_style_keyboard()
        )
        return STYLE
    except ValueError:
        await update.message.reply_text("Invalid chat ID. Please send a valid chat ID (number).")
        return DESTINATION

async def time_range_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the time range for the rule."""
    if update.message.text.lower() == 'no':
        context.user_data["time_range"] = None
        await update.message.reply_text("Okay, no time range will be applied.")
        return await style_received(update, context) # Proceed to save the rule

    try:
        start, end = update.message.text.split('-')
        time_range = {"start": start.strip(), "end": end.strip()}
        context.user_data["time_range"] = time_range
        await update.message.reply_text(f"Time range set from {start} to {end}.")
        return await style_received(update, context) # Proceed to save the rule
    except ValueError:
        await update.message.reply_text("Invalid format. Please use HH:MM - HH:MM format, or send 'no'.")
        return TIME_RANGE

async def style_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the forwarding style and asks for the content type."""
    query = update.callback_query
    await query.answer()
    
    style = query.data.split('_')[1] # style_new -> new
    context.user_data["forwarding_style"] = style
    
    # Fetch chat names
    user_id = update.effective_user.id
    from app.db.database import sessions_collection
    session_data = sessions_collection.find_one({"user_id": user_id})
    if not session_data:
        await update.message.reply_text("Could not find your session. Please /login again.")
        return ConversationHandler.END

    client = TelegramClient(StringSession(session_data["session_string"]), Config.API_ID, Config.API_HASH)
    await client.connect()
    
    try:
        source_names = []
        for chat_id in context.user_data["source_chats"]:
            entity = await client.get_entity(chat_id)
            source_names.append(entity.title)
        context.user_data["source_names"] = source_names
        
        entity = await client.get_entity(context.user_data["destination_chat"])
        context.user_data["destination_name"] = entity.title
        
    except Exception as e:
        logger.error(f"Error fetching chat names for user {user_id}: {e}")
        await update.message.reply_text("Could not fetch chat names. Please ensure the chat IDs are correct and you are a member of the chats.")
        return ConversationHandler.END
    finally:
        await client.disconnect()

    await query.edit_message_text(
        "Finally, what type of content should I forward?",
        reply_markup=content_type_keyboard()
    )
    return CONTENT_TYPE

async def content_type_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the content type and saves the rule."""
    query = update.callback_query
    await query.answer()
    
    content_type = query.data.split('_')[1] # e.g., 'content_media' -> 'media'
    
    user_id = update.effective_user.id
    source_chats = context.user_data["source_chats"]
    destination_chat = context.user_data["destination_chat"]
    style = context.user_data["forwarding_style"]
    source_names = context.user_data["source_names"]
    destination_name = context.user_data["destination_name"]

    from app.db.database import rules_collection
    from app.db.models import rule_model

    rules_collection.insert_one(
        rule_model(
            user_id=user_id,
            source_chats=source_chats,
            destination_chat=destination_chat,
            source_names=source_names,
            destination_name=destination_name,
            forwarding_style=style,
            content_type=content_type
        )
    )

    await query.edit_message_text("Rule created successfully! Restarting forwarder...")
    await restart_forwarder_for_user(user_id, context)
    await asyncio.sleep(2)
    await show_main_menu(update, context)
    return ConversationHandler.END

@is_authorized
async def my_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the user's current forwarding rules."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    from app.db.database import rules_collection
    user_rules = list(rules_collection.find({"user_id": user_id}))

    if not user_rules:
        text = "You don't have any rules set up yet."
        reply_markup = back_keyboard('main_menu')
    else:
        text = "Your forwarding rules:\n\n"
        for i, rule in enumerate(user_rules):
            text += f"Rule {i+1}:\n"
            text += f"  Source: {', '.join(rule.get('source_names', [str(c) for c in rule['source_chats']]))}\n"
            text += f"  Destination: {rule.get('destination_name', str(rule['destination_chat']))}\n"
            text += f"  Style: {rule['forwarding_style']}\n"
            text += f"  Content: {rule.get('content_type', 'both').capitalize()}\n"
            text += f"  Enabled: {rule['enabled']}\n\n"
        reply_markup = my_rules_keyboard()
    
    await query.edit_message_text(text, reply_markup=reply_markup)

@is_authorized
async def delete_rule_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks for the rule number to delete."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Please send me the number of the rule you want to delete.",
        reply_markup=back_keyboard('my_rules')
    )
    return DELETE_RULE_NUMBER

async def delete_rule_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Deletes the specified rule."""
    try:
        rule_number = int(update.message.text)
        user_id = update.effective_user.id
        from app.db.database import rules_collection
        user_rules = list(rules_collection.find({"user_id": user_id}))

        if not 1 <= rule_number <= len(user_rules):
            await update.message.reply_text("Invalid rule number. Please try again.")
        else:
            rule_to_delete = user_rules[rule_number - 1]
            rules_collection.delete_one({"_id": rule_to_delete["_id"]})
            await update.message.reply_text(f"Rule {rule_number} has been deleted.")
            
    except (ValueError, AttributeError):
        await update.message.reply_text("Invalid input. Please send a number.")

    await restart_forwarder_for_user(user_id, context)
    await asyncio.sleep(2)
    await show_main_menu(update, context)
    return ConversationHandler.END

@is_authorized
async def edit_rule_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks for the rule number to edit."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Please send me the number of the rule you want to edit.",
        reply_markup=back_keyboard('my_rules')
    )
    return EDIT_RULE_NUMBER

async def edit_rule_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays the edit menu for the selected rule."""
    try:
        rule_number = int(update.message.text)
        user_id = update.effective_user.id
        from app.db.database import rules_collection
        user_rules = list(rules_collection.find({"user_id": user_id}))

        if not 1 <= rule_number <= len(user_rules):
            await update.message.reply_text("Invalid rule number.", reply_markup=back_keyboard('my_rules'))
            return EDIT_RULE_NUMBER
        
        rule_to_edit = user_rules[rule_number - 1]
        context.user_data['rule_to_edit_id'] = rule_to_edit['_id']
        context.user_data['rule_number'] = rule_number
        
        text = f"Editing Rule {rule_number}:\n"
        text += f"  Source: {', '.join(rule_to_edit.get('source_names', [str(c) for c in rule_to_edit['source_chats']]))}\n"
        text += f"  Destination: {rule_to_edit.get('destination_name', str(rule_to_edit['destination_chat']))}\n"
        text += f"  Style: {rule_to_edit['forwarding_style']}\n"
        text += f"  Content: {rule_to_edit.get('content_type', 'both').capitalize()}\n"
        text += f"  Enabled: {rule_to_edit['enabled']}\n\n"
        text += "What would you like to change?"
        
        await update.message.reply_text(text, reply_markup=edit_rule_keyboard(str(rule_to_edit['_id'])))
        return EDIT_RULE_MENU
        
    except (ValueError, AttributeError):
        await update.message.reply_text("Invalid input. Please send a number.", reply_markup=back_keyboard('my_rules'))
        return EDIT_RULE_NUMBER

async def prompt_edit_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompts the user to choose a new forwarding style."""
    query = update.callback_query
    await query.answer()
    rule_id = query.data.split('_')[-1]
    await query.edit_message_text(
        "Please choose the new forwarding style:",
        reply_markup=forwarding_style_keyboard_for_edit(rule_id)
    )
    return CHOOSE_EDIT_STYLE

async def prompt_edit_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompts the user to choose a new content type."""
    query = update.callback_query
    await query.answer()
    rule_id = query.data.split('_')[-1]
    await query.edit_message_text(
        "Please choose the new content type:",
        reply_markup=content_type_keyboard_for_edit(rule_id)
    )
    return CHOOSE_EDIT_CONTENT

async def update_rule_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Updates a specific field of a rule."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    action, field, rule_id_str = parts[0], parts[1], parts[2]
    new_value = parts[3] if len(parts) > 3 else None

    from app.db.database import rules_collection
    from bson.objectid import ObjectId
    
    rule_id = ObjectId(rule_id_str)
    
    if field == "style":
        update_field = "forwarding_style"
    elif field == "content":
        update_field = "content_type"
    else:
        logger.warning(f"Unknown field to update: {field}")
        return EDIT_RULE_MENU

    rules_collection.update_one({"_id": rule_id}, {"$set": {update_field: new_value}})
    
    await query.edit_message_text(f"Rule's {field} has been updated successfully!")
    await restart_forwarder_for_user(update.effective_user.id, context)
    await asyncio.sleep(1)
    await my_rules(update, context) # Show the updated rules list
    return ConversationHandler.END


async def toggle_rule_enabled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Toggles the 'enabled' status of a rule."""
    query = update.callback_query
    await query.answer()
    
    rule_id_str = query.data.split('_')[-1]
    from app.db.database import rules_collection
    from bson.objectid import ObjectId
    
    rule_id = ObjectId(rule_id_str)
    
    rule = rules_collection.find_one({"_id": rule_id})
    if rule:
        new_status = not rule.get("enabled", True)
        rules_collection.update_one({"_id": rule_id}, {"$set": {"enabled": new_status}})
        await query.edit_message_text(f"Rule has been {'enabled' if new_status else 'disabled'}.")
        await restart_forwarder_for_user(update.effective_user.id, context)
    else:
        await query.edit_message_text("Could not find the rule to update.")

    await asyncio.sleep(1)
    await my_rules(update, context) # Show the updated rules list
    return ConversationHandler.END


@is_authorized
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays a help message with all available commands."""
    query = update.callback_query
    await query.answer()
    
    help_text = """
Here are the available commands:

/start - Initialize the bot.
/login - Connect your Telegram account using a session string.
/newrule - Create a new rule for real-time forwarding of new messages.
/batchforward - Forward historical messages from a specific date range.
/myrules - View all your active real-time forwarding rules.
/delrule <number> - Delete a specific real-time forwarding rule.
/cancel - Cancel the current operation.
/help - Show this help message.
"""
    await query.edit_message_text(help_text, reply_markup=back_keyboard('main_menu'))

async def batch_source_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the batch source chat ID."""
    try:
        source_chat = int(update.message.text)
        context.user_data["batch_source"] = source_chat
        await update.message.reply_text("Great. Now, send me the destination chat ID for the batch forward.")
        return BATCH_DESTINATION
    except ValueError:
        await update.message.reply_text("Invalid chat ID. Please send a valid chat ID (number).")
        return BATCH_SOURCE

async def batch_destination_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the batch destination chat ID."""
    try:
        destination_chat = int(update.message.text)
        context.user_data["batch_destination"] = destination_chat
        await update.message.reply_text("Got it. Now, send me the start date and time in MM/DD/YYYY HH:MM AM/PM format.")
        return BATCH_START_DATE
    except ValueError:
        await update.message.reply_text("Invalid chat ID. Please send a valid chat ID (number).")
        return BATCH_DESTINATION

async def batch_start_date_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the batch start date."""
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        USER_TZ = ZoneInfo("Asia/Colombo")
        naive_start_date = datetime.strptime(update.message.text, "%m/%d/%Y %I:%M %p")
        local_start_date = naive_start_date.replace(tzinfo=USER_TZ)
        utc_start_date = local_start_date.astimezone(ZoneInfo("UTC"))
        context.user_data["batch_start_date"] = utc_start_date
        await update.message.reply_text("Okay. Now, send me the end date and time in MM/DD/YYYY HH:MM AM/PM format.")
        return BATCH_END_DATE
    except ValueError:
        await update.message.reply_text("Invalid date format. Please use MM/DD/YYYY HH:MM AM/PM.")
        return BATCH_START_DATE

async def batch_end_date_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the batch end date and asks for the forwarding style."""
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        USER_TZ = ZoneInfo("Asia/Colombo")
        naive_end_date = datetime.strptime(update.message.text, "%m/%d/%Y %I:%M %p")
        local_end_date = naive_end_date.replace(tzinfo=USER_TZ)
        utc_end_date = local_end_date.astimezone(ZoneInfo("UTC"))
        context.user_data["batch_end_date"] = utc_end_date
        await update.message.reply_text(
            "Next, what type of content should I forward?",
            reply_markup=content_type_keyboard()
        )
        return BATCH_CONTENT_TYPE
    except ValueError:
        await update.message.reply_text("Invalid date format. Please use MM/DD/YYYY HH:MM AM/PM.")
        return BATCH_END_DATE

async def batch_content_type_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the content type for batch forwarding."""
    query = update.callback_query
    await query.answer()
    
    content_type = query.data.split('_')[1]
    context.user_data["batch_content_type"] = content_type
    
    await query.edit_message_text(
        "Got it. How should I forward these messages?",
        reply_markup=forwarding_style_keyboard()
    )
    return BATCH_STYLE

async def batch_style_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the batch forwarding style and starts the process."""
    query = update.callback_query
    await query.answer()
    
    style = query.data.split('_')[1]
    context.user_data["batch_style"] = style

    user_id = update.effective_user.id
    source_chat = context.user_data["batch_source"]
    destination_chat = context.user_data["batch_destination"]
    start_date = context.user_data["batch_start_date"]
    end_date = context.user_data["batch_end_date"]
    content_type = context.user_data["batch_content_type"]

    status_message = await query.edit_message_text("Starting batch forward process. This may take some time...")

    # Run the batch forward in the background
    loop = asyncio.get_event_loop()
    loop.create_task(
        run_batch_forward(
            user_id,
            source_chat,
            destination_chat,
            start_date,
            end_date,
            style,
            content_type,
            context.bot,
            status_message.chat_id,
            status_message.message_id,
        )
    )

    return ConversationHandler.END

async def run_batch_forward(user_id, source_chat, destination_chat, start_date, end_date, style, content_type, bot, chat_id, message_id):
    """Connects with the user's client and forwards messages from the specified date range."""
    from app.db.database import sessions_collection
    session_data = sessions_collection.find_one({"user_id": user_id})
    if not session_data:
        logger.error(f"No session found for user {user_id} during batch forward.")
        await bot.edit_message_text("Could not find your session. Please /login again.", chat_id=chat_id, message_id=message_id)
        return

    client = TelegramClient(StringSession(session_data["session_string"]), Config.API_ID, Config.API_HASH)
    
    try:
        await client.connect()
        logger.info(f"Starting batch forward for user {user_id} from chat {source_chat} to {destination_chat} with style '{style}'")
        count = 0
        messages_to_forward = []
        # Iterate backwards from the newest messages
        async for message in client.iter_messages(source_chat):
            # If the message is older than the start date, we can stop
            if message.date < start_date:
                break
            # If the message is within the date range, add it for forwarding
            if message.date <= end_date:
                messages_to_forward.append(message)

        # Forward messages in chronological order
        for message in reversed(messages_to_forward):
            # Content type filtering
            has_media = message.media is not None
            has_text = message.text is not None

            if content_type == "media" and not has_media:
                continue
            if content_type == "text" and not has_text:
                continue
            if content_type == "photo" and not message.photo:
                continue
            if content_type == "video" and not message.video:
                continue

            try:
                if style == "forwarded" and not message.noforwards:
                    await message.forward_to(destination_chat)
                else:
                    if has_media:
                        file_path = await message.download_media(file="temp/")
                        try:
                            await client.send_file(destination_chat, file_path, caption=message.text if has_text else None)
                        finally:
                            os.remove(file_path)
                    elif has_text:
                        await client.send_message(destination_chat, message.text)

                count += 1
                if count % 10 == 0:
                    await asyncio.sleep(5)  # 5-second delay every 10 messages
                else:
                    await asyncio.sleep(1) # 1-second delay for other messages
            except Exception as e:
                logger.error(f"Could not forward message {message.id} for user {user_id}: {e}")
                continue

        logger.info(f"Batch forward completed for user {user_id}. Forwarded {count} messages.")
        await bot.edit_message_text(f"Batch forward completed! Forwarded {count} messages.", chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f"Error during batch forward for user {user_id}: {e}")
        await bot.edit_message_text(f"Batch forward failed. Error: {e}", chat_id=chat_id, message_id=message_id)
    finally:
        if client.is_connected():
            await client.disconnect()

@is_authorized
async def session_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the session management menu."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Manage your session:",
        reply_markup=session_management_keyboard()
    )

@is_authorized
async def view_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Views the current session."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    from app.db.database import sessions_collection
    session_data = sessions_collection.find_one({"user_id": user_id})

    if not session_data:
        text = "You are not logged in."
    else:
        try:
            client = TelegramClient(StringSession(session_data["session_string"]), Config.API_ID, Config.API_HASH)
            await client.connect()
            me = await client.get_me()
            text = f"You are currently logged in as: {me.first_name}"
            await client.disconnect()
        except Exception as e:
            text = "Your session string is invalid. Please log in again."
            logger.error(f"Error viewing session for user {user_id}: {e}")

    await query.edit_message_text(text, reply_markup=back_keyboard('session_management'))

@is_authorized
async def delete_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deletes the current session."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    from app.db.database import sessions_collection
    result = sessions_collection.delete_one({"user_id": user_id})

    if result.deleted_count > 0:
        text = "Your session has been deleted."
    else:
        text = "You were not logged in."

    await query.edit_message_text(text, reply_markup=back_keyboard('session_management'))

async def restart_forwarder_for_user(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Stops and restarts the forwarder task for a specific user."""
    forwarder_tasks = context.bot_data["forwarder_tasks"]
    
    if user_id in forwarder_tasks:
        task = forwarder_tasks[user_id]
        task.cancel()
        logger.info(f"Canceled forwarder task for user_id: {user_id}")

    from app.db.database import sessions_collection
    from app.forwarder.main import start_client
    
    session_data = sessions_collection.find_one({"user_id": user_id})
    if session_data:
        new_task = asyncio.create_task(start_client(session_data))
        forwarder_tasks[user_id] = new_task
        logger.info(f"Restarted forwarder task for user_id: {user_id}")

# --- Owner Commands ---
@is_owner
async def owner_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the owner menu."""
    query = update.callback_query
    text = "Owner Menu:"
    reply_markup = owner_menu_keyboard()

    if query:
        await query.answer()
        await query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

@is_owner
async def add_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks for the user ID to add."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Please send the Telegram User ID of the user you want to authorize.",
        reply_markup=back_keyboard('owner_menu')
    )
    return ADD_USER_ID

@is_owner
async def add_user_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Adds a user to the authorized list."""
    try:
        user_id_to_add = int(update.message.text)
        if authorized_users_collection.find_one({"user_id": user_id_to_add}):
            await update.message.reply_text("This user is already authorized.")
        else:
            authorized_users_collection.insert_one(
                authorized_user_model(user_id_to_add, update.effective_user.id)
            )
            await update.message.reply_text(f"User {user_id_to_add} has been authorized.")
    except ValueError:
        await update.message.reply_text("Invalid User ID. Please send a number.")
        return ADD_USER_ID

    await update.message.reply_text("Owner Menu:", reply_markup=owner_menu_keyboard())
    return ConversationHandler.END

@is_owner
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all authorized users."""
    query = update.callback_query
    await query.answer()
    
    users = list(authorized_users_collection.find())
    if not users:
        text = "No users have been authorized yet."
    else:
        text = "Authorized Users:\n\n"
        for user in users:
            text += f"- `{user['user_id']}` (Added by: `{user['added_by']}`)\n"
            
    await query.edit_message_text(text, reply_markup=back_keyboard('owner_menu'))

@is_owner
async def remove_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks for the user ID to remove."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Please send the Telegram User ID of the user you want to remove.",
        reply_markup=back_keyboard('owner_menu')
    )
    return REMOVE_USER_ID

@is_owner
async def remove_user_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Removes a user from the authorized list."""
    try:
        user_id_to_remove = int(update.message.text)
        result = authorized_users_collection.delete_one({"user_id": user_id_to_remove})
        if result.deleted_count > 0:
            await update.message.reply_text(f"User {user_id_to_remove} has been removed.")
        else:
            await update.message.reply_text("That user was not found in the authorized list.")
    except ValueError:
        await update.message.reply_text("Invalid User ID. Please send a number.")
        return REMOVE_USER_ID

    await owner_menu(update, context)
    return ConversationHandler.END

# --- Forward by Link ---
@is_authorized
async def forward_by_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the forward by link conversation."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Please send me the message link.",
        reply_markup=back_keyboard('main_menu')
    )
    return FORWARD_BY_LINK_LINK

async def forward_by_link_link_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the message link and asks for the destination."""
    context.user_data['message_link'] = update.message.text
    await update.message.reply_text("Great. Now, send me the destination chat ID.")
    return FORWARD_BY_LINK_DESTINATION

async def forward_by_link_destination_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the destination and forwards the message."""
    destination_chat = int(update.message.text)
    message_link = context.user_data['message_link']
    user_id = update.effective_user.id

    status_message = await update.message.reply_text("Forwarding message...")

    loop = asyncio.get_event_loop()
    loop.create_task(
        run_forward_by_link(
            user_id,
            message_link,
            destination_chat,
            context.bot,
            status_message.chat_id,
            status_message.message_id,
        )
    )
    return ConversationHandler.END

async def run_forward_by_link(user_id, message_link, destination_chat, bot, chat_id, message_id):
    """Connects with the user's client and forwards the message."""
    from app.db.database import sessions_collection
    session_data = sessions_collection.find_one({"user_id": user_id})
    if not session_data:
        logger.error(f"No session found for user {user_id} during forward by link.")
        await bot.edit_message_text("Could not find your session. Please /login again.", chat_id=chat_id, message_id=message_id)
        return

    client = TelegramClient(StringSession(session_data["session_string"]), Config.API_ID, Config.API_HASH)

    try:
        await client.connect()
        
        # Parse the message link
        parts = message_link.split('/')
        msg_id = int(parts[-1])

        if "/c/" in message_link:
            chat_id_str = parts[-2]
            chat_entity = int("-100" + chat_id_str)
        else:
            chat_entity = parts[-2]

        # Get the message
        message = await client.get_messages(chat_entity, ids=msg_id)

        if message:
            if message.media:
                file_path = await message.download_media(file="temp/")
                try:
                    await client.send_file(destination_chat, file_path, caption=message.text)
                finally:
                    os.remove(file_path)
            elif message.text:
                await client.send_message(destination_chat, message.text)
            
            await bot.edit_message_text("Message forwarded successfully!", chat_id=chat_id, message_id=message_id)
        else:
            await bot.edit_message_text("Could not find the message. Please ensure the link is correct.", chat_id=chat_id, message_id=message_id)

    except Exception as e:
        logger.error(f"Error during forward by link for user {user_id}: {e}")
        await bot.edit_message_text(f"Forwarding failed. Error: {e}", chat_id=chat_id, message_id=message_id)
    finally:
        if client.is_connected():
            await client.disconnect()

@is_owner
async def export_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exports the logs and sends them to the owner."""
    query = update.callback_query
    await query.answer()
    
    log_file_path = "logs/bot.log"
    
    try:
        if os.path.getsize(log_file_path) == 0:
            await query.edit_message_text("The log file is currently empty.")
            return

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(log_file_path, "rb"),
            filename="bot_logs.txt"
        )
    except Exception as e:
        logger.error(f"Error exporting logs: {e}")
        await query.edit_message_text("An error occurred while exporting the logs.")

async def content_filters_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the content filters menu."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Manage your content filters:",
        reply_markup=content_filters_keyboard()
    )

async def add_to_blocklist_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user for the message link to block."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Please send me the link of the message you want to block.",
        reply_markup=back_keyboard('content_filters')
    )
    return ADD_TO_BLOCKLIST_LINK

async def blocklist_link_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the message link and adds its content to the blocklist."""
    message_link = update.message.text
    user_id = update.effective_user.id

    status_message = await update.message.reply_text("Adding content to blocklist...")

    loop = asyncio.get_event_loop()
    loop.create_task(
        run_add_to_blocklist(
            user_id,
            message_link,
            context.bot,
            status_message.chat_id,
            status_message.message_id,
        )
    )
    return ConversationHandler.END

async def run_add_to_blocklist(user_id, message_link, bot, chat_id, message_id):
    """Connects with the user's client, fetches the message, and blocks its content."""
    from app.db.database import sessions_collection, blocked_content_collection
    from app.db.models import blocked_content_model
    
    session_data = sessions_collection.find_one({"user_id": user_id})
    if not session_data:
        logger.error(f"No session found for user {user_id} during blocklist add.")
        await bot.edit_message_text("Could not find your session. Please /login again.", chat_id=chat_id, message_id=message_id)
        return

    client = TelegramClient(StringSession(session_data["session_string"]), Config.API_ID, Config.API_HASH)

    try:
        await client.connect()
        
        parts = message_link.split('/')
        msg_id = int(parts[-1])

        if "/c/" in message_link:
            chat_id_str = parts[-2]
            chat_entity = int("-100" + chat_id_str)
        else:
            chat_entity = parts[-2]

        message = await client.get_messages(chat_entity, ids=msg_id)

        if message:
            media_id = None
            text_content = message.text or None

            if message.photo:
                media_id = str(message.photo.id)
            elif message.video:
                media_id = str(message.video.id)

            if media_id or text_content:
                # Check if this exact content is already blocked
                if blocked_content_collection.find_one({"user_id": user_id, "file_id": media_id, "text": text_content}):
                    await bot.edit_message_text("This content is already on the blocklist.", chat_id=chat_id, message_id=message_id)
                else:
                    blocked_content_collection.insert_one(blocked_content_model(user_id, file_id=media_id, text=text_content))
                    await bot.edit_message_text("Content has been added to the blocklist.", chat_id=chat_id, message_id=message_id)
            else:
                await bot.edit_message_text("This content type cannot be blocked.", chat_id=chat_id, message_id=message_id)
        else:
            await bot.edit_message_text("Could not find the message. Please ensure the link is correct.", chat_id=chat_id, message_id=message_id)

    except Exception as e:
        logger.error(f"Error during blocklist add for user {user_id}: {e}")
        await bot.edit_message_text(f"Failed to add to blocklist. Error: {e}", chat_id=chat_id, message_id=message_id)
    finally:
        if client.is_connected():
            await client.disconnect()