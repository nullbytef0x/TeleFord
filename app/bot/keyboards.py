from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard(user_id: int = None):
    """Returns the main menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("🔐 Session Management", callback_data='session_management')],
        [InlineKeyboardButton("➕ Add New Rule", callback_data='new_rule')],
        [InlineKeyboardButton("📋 View My Rules", callback_data='my_rules')],
        [InlineKeyboardButton("⏳ Batch Forward", callback_data='batch_forward')],
        [InlineKeyboardButton("🔗 Forward by Link", callback_data='forward_by_link')],
        [InlineKeyboardButton("❓ Help", callback_data='help')],
    ]
    from config import Config
    if user_id == Config.OWNER_ID:
        keyboard.append([InlineKeyboardButton("👑 Owner", callback_data='owner_menu')])
    return InlineKeyboardMarkup(keyboard)

def owner_menu_keyboard():
    """Returns the owner menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("➕ Add User", callback_data='add_user')],
        [InlineKeyboardButton("📋 List Users", callback_data='list_users')],
        [InlineKeyboardButton("🗑️ Remove User", callback_data='remove_user')],
        [InlineKeyboardButton("📄 Export Logs", callback_data='export_logs')],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data='main_menu')],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard(callback_data: str):
    """Returns a keyboard with a back button."""
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)

def session_management_keyboard():
    """Returns the session management keyboard."""
    keyboard = [
        [InlineKeyboardButton("👁️ View Current Session", callback_data='view_session')],
        [InlineKeyboardButton("➕ Add / Update Session", callback_data='login')],
        [InlineKeyboardButton("🗑️ Delete Session", callback_data='delete_session')],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data='main_menu')],
    ]
    return InlineKeyboardMarkup(keyboard)

def login_method_keyboard():
    """Returns the login method selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("📱 QR Code Login (Recommended)", callback_data='login_qr')],
        [InlineKeyboardButton("🔑 Session String (Advanced)", callback_data='login_string')],
        [InlineKeyboardButton("⬅️ Back", callback_data='session_management')],
    ]
    return InlineKeyboardMarkup(keyboard)

def content_type_keyboard():
    """Returns the content type selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("🖼️ Photo Only", callback_data='content_photo')],
        [InlineKeyboardButton("🎥 Video Only", callback_data='content_video')],
        [InlineKeyboardButton("🖼️ Media Only", callback_data='content_media')],
        [InlineKeyboardButton("📄 Text Only", callback_data='content_text')],
        [InlineKeyboardButton("🖼️📄 Both", callback_data='content_both')],
        [InlineKeyboardButton("⬅️ Back", callback_data='main_menu')],
    ]
    return InlineKeyboardMarkup(keyboard)

def edit_rule_keyboard(rule_id: str):
    """Returns the keyboard for editing a rule."""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Change Style", callback_data=f'edit_style_{rule_id}'),
            InlineKeyboardButton("📄 Change Content Type", callback_data=f'edit_content_{rule_id}')
        ],
        [
            InlineKeyboardButton("✅ Enable / Disable 🔽", callback_data=f'toggle_enabled_{rule_id}'),
        ],
        [InlineKeyboardButton("⬅️ Back to Rules", callback_data='my_rules')],
    ]
    return InlineKeyboardMarkup(keyboard)


def forwarding_style_keyboard_for_edit(rule_id: str):
    """Returns the forwarding style selection keyboard for editing a rule."""
    keyboard = [
        [
            InlineKeyboardButton("🆕 As New", callback_data=f'update_style_{rule_id}_new'),
            InlineKeyboardButton("➡️ Forwarded", callback_data=f'update_style_{rule_id}_forwarded')
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data='my_rules')],
    ]
    return InlineKeyboardMarkup(keyboard)


def content_type_keyboard_for_edit(rule_id: str):
    """Returns the content type selection keyboard for editing a rule."""
    keyboard = [
        [InlineKeyboardButton("🖼️ Photo Only", callback_data=f'update_content_{rule_id}_photo')],
        [InlineKeyboardButton("🎥 Video Only", callback_data=f'update_content_{rule_id}_video')],
        [InlineKeyboardButton("🖼️ Media Only", callback_data=f'update_content_{rule_id}_media')],
        [InlineKeyboardButton("📄 Text Only", callback_data=f'update_content_{rule_id}_text')],
        [InlineKeyboardButton("🖼️📄 Both", callback_data=f'update_content_{rule_id}_both')],
        [InlineKeyboardButton("⬅️ Back", callback_data='my_rules')],
    ]
    return InlineKeyboardMarkup(keyboard)

def my_rules_keyboard():
    """Returns a keyboard with edit and delete buttons."""
    keyboard = [
        [
            InlineKeyboardButton("📝 Edit Rule", callback_data='edit_rule'),
            InlineKeyboardButton("🗑️ Delete Rule", callback_data='delete_rule')
        ],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def forwarding_style_keyboard():
    """Returns the forwarding style selection keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🆕 As New", callback_data='style_new'),
            InlineKeyboardButton("➡️ Forwarded", callback_data='style_forwarded')
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data='main_menu')],
    ]
    return InlineKeyboardMarkup(keyboard)