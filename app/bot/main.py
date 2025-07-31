import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from config import Config
from app.db.database import users_collection
from app.db.models import user_model
from app.bot.handlers import (
    start, show_main_menu, menu_command,
    login, session_received, cancel, LOGIN_SESSION,
    session_management, view_session, delete_session,
    new_rule, source_received, destination_received, style_received, content_type_received,
    SOURCE, DESTINATION, STYLE, CONTENT_TYPE, my_rules, delete_rule_start, delete_rule_received, edit_rule_start, help_command, DELETE_RULE_NUMBER, EDIT_RULE_NUMBER,
    batch_forward, batch_source_received, batch_destination_received,
    batch_start_date_received, batch_end_date_received, batch_style_received,
    BATCH_SOURCE, BATCH_DESTINATION, BATCH_START_DATE, BATCH_END_DATE, BATCH_STYLE, BATCH_CONTENT_TYPE,
    edit_rule_received, prompt_edit_style, prompt_edit_content, update_rule_field, toggle_rule_enabled,
    EDIT_RULE_MENU, CHOOSE_EDIT_STYLE, CHOOSE_EDIT_CONTENT,
    owner_menu, add_user_start, add_user_received, list_users, remove_user_start, remove_user_received, export_logs,
    ADD_USER_ID, REMOVE_USER_ID, batch_content_type_received,
    forward_by_link_start, forward_by_link_link_received, forward_by_link_destination_received,
    FORWARD_BY_LINK_LINK, FORWARD_BY_LINK_DESTINATION,
    content_filters_menu, add_to_blocklist_start, blocklist_link_received, ADD_TO_BLOCKLIST_LINK
)

# Enable logging
logger = logging.getLogger(__name__)


async def main(forwarder_tasks) -> None:
    """Start the bot."""
    application = Application.builder().token(Config.BOT_TOKEN).build()
    application.bot_data["forwarder_tasks"] = forwarder_tasks

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(login, pattern='^login$'),
            CallbackQueryHandler(new_rule, pattern='^new_rule$'),
            CallbackQueryHandler(batch_forward, pattern='^batch_forward$'),
            CallbackQueryHandler(delete_rule_start, pattern='^delete_rule$'),
            CallbackQueryHandler(edit_rule_start, pattern='^edit_rule$'),
            CallbackQueryHandler(add_user_start, pattern='^add_user$'),
            CallbackQueryHandler(remove_user_start, pattern='^remove_user$'),
            CallbackQueryHandler(forward_by_link_start, pattern='^forward_by_link$'),
            CallbackQueryHandler(add_to_blocklist_start, pattern='^add_to_blocklist$'),
        ],
        states={
            LOGIN_SESSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, session_received)],
            SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, source_received)],
            DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, destination_received)],
            STYLE: [CallbackQueryHandler(style_received, pattern='^style_')],
            CONTENT_TYPE: [CallbackQueryHandler(content_type_received, pattern='^content_')],
            BATCH_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, batch_source_received)],
            BATCH_DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, batch_destination_received)],
            BATCH_START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, batch_start_date_received)],
            BATCH_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, batch_end_date_received)],
            BATCH_STYLE: [CallbackQueryHandler(batch_style_received, pattern='^style_')],
            BATCH_CONTENT_TYPE: [CallbackQueryHandler(batch_content_type_received, pattern='^content_')],
            DELETE_RULE_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_rule_received)],
            EDIT_RULE_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_rule_received)],
            ADD_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_user_received)],
            REMOVE_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_user_received)],
            FORWARD_BY_LINK_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, forward_by_link_link_received)],
            FORWARD_BY_LINK_DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, forward_by_link_destination_received)],
            EDIT_RULE_MENU: [
                CallbackQueryHandler(prompt_edit_style, pattern='^edit_style_'),
                CallbackQueryHandler(prompt_edit_content, pattern='^edit_content_'),
                CallbackQueryHandler(toggle_rule_enabled, pattern='^toggle_enabled_'),
                CallbackQueryHandler(my_rules, pattern='^my_rules$'),
            ],
            CHOOSE_EDIT_STYLE: [CallbackQueryHandler(update_rule_field, pattern='^update_style_')],
            CHOOSE_EDIT_CONTENT: [CallbackQueryHandler(update_rule_field, pattern='^update_content_')],
            ADD_TO_BLOCKLIST_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, blocklist_link_received)],
        },
        fallbacks=[
            CallbackQueryHandler(show_main_menu, pattern='^main_menu$'),
            CallbackQueryHandler(my_rules, pattern='^my_rules$'),
            CallbackQueryHandler(new_rule, pattern='^new_rule$'),
        ],
        per_message=False,
        map_to_parent={
            ConversationHandler.END: ConversationHandler.END
        }
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(my_rules, pattern='^my_rules$'))
    application.add_handler(CallbackQueryHandler(help_command, pattern='^help$'))
    application.add_handler(CallbackQueryHandler(show_main_menu, pattern='^main_menu$'))
    application.add_handler(CallbackQueryHandler(session_management, pattern='^session_management$'))
    application.add_handler(CallbackQueryHandler(view_session, pattern='^view_session$'))
    application.add_handler(CallbackQueryHandler(delete_session, pattern='^delete_session$'))
    application.add_handler(CallbackQueryHandler(owner_menu, pattern='^owner_menu$'))
    application.add_handler(CallbackQueryHandler(list_users, pattern='^list_users$'))
    application.add_handler(CallbackQueryHandler(export_logs, pattern='^export_logs$'))
    application.add_handler(CallbackQueryHandler(content_filters_menu, pattern='^content_filters$'))
    application.add_handler(conv_handler)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()