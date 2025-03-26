from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import config
from database import Database
import keyboards
import re
import datetime
from typing import Dict, List, Optional, Any
import logging
import time
import json
import os
import random
import string
import base64
import requests
import io
from PIL import Image

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

db = Database()

# Lưu trạng thái của người dùng
user_states = {}

def is_admin(user_id: int) -> bool:
    """Kiểm tra xem người dùng có phải là admin không"""
    return user_id in config.ADMIN_IDS

def register_handlers(bot: TeleBot) -> None:
    """Đăng ký tất cả các handler cho bot"""
    
    # Command handlers
    bot.register_message_handler(lambda msg: start_command(bot, msg), commands=['start'])
    bot.register_message_handler(lambda msg: help_command(bot, msg), commands=['help'])
    bot.register_message_handler(lambda msg: dashboard_command(bot, msg), commands=['dashboard'])
    
    # Admin command handlers
    bot.register_message_handler(lambda msg: create_product_command(bot, msg), commands=['create_product'], func=lambda msg: is_admin(msg.from_user.id))
    bot.register_message_handler(lambda msg: product_list_command(bot, msg), commands=['product_list'], func=lambda msg: is_admin(msg.from_user.id))
    bot.register_message_handler(lambda msg: upload_product_command(bot, msg), commands=['upload_product'], func=lambda msg: is_admin(msg.from_user.id))
    bot.register_message_handler(lambda msg: add_money_command(bot, msg), commands=['add_money'], func=lambda msg: is_admin(msg.from_user.id))
    bot.register_message_handler(lambda msg: user_list_command(bot, msg), commands=['user_list'], func=lambda msg: is_admin(msg.from_user.id))
    bot.register_message_handler(lambda msg: ban_user_command(bot, msg), commands=['ban_user'], func=lambda msg: is_admin(msg.from_user.id))
    bot.register_message_handler(lambda msg: unban_user_command(bot, msg), commands=['unban_user'], func=lambda msg: is_admin(msg.from_user.id))
    bot.register_message_handler(lambda msg: broadcast_command(bot, msg), commands=['broadcast'], func=lambda msg: is_admin(msg.from_user.id))
    bot.register_message_handler(lambda msg: add_admin_command(bot, msg), commands=['add_admin'], func=lambda msg: is_admin(msg.from_user.id))
    
    # Debug commands
    bot.register_message_handler(lambda msg: debug_user_command(bot, msg), commands=['debug_user'], func=lambda msg: is_admin(msg.from_user.id))
    bot.register_message_handler(lambda msg: check_ban_command(bot, msg), commands=['check_ban'], func=lambda msg: is_admin(msg.from_user.id))
    bot.register_message_handler(lambda msg: force_ban_command(bot, msg), commands=['force_ban'], func=lambda msg: is_admin(msg.from_user.id))
    
    # Callback query handlers
    bot.register_callback_query_handler(lambda call: handle_callback_query(bot, call), func=lambda call: True)
    
    # State handlers
    bot.register_message_handler(lambda msg: handle_state(bot, msg), content_types=['text'], func=lambda msg: msg.from_user.id in user_states)

def start_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /start"""
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    logger.info(f"User {username} (ID: {user_id}) started the bot")
    
    # Import datetime để sử dụng trong hàm này
    import datetime
    
    # Kiểm tra xem người dùng đã tồn tại chưa
    user = db.get_user(user_id)
    if not user:
        # Tạo người dùng mới
        user_data = {
            'id': user_id,
            'username': username,
            'balance': 0,
            'banned': False,
            'purchases': [],
            'created_at': datetime.datetime.now().isoformat()
        }
        # Thêm người dùng vào database
        success = db.add_user(user_data)
        
        if success:
            # Sử dụng user_data thay vì gọi lại get_user
            user = user_data
            
            # Thông báo cho admin về người dùng mới
            admin_notification = (
                f"👤 *Người dùng mới tham gia!*\n\n"
                f"ID: `{user_id}`\n"
                f"Username: @{username}\n"
                f"Thời gian: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            notify_admins(bot, admin_notification, parse_mode="Markdown")
        else:
            # Thử lấy lại thông tin người dùng
            user = db.get_user(user_id)
            if not user:
                # Nếu vẫn không tìm thấy, đây là lỗi thực sự
                logger.error(f"Failed to add new user {username} (ID: {user_id}) to database")
                bot.send_message(user_id, "Có lỗi xảy ra khi đăng ký tài khoản. Vui lòng thử lại sau.")
                return
    
    # Kiểm tra xem người dùng có bị cấm không - in ra log để debug
    is_banned = user.get('banned', False)
    logger.info(f"User {username} (ID: {user_id}) banned status: {is_banned}")
    
    if is_banned:
        bot.send_message(user_id, "⛔ Tài khoản của bạn đã bị cấm. Vui lòng liên hệ quản trị viên.")
        return
    
    # Gửi tin nhắn chào mừng
    welcome_text = (
        f"🏠 *Menu chính*\n\n"
        f"👋 Chào mừng, {username}!\n"
        f"Đây là bot mua bán tài khoản. Sử dụng các nút bên dưới để điều hướng.\n\n"
        f"Số dư hiện tại: {user.get('balance', 0):,} {config.CURRENCY}"
    )
    
    bot.send_message(
        user_id,
        welcome_text,
        parse_mode="Markdown",
        reply_markup=keyboards.main_menu(is_admin(user_id))
    )

def help_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /help"""
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    logger.info(f"User {username} (ID: {user_id}) requested help")
    
    # Kiểm tra xem người dùng có bị cấm không
    user = db.get_user(user_id)
    if user and user.get('banned', False):
        bot.send_message(user_id, "⛔ Tài khoản của bạn đã bị cấm. Vui lòng liên hệ quản trị viên.")
        return
    
    help_text = (
        "🔍 *Hướng dẫn sử dụng bot*\n\n"
        "*Các lệnh cơ bản:*\n"
        "/start - Khởi động bot\n"
        "/help - Hiển thị trợ giúp\n"
        "/dashboard - Mở bảng điều khiển\n\n"
        
        "*Cách sử dụng:*\n"
        "1. Chọn loại tài khoản (trả phí/miễn phí)\n"
        "2. Chọn sản phẩm bạn muốn mua\n"
        "3. Xác nhận giao dịch\n"
        "4. Nhận thông tin tài khoản\n\n"
        
        "*Nạp tiền:*\n"
        "Vui lòng liên hệ quản trị viên để nạp tiền vào tài khoản của bạn."
    )
    
    # Chỉ hiển thị lệnh quản trị viên cho admin
    if is_admin(user_id):
        help_text += (
            "\n\n*Lệnh quản trị viên:*\n"
            "/create\\_product [tên] [giá] - Tạo/sửa sản phẩm\n"
            "/product\\_list - Xem danh sách sản phẩm\n"
            "/upload\\_product [product_id] - Upload tài khoản cho sản phẩm\n"
            "/add\\_money [user_id] [số tiền] - Thêm tiền cho người dùng\n"
            "/user\\_list - Xem danh sách người dùng\n"
            "/ban\\_user [user_id] - Cấm người dùng\n"
            "/unban\\_user [user_id] - Bỏ cấm người dùng\n"
            "/broadcast - Gửi thông báo đến tất cả người dùng\n"
            "/add\\_admin [user_id] - Thêm quản trị viên mới\n"
            "/debug\\_user [user_id] - Xem thông tin debug của người dùng\n"
            "/check\\_ban [user_id] - Kiểm tra trạng thái cấm của người dùng\n"
            "/force\\_ban [user_id] - Cấm người dùng (phương pháp thay thế)\n"
        )
    
    bot.send_message(
        user_id,
        help_text,
        parse_mode="Markdown",
        reply_markup=keyboards.back_button()
    )

def dashboard_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /dashboard"""
    user_id = message.from_user.id
    
    # Kiểm tra xem người dùng có bị cấm không
    user = db.get_user(user_id)
    if user and user.get('banned', False):
        bot.send_message(user_id, "⛔ Tài khoản của bạn đã bị cấm. Vui lòng liên hệ quản trị viên.")
        return
    
    bot.send_message(
        user_id,
        "🎛️ *Bảng điều khiển*\n\nChọn một tùy chọn bên dưới:",
        parse_mode="Markdown",
        reply_markup=keyboards.main_menu(is_admin(user_id))
    )

def create_product_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /create_product"""
    user_id = message.from_user.id
    
    # Phân tích cú pháp lệnh
    args = message.text.split(maxsplit=2)
    
    if len(args) < 3:
        bot.send_message(
            user_id,
            "❌ Sử dụng sai cú pháp. Vui lòng sử dụng: /create_product [tên] [giá]\n"
            "Ví dụ: /create_product \"Netflix Premium\" 50000"
        )
        return
    
    name = args[1]
    try:
        price = float(args[2])
    except ValueError:
        bot.send_message(user_id, "❌ Giá phải là một số.")
        return
    
    # Tạo sản phẩm mới
    product_data = {
        'name': name,
        'price': price,
        'is_free': price <= 0,
        'description': f"Sản phẩm: {name}"
    }
    
    product_id = db.create_product(product_data)
    
    bot.send_message(
        user_id,
        f"✅ Đã tạo sản phẩm thành công!\n\n"
        f"ID: {product_id}\n"
        f"Tên: {name}\n"
        f"Giá: {price:,} {config.CURRENCY}\n"
        f"Loại: {'Miễn phí' if price <= 0 else 'Trả phí'}"
    )

def product_list_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /product_list"""
    user_id = message.from_user.id
    
    products = db.get_all_products()
    
    if not products:
        bot.send_message(user_id, "📦 Chưa có sản phẩm nào.")
        return
    
    bot.send_message(
        user_id,
        "📋 *Danh sách sản phẩm*\n\nChọn một sản phẩm để xem chi tiết:",
        parse_mode="Markdown",
        reply_markup=keyboards.product_list_keyboard(products, admin=True)
    )

def upload_product_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /upload_product"""
    user_id = message.from_user.id
    
    # Phân tích cú pháp lệnh
    args = message.text.split()
    
    if len(args) < 2:
        bot.send_message(
            user_id,
            "❌ Sử dụng sai cú pháp. Vui lòng sử dụng: /upload_product [product_id]"
        )
        return
    
    try:
        product_id = int(args[1])
    except ValueError:
        bot.send_message(user_id, "❌ ID sản phẩm phải là một số.")
        return
    
    # Kiểm tra sản phẩm tồn tại
    product = db.get_product(product_id)
    if not product:
        bot.send_message(user_id, f"❌ Không tìm thấy sản phẩm với ID {product_id}.")
        return
    
    # Lưu trạng thái người dùng để xử lý tin nhắn tiếp theo
    user_states[user_id] = {
        'state': 'waiting_for_accounts',
        'product_id': product_id
    }
    
    bot.send_message(
        user_id,
        f"📤 Vui lòng gửi danh sách tài khoản cho sản phẩm *{product['name']}*.\n\n"
        f"Mỗi tài khoản trên một dòng, định dạng: `username:password` hoặc bất kỳ định dạng nào bạn muốn.\n\n"
        f"Ví dụ:\n"
        f"```\n"
        f"user1@example.com:password1\n"
        f"user2@example.com:password2\n"
        f"```",
        parse_mode="Markdown"
    )

def add_money_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /add_money"""
    user_id = message.from_user.id
    
    # Phân tích cú pháp lệnh
    args = message.text.split()
    
    if len(args) < 3:
        bot.send_message(
            user_id,
            "❌ Sử dụng sai cú pháp. Vui lòng sử dụng: /add_money [user_id] [số tiền]"
        )
        return
    
    try:
        target_user_id = int(args[1])
        amount = float(args[2])
    except ValueError:
        bot.send_message(user_id, "❌ ID người dùng và số tiền phải là số.")
        return
    
    if amount <= 0:
        bot.send_message(user_id, "❌ Số tiền phải lớn hơn 0.")
        return
    
    # Kiểm tra người dùng tồn tại
    target_user = db.get_user(target_user_id)
    if not target_user:
        bot.send_message(user_id, f"❌ Không tìm thấy người dùng với ID {target_user_id}.")
        return
    
    # Thêm tiền cho người dùng
    success = db.add_money(target_user_id, amount)
    if success:
        new_balance = db.get_user(target_user_id).get('balance', 0)
        bot.send_message(
            user_id,
            f"✅ Đã thêm {amount:,} {config.CURRENCY} cho người dùng {target_user.get('username', target_user_id)}.\n"
            f"Số dư mới: {new_balance:,} {config.CURRENCY}"
        )
        
        # Thông báo cho người dùng
        bot.send_message(
            target_user_id,
            f"💰 Tài khoản của bạn vừa được cộng {amount:,} {config.CURRENCY}.\n"
            f"Số dư hiện tại: {new_balance:,} {config.CURRENCY}"
        )
    else:
        bot.send_message(user_id, "❌ Không thể thêm tiền cho người dùng này.")

def user_list_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /user_list"""
    user_id = message.from_user.id
    
    users = db.get_all_users()
    
    if not users:
        bot.send_message(user_id, "👥 Chưa có người dùng nào.")
        return
    
    # Lưu trạng thái để xử lý phân trang
    user_states[user_id] = {
        'state': 'viewing_user_list',
        'page': 0,
        'users': users,
        'search_query': ''
    }
    
    # Hiển thị trang đầu tiên
    display_user_list_page(bot, user_id, message.message_id)

def display_user_list_page(bot: TeleBot, user_id: int, message_id: int = None) -> None:
    """Hiển thị một trang danh sách người dùng"""
    state = user_states.get(user_id, {})
    users = state.get('users', [])
    page = state.get('page', 0)
    search_query = state.get('search_query', '').lower()
    
    # Lọc người dùng theo từ khóa tìm kiếm nếu có
    if search_query:
        filtered_users = []
        for user in users:
            username = str(user.get('username', '')).lower()
            user_id_str = str(user.get('id', ''))
            if search_query in username or search_query in user_id_str:
                filtered_users.append(user)
        users = filtered_users
    
    # Số người dùng mỗi trang
    per_page = 5
    total_pages = (len(users) + per_page - 1) // per_page
    
    if total_pages == 0:
        text = "🔍 Không tìm thấy người dùng nào phù hợp."
        markup = keyboards.user_list_navigation_keyboard(0, 0, search_query)
    else:
        # Lấy người dùng cho trang hiện tại
        start_idx = page * per_page
        end_idx = min(start_idx + per_page, len(users))
        current_users = users[start_idx:end_idx]
        
        # Tạo nội dung tin nhắn
        text = f"👥 *Danh sách người dùng* (Trang {page+1}/{total_pages})\n\n"
        
        for i, user in enumerate(current_users, 1):
            username = user.get('username', 'Không có')
            user_id = user.get('id', 'N/A')
            balance = user.get('balance', 0)
            banned = "🚫" if user.get('banned', False) else "✅"
            
            text += f"{i}. {banned} @{username} (ID: `{user_id}`)\n   💰 {balance:,} {config.CURRENCY}\n\n"
        
        # Tạo bàn phím điều hướng
        markup = keyboards.user_list_navigation_keyboard(page, total_pages, search_query)
    
    # Gửi hoặc cập nhật tin nhắn
    if message_id:
        try:
            bot.edit_message_text(
                text,
                user_id,
                message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
        except Exception as e:
            logger.error(f"Error updating user list message: {e}")
            # Nếu không thể cập nhật, gửi tin nhắn mới
            bot.send_message(
                user_id,
                text,
                parse_mode="Markdown",
                reply_markup=markup
            )
    else:
        bot.send_message(
            user_id,
            text,
            parse_mode="Markdown",
            reply_markup=markup
        )

def ban_user_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /ban_user"""
    user_id = message.from_user.id
    
    # Kiểm tra quyền admin
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Bạn không có quyền thực hiện lệnh này.")
        return
    
    # Phân tích cú pháp lệnh
    args = message.text.split()
    
    if len(args) < 2:
        bot.send_message(
            user_id,
            "❌ Sử dụng sai cú pháp. Vui lòng sử dụng: /ban_user [user_id]"
        )
        return
    
    try:
        target_user_id = int(args[1])
    except ValueError:
        bot.send_message(user_id, "❌ ID người dùng phải là một số.")
        return
    
    # Kiểm tra người dùng tồn tại
    target_user = db.get_user(target_user_id)
    if not target_user:
        bot.send_message(user_id, f"❌ Không tìm thấy người dùng với ID {target_user_id}.")
        return
    
    # Không thể cấm admin
    if target_user_id in config.ADMIN_IDS:
        bot.send_message(user_id, "❌ Không thể cấm quản trị viên.")
        return
    
    # Kiểm tra xem người dùng đã bị cấm chưa
    if target_user.get('banned', False):
        bot.send_message(user_id, f"❌ Người dùng {target_user.get('username', target_user_id)} đã bị cấm rồi.")
        return
    
    # Sử dụng hàm ban_user từ database
    logger.info(f"Admin {message.from_user.username} (ID: {user_id}) is banning user {target_user_id}")
    success = db.ban_user(target_user_id)
    
    if success:
        # Gửi thông báo thành công
        bot.send_message(
            user_id,
            f"✅ Đã cấm người dùng {target_user.get('username', target_user_id)} thành công."
        )
        
        # Thông báo cho người dùng
        try:
            bot.send_message(
                target_user_id,
                "⛔ Tài khoản của bạn đã bị cấm. Vui lòng liên hệ quản trị viên."
            )
            logger.info(f"Notification sent to banned user {target_user_id}")
        except Exception as e:
            logger.error(f"Không thể gửi thông báo đến người dùng bị cấm: {e}")
    else:
        bot.send_message(user_id, f"❌ Không thể cấm người dùng với ID {target_user_id}. Hãy kiểm tra lại hoặc thử lại sau.")

def unban_user_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /unban_user"""
    user_id = message.from_user.id
    
    # Kiểm tra quyền admin
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Bạn không có quyền thực hiện lệnh này.")
        return
    
    # Phân tích cú pháp lệnh
    args = message.text.split()
    
    if len(args) < 2:
        bot.send_message(
            user_id,
            "❌ Sử dụng sai cú pháp. Vui lòng sử dụng: /unban_user [user_id]"
        )
        return
    
    try:
        target_user_id = int(args[1])
    except ValueError:
        bot.send_message(user_id, "❌ ID người dùng phải là một số.")
        return
    
    # Kiểm tra người dùng tồn tại
    target_user = db.get_user(target_user_id)
    if not target_user:
        bot.send_message(user_id, f"❌ Không tìm thấy người dùng với ID {target_user_id}.")
        return
    
    # Kiểm tra xem người dùng có bị cấm không
    if not target_user.get('banned', False):
        bot.send_message(user_id, f"❌ Người dùng {target_user.get('username', target_user_id)} không bị cấm.")
        return
    
    # Sử dụng hàm unban_user từ database
    logger.info(f"Admin {message.from_user.username} (ID: {user_id}) is unbanning user {target_user_id}")
    success = db.unban_user(target_user_id)
    
    if success:
        # Gửi thông báo thành công
        bot.send_message(
            user_id,
            f"✅ Đã bỏ cấm người dùng {target_user.get('username', target_user_id)} thành công."
        )
        
        # Thông báo cho người dùng
        try:
            bot.send_message(
                target_user_id,
                "🎉 Tài khoản của bạn đã được bỏ cấm. Bạn có thể sử dụng bot bình thường."
            )
            logger.info(f"Notification sent to unbanned user {target_user_id}")
        except Exception as e:
            logger.error(f"Không thể gửi thông báo đến người dùng được bỏ cấm: {e}")
    else:
        bot.send_message(user_id, f"❌ Không thể bỏ cấm người dùng với ID {target_user_id}. Hãy kiểm tra lại hoặc thử lại sau.")

def broadcast_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /broadcast - Gửi thông báo đến tất cả người dùng"""
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    logger.info(f"Admin {username} (ID: {user_id}) started broadcast")
    
    # Lưu trạng thái để nhận nội dung thông báo
    user_states[user_id] = {
        'state': 'waiting_for_broadcast',
        'data': {}
    }
    
    bot.send_message(
        user_id,
        "📣 *Gửi thông báo đến tất cả người dùng*\n\n"
        "Vui lòng nhập nội dung thông báo bạn muốn gửi.\n"
        "Bạn có thể sử dụng định dạng Markdown.\n\n"
        "Gửi /cancel để hủy.",
        parse_mode="Markdown"
    )

def handle_state(bot: TeleBot, message: Message) -> None:
    """Xử lý trạng thái người dùng"""
    # Lấy thông tin người dùng
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    # Lấy trạng thái hiện tại của người dùng
    state = user_states.get(user_id, {}).get('state', None)
    
    if not state:
        return
    
    # Xử lý các trạng thái khác nhau
    if state == 'waiting_for_create_product_name':
        # Xử lý nhập tên sản phẩm
        user_states[user_id]['state'] = 'waiting_for_product_price'
        bot.send_message(
            user_id,
            f"👍 Đã lưu tên sản phẩm: *{user_states[user_id]['data']['name']}*\n\n"
            f"Vui lòng nhập giá cho sản phẩm (số):",
            parse_mode="Markdown"
        )
    
    elif state == 'waiting_for_product_price':
        # Xử lý giá sản phẩm
        try:
            price = float(message.text.strip())
            if price < 0:
                bot.send_message(user_id, "❌ Giá sản phẩm không thể âm.")
                return
        except ValueError:
            bot.send_message(user_id, "❌ Giá sản phẩm phải là một số.")
            return
        
        # Lấy dữ liệu sản phẩm
        product_name = user_states[user_id]['data']['name']
        
        # Chuyển sang trạng thái chờ mô tả
        user_states[user_id]['data']['price'] = price
        user_states[user_id]['state'] = 'waiting_for_product_description'
        
        bot.send_message(
            user_id,
            f"👍 Đã lưu giá sản phẩm: *{price:,}* {config.CURRENCY}\n\n"
            f"Vui lòng nhập mô tả cho sản phẩm:",
            parse_mode="Markdown"
        )
    
    elif state == 'waiting_for_product_description':
        # Xử lý mô tả sản phẩm
        product_data = user_states[user_id]['data']
        product_data['description'] = message.text.strip()
        
        # Tạo sản phẩm mới
        new_id = db.create_product(product_data)
        
        # Xóa trạng thái
        del user_states[user_id]
        
        bot.send_message(
            user_id,
            f"✅ Đã tạo sản phẩm mới thành công!\n\n"
            f"ID: {new_id}\n"
            f"Tên: {product_data['name']}\n"
            f"Giá: {product_data['price']:,} {config.CURRENCY}\n"
            f"Mô tả: {text}",
            reply_markup=keyboards.back_button("back_to_product_list")
        )
    
    elif state == 'edit_product_name':
        # Xử lý tên sản phẩm mới
        product_id = user_states[user_id]['product_id']
        product_data = user_states[user_id]['data']
        
        if text.lower() != 'giữ nguyên':
            product_data['name'] = text
        
        # Chuyển sang trạng thái chỉnh sửa giá
        user_states[user_id]['state'] = 'edit_product_price'
        
        bot.send_message(
            user_id,
            f"👍 Tên sản phẩm: *{product_data['name']}*\n\n"
            f"Vui lòng nhập giá mới cho sản phẩm (hoặc gõ 'giữ nguyên' để không thay đổi):",
            parse_mode="Markdown"
        )
    
    elif state == 'edit_product_price':
        # Xử lý giá sản phẩm mới
        product_id = user_states[user_id]['product_id']
        product_data = user_states[user_id]['data']
        
        if text.lower() != 'giữ nguyên':
            try:
                price = float(text)
                if price < 0:
                    bot.send_message(user_id, "❌ Giá sản phẩm không thể âm.")
                    return
                product_data['price'] = price
            except ValueError:
                bot.send_message(user_id, "❌ Giá sản phẩm phải là một số. Vui lòng nhập lại.")
                return
        
        # Chuyển sang trạng thái chỉnh sửa mô tả
        user_states[user_id]['state'] = 'edit_product_description'
        
        bot.send_message(
            user_id,
            f"👍 Giá sản phẩm: *{product_data['price']:,}* {config.CURRENCY}\n\n"
            f"Vui lòng nhập mô tả mới cho sản phẩm (hoặc gõ 'giữ nguyên' để không thay đổi):",
            parse_mode="Markdown"
        )
    
    elif state == 'edit_product_description':
        # Xử lý mô tả sản phẩm mới
        product_id = user_states[user_id]['product_id']
        product_data = user_states[user_id]['data']
        
        if text.lower() != 'giữ nguyên':
            product_data['description'] = text
        
        # Cập nhật sản phẩm trong cơ sở dữ liệu
        try:
            db.create_product(product_data)
            
            # Xóa trạng thái
            del user_states[user_id]
            
            bot.send_message(
                user_id,
                f"✅ Đã cập nhật sản phẩm thành công!\n\n"
                f"ID: {product_id}\n"
                f"Tên: {product_data['name']}\n"
                f"Giá: {product_data['price']:,} {config.CURRENCY}\n"
                f"Mô tả: {product_data.get('description', 'Không có')}",
                reply_markup=keyboards.back_button("back_to_product_list")
            )
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật sản phẩm: {e}")
            bot.send_message(
                user_id,
                "❌ Đã xảy ra lỗi khi cập nhật sản phẩm. Vui lòng thử lại sau."
            )
    
    elif state == 'waiting_for_accounts':
        # Xử lý upload tài khoản
        product_id = user_states[user_id]['product_id']
        product = db.get_product(product_id)
        
        if not product:
            bot.send_message(user_id, "❌ Sản phẩm không tồn tại.")
            del user_states[user_id]
            return
        
        # Phân tích danh sách tài khoản
        accounts = text.strip().split('\n')
        accounts = [account.strip() for account in accounts if account.strip()]
        
        if not accounts:
            bot.send_message(user_id, "❌ Danh sách tài khoản không hợp lệ.")
            return
        
        # Thêm tài khoản vào cơ sở dữ liệu
        count = db.add_accounts(product_id, accounts)
        
        # Xóa trạng thái
        del user_states[user_id]
        
        bot.send_message(
            user_id,
            f"✅ Đã thêm {count} tài khoản cho sản phẩm *{product['name']}* thành công!",
            parse_mode="Markdown"
        )
    
    elif state == 'waiting_for_user_id_to_add_money':
        # Xử lý ID người dùng để thêm tiền
        try:
            target_user_id = int(text.strip())
            target_user = db.get_user(target_user_id)
            
            if not target_user:
                bot.send_message(
                    user_id,
                    "❌ Không tìm thấy người dùng với ID này. Vui lòng kiểm tra lại."
                )
                return
            
            # Lưu ID người dùng và chuyển sang trạng thái nhập số tiền
            user_states[user_id] = {
                'state': 'waiting_for_add_money_amount',
                'target_user_id': target_user_id
            }
            
            bot.send_message(
                user_id,
                f"💰 Thêm tiền cho người dùng:\n\n"
                f"ID: {target_user['id']}\n"
                f"Username: @{target_user.get('username', 'Không có')}\n"
                f"Số dư hiện tại: {target_user.get('balance', 0):,} {config.CURRENCY}\n\n"
                f"Vui lòng nhập số tiền muốn thêm:"
            )
        except ValueError:
            bot.send_message(
                user_id,
                "❌ ID người dùng phải là một số. Vui lòng nhập lại."
            )

    elif state == 'waiting_for_add_money_amount':
        # Xử lý số tiền cần thêm
        try:
            amount = int(text.strip())
            if amount <= 0:
                bot.send_message(
                    user_id,
                    "❌ Số tiền phải lớn hơn 0. Vui lòng nhập lại."
                )
                return
            
            target_user_id = user_states[user_id]['target_user_id']
            target_user = db.get_user(target_user_id)
            
            if not target_user:
                bot.send_message(
                    user_id,
                    "❌ Không tìm thấy người dùng. Vui lòng thử lại."
                )
                del user_states[user_id]
                return
            
            # Cập nhật số dư
            current_balance = target_user.get('balance', 0)
            new_balance = current_balance + amount
            
            if db.update_user(target_user_id, {'balance': new_balance}):
                # Xóa trạng thái
                del user_states[user_id]
                
                bot.send_message(
                    user_id,
                    f"✅ Đã thêm {amount:,} {config.CURRENCY} cho người dùng @{target_user.get('username', 'Không có')}.\n"
                    f"Số dư mới: {new_balance:,} {config.CURRENCY}",
                    reply_markup=keyboards.back_button("back_to_user_management")
                )
                
                # Thông báo cho người dùng
                try:
                    bot.send_message(
                        target_user_id,
                        f"💰 Tài khoản của bạn vừa được cộng thêm {amount:,} {config.CURRENCY}.\n"
                        f"Số dư hiện tại: {new_balance:,} {config.CURRENCY}"
                    )
                except Exception as e:
                    logger.error(f"Không thể gửi thông báo đến người dùng {target_user_id}: {e}")
            else:
                bot.send_message(
                    user_id,
                    "❌ Không thể cập nhật số dư. Vui lòng thử lại sau."
                )
                del user_states[user_id]
        except ValueError:
            bot.send_message(
                user_id,
                "❌ Số tiền phải là một số. Vui lòng nhập lại."
            )
    
    elif state == 'searching_user':
        # Xử lý tìm kiếm người dùng
        search_query = message.text.strip().lower()
        user_states[user_id]['search_query'] = search_query
        user_states[user_id]['page'] = 0
        user_states[user_id]['state'] = 'viewing_user_list'
        
        bot.delete_message(user_id, message.message_id)
        display_user_list_page(bot, user_id)

    elif state == 'waiting_for_broadcast':
        # Xử lý broadcast message
        broadcast_message = text
        
        # Xóa trạng thái
        del user_states[user_id]
        
        # Hiển thị tin nhắn xác nhận
        bot.send_message(
            user_id,
            "🔄 Đang gửi thông báo đến tất cả người dùng... Quá trình này có thể mất một chút thời gian."
        )
        
        # Thực hiện gửi thông báo
        users = db.get_all_users()
        success_count = 0
        fail_count = 0
        
        for user_item in users:
            try:
                target_id = user_item.get('id')
                if target_id != user_id:  # Không gửi cho chính mình
                    bot.send_message(
                        target_id,
                        f"📣 *THÔNG BÁO TỪ QUẢN TRỊ VIÊN*\n\n{broadcast_message}",
                        parse_mode="Markdown"
                    )
                    success_count += 1
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo đến người dùng {user_item.get('id')}: {e}")
                fail_count += 1
        
        # Gửi thông báo kết quả
        bot.send_message(
            user_id,
            f"✅ Đã gửi thông báo thành công:\n"
            f"- Số người nhận được: {success_count}\n"
            f"- Số lỗi: {fail_count}"
        )
    
    elif state == 'waiting_for_ban_user_id':
        # Xử lý ID người dùng để cấm
        try:
            target_user_id = int(text.strip())
            
            # Kiểm tra người dùng tồn tại
            target_user = db.get_user(target_user_id)
            if not target_user:
                bot.send_message(user_id, f"❌ Không tìm thấy người dùng với ID {target_user_id}.")
                return
            
            # Kiểm tra nếu là admin
            if target_user_id in config.ADMIN_IDS:
                bot.send_message(user_id, "❌ Không thể cấm quản trị viên.")
                return
            
            # Kiểm tra nếu đã bị cấm
            if target_user.get('banned', False):
                bot.send_message(user_id, f"❌ Người dùng {target_user.get('username', target_user_id)} đã bị cấm rồi.")
                return
            
            # Cấm người dùng
            success = db.ban_user(target_user_id)
            
            # Xóa trạng thái
            del user_states[user_id]
            
            if success:
                bot.send_message(
                    user_id,
                    f"✅ Đã cấm người dùng {target_user.get('username', target_user_id)} thành công."
                )
                
                # Thông báo cho người dùng bị cấm
                try:
                    bot.send_message(
                        target_user_id,
                        "⛔ Tài khoản của bạn đã bị cấm. Vui lòng liên hệ quản trị viên."
                    )
                except Exception as e:
                    logger.error(f"Không thể gửi thông báo đến người dùng bị cấm: {e}")
            else:
                bot.send_message(
                    user_id,
                    f"❌ Không thể cấm người dùng với ID {target_user_id}. Hãy kiểm tra lại hoặc thử lại sau."
                )
        except ValueError:
            bot.send_message(user_id, "❌ ID người dùng phải là một số.")
    
    elif state == 'waiting_for_unban_user_id':
        # Xử lý ID người dùng để bỏ cấm
        try:
            target_user_id = int(text.strip())
            
            # Kiểm tra người dùng tồn tại
            target_user = db.get_user(target_user_id)
            if not target_user:
                bot.send_message(user_id, f"❌ Không tìm thấy người dùng với ID {target_user_id}.")
                return
            
            # Kiểm tra nếu chưa bị cấm
            if not target_user.get('banned', False):
                bot.send_message(user_id, f"❌ Người dùng {target_user.get('username', target_user_id)} không bị cấm.")
                return
            
            # Bỏ cấm người dùng
            success = db.unban_user(target_user_id)
            
            # Xóa trạng thái
            del user_states[user_id]
            
            if success:
                bot.send_message(
                    user_id,
                    f"✅ Đã bỏ cấm người dùng {target_user.get('username', target_user_id)} thành công."
                )
                
                # Thông báo cho người dùng được bỏ cấm
                try:
                    bot.send_message(
                        target_user_id,
                        "🎉 Tài khoản của bạn đã được bỏ cấm. Bạn có thể sử dụng bot bình thường."
                    )
                except Exception as e:
                    logger.error(f"Không thể gửi thông báo đến người dùng được bỏ cấm: {e}")
            else:
                bot.send_message(
                    user_id,
                    f"❌ Không thể bỏ cấm người dùng với ID {target_user_id}. Hãy kiểm tra lại hoặc thử lại sau."
                )
        except ValueError:
            bot.send_message(user_id, "❌ ID người dùng phải là một số.")
    
    # Thêm các trạng thái khác ở đây

    # Thêm xử lý cho trạng thái chờ nhập số tiền nạp tùy chọn
    elif state == 'waiting_for_deposit_amount':
        # Xử lý nhập số tiền nạp tùy chọn
        try:
            # Xóa dấu phẩy nếu có và chuyển đổi sang số nguyên
            amount_text = message.text.strip().replace(',', '')
            amount = int(amount_text)
            
            # Kiểm tra số tiền tối thiểu
            if amount < 10000:
                bot.send_message(
                    user_id,
                    "❌ Số tiền tối thiểu là 10,000 VNĐ. Vui lòng nhập lại.",
                    reply_markup=keyboards.back_button("deposit_money")
                )
                return
            
            # Tạo QR code
            qr_image_data = generate_qr_code(user_id, amount)
            
            if qr_image_data:
                # Tạo caption
                caption = (
                    f"💳 *Mã QR thanh toán*\n\n"
                    f"Số tiền: {amount:,} {config.CURRENCY}\n"
                    f"Người nhận: {config.BANK_ACCOUNT_NAME}\n"
                    f"Số tài khoản: {config.BANK_ACCOUNT_NO}\n"
                    f"Nội dung: NAP TIEN USER {user_id}\n\n"
                    f"⚠️ Vui lòng chuyển đúng số tiền và nội dung để hệ thống xác nhận tự động.\n"
                    f"👉 Sau khi chuyển khoản, vui lòng đợi 1-5 phút để hệ thống cập nhật."
                )
                
                # Lưu QR code tạm thời
                qr_filename = f"qr_{user_id}_{int(datetime.datetime.now().timestamp())}.png"
                with open(qr_filename, "wb") as f:
                    f.write(qr_image_data)
                
                # Gửi QR code
                with open(qr_filename, "rb") as f:
                    bot.send_photo(
                        user_id,
                        f,
                        caption=caption,
                        parse_mode="Markdown",
                        reply_markup=keyboards.back_button("account_menu")
                    )
                
                # Xóa file tạm
                try:
                    os.remove(qr_filename)
                except:
                    pass
                
                # Xóa trạng thái người dùng
                if user_id in user_states:
                    del user_states[user_id]
                
                # Thông báo cho admin về giao dịch mới
                admin_notification = (
                    f"💰 *Yêu cầu nạp tiền mới (số tiền tùy chọn)*\n\n"
                    f"💰 *Yêu cầu nạp tiền mới*\n\n"
                    f"User: @{username} (ID: `{user_id}`)\n"
                    f"Số tiền: {amount:,} {config.CURRENCY}\n"
                    f"Thời gian: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"Nội dung chuyển khoản: `NAP TIEN USER {user_id}`"
                )
                notify_admins(bot, admin_notification, "Markdown")
                
            else:
                # Thông báo lỗi nếu không tạo được QR
                bot.answer_callback_query(
                    call.id,
                    "Không thể tạo mã QR. Vui lòng thử lại sau hoặc liên hệ admin.",
                    show_alert=True
                )
                
                # Quay lại menu tài khoản
                bot.edit_message_text(
                    f"👤 *Quản lý tài khoản*\n\n"
                    f"Xin chào, {username}!\n"
                    f"Số dư hiện tại: {user.get('balance', 0):,} {config.CURRENCY}\n\n"
                    f"Chọn một trong các tùy chọn bên dưới:",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=keyboards.account_menu()
                )
                
        except Exception as e:
            logger.error(f"Error processing deposit: {str(e)}")
            bot.answer_callback_query(
                call.id,
                "Có lỗi xảy ra. Vui lòng thử lại sau.",
                show_alert=True
            )
    
    elif data == "custom_amount":
        # Yêu cầu người dùng nhập số tiền tùy chọn
        bot.edit_message_text(
            "💰 *Nhập số tiền nạp*\n\n"
            "Vui lòng nhập số tiền bạn muốn nạp (VD: 150000).\n"
            "Số tiền tối thiểu là 10,000 VNĐ.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.back_button("deposit_money")
        )
        
        # Lưu trạng thái chờ nhập số tiền
        user_states[user_id] = {
            'state': 'waiting_for_deposit_amount'
        }
    
    # Xử lý phân trang
    elif data.startswith("product_page_"):
        page = int(data.split("_")[2])
        if is_admin(user_id):
            products = db.get_all_products()
            bot.edit_message_text(
                "📋 Danh sách sản phẩm:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.product_list_keyboard(products, page=page, admin=True)
            )
        else:
            products = [p for p in db.get_all_products() if not p.get('is_free', False)]
            bot.edit_message_text(
                "🔐 Danh sách tài khoản trả phí:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.product_list_keyboard(products, page=page)
            )
    
    elif data.startswith("user_page_") and is_admin(user_id):
        page = int(data.split("_")[2])
        users = db.get_all_users()
        bot.edit_message_text(
            "📋 Danh sách người dùng:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.user_list_keyboard(users, page=page)
        )
    
    # Thêm xử lý cho các nút admin
    elif data.startswith("add_money_") and is_admin(user_id):
        # Thêm tiền cho người dùng
        target_user_id = int(data.split("_")[2])
        target_user = db.get_user(target_user_id)
        
        if target_user:
            # Lưu trạng thái để nhận số tiền
            user_states[user_id] = {
                'state': 'waiting_for_add_money',
                'target_user_id': target_user_id
            }
            
            bot.edit_message_text(
                f"💰 Thêm tiền cho người dùng:\n\n"
                f"ID: {target_user['id']}\n"
                f"Username: @{target_user.get('username', 'Không có')}\n"
                f"Số dư hiện tại: {target_user.get('balance', 0):,} {config.CURRENCY}\n\n"
                f"Vui lòng nhập số tiền muốn thêm:"
            )
    
    elif data.startswith("ban_user_") and is_admin(user_id):
        # Cấm người dùng
        target_user_id = int(data.split("_")[2])
        target_user = db.get_user(target_user_id)
        
        if target_user:
            # Không cho phép cấm admin
            if is_admin(target_user_id):
                bot.answer_callback_query(call.id, "⛔ Không thể cấm quản trị viên khác.", show_alert=True)
                return
            
            # Kiểm tra nếu người dùng đã bị cấm
            if target_user.get('banned', False):
                bot.answer_callback_query(call.id, "❌ Người dùng này đã bị cấm rồi.", show_alert=True)
                return
            
            # Cấm người dùng với phương pháp trực tiếp nhất
            logger.info(f"Admin {username} (ID: {user_id}) is banning user {target_user_id} via callback")
            
            try:
                # Đọc dữ liệu hiện tại
                import json
                import os
                
                users_file_path = config.USERS_FILE
                logger.info(f"Reading users data from {users_file_path}")
                
                if not os.path.exists(users_file_path):
                    logger.error(f"Users file does not exist: {users_file_path}")
                    bot.answer_callback_query(call.id, "❌ File dữ liệu người dùng không tồn tại.", show_alert=True)
                    return
                
                # Đọc dữ liệu trực tiếp từ file
                try:
                    with open(users_file_path, 'r', encoding='utf-8') as file:
                        users_data = json.load(file)
                        logger.info(f"Successfully read users data. Found {len(users_data)} users.")
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    bot.answer_callback_query(call.id, "❌ Lỗi định dạng file dữ liệu.", show_alert=True)
                    return
                except Exception as e:
                    logger.error(f"Error reading users file: {e}")
                    bot.answer_callback_query(call.id, f"❌ Lỗi khi đọc file dữ liệu: {str(e)}", show_alert=True)
                    return
                
                # Tìm và cập nhật người dùng
                user_found = False
                for i, user in enumerate(users_data):
                    if user.get('id') == target_user_id:
                        logger.info(f"Found user {target_user_id} at index {i}")
                        users_data[i]['banned'] = True
                        user_found = True
                        break
                
                if not user_found:
                    logger.error(f"User {target_user_id} not found in users data")
                    bot.answer_callback_query(call.id, f"❌ Không tìm thấy người dùng với ID {target_user_id} trong dữ liệu.", show_alert=True)
                    return
                
                # Ghi dữ liệu trở lại file
                try:
                    with open(users_file_path, 'w', encoding='utf-8') as file:
                        json.dump(users_data, file, ensure_ascii=False, indent=2)
                        logger.info(f"Successfully wrote updated data to {users_file_path}")
                except Exception as e:
                    logger.error(f"Error writing to users file: {e}")
                    bot.answer_callback_query(call.id, f"❌ Lỗi khi ghi file dữ liệu: {str(e)}", show_alert=True)
                    return
                
                # Hiển thị thông báo thành công
                bot.edit_message_text(
                    f"✅ Đã cấm người dùng thành công!\n\n"
                    f"ID: {target_user['id']}\n"
                    f"Username: @{target_user.get('username', 'Không có')}",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboards.back_button("back_to_user_list")
                )
                
                # Thông báo cho người dùng
                try:
                    bot.send_message(
                        target_user_id,
                        "⛔ Tài khoản của bạn đã bị cấm. Vui lòng liên hệ quản trị viên."
                    )
                    logger.info(f"Notification sent to banned user {target_user_id}")
                except Exception as e:
                    logger.error(f"Không thể gửi thông báo đến người dùng bị cấm: {e}")
            
            except Exception as e:
                logger.error(f"Unexpected error in ban user callback: {e}", exc_info=True)
                bot.answer_callback_query(call.id, f"❌ Lỗi không xác định: {str(e)}", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"❌ Không tìm thấy người dùng với ID {target_user_id}.", show_alert=True)
    
    elif data.startswith("unban_user_") and is_admin(user_id):
        # Bỏ cấm người dùng
        target_user_id = int(data.split("_")[2])
        target_user = db.get_user(target_user_id)
        
        if target_user:
            # Kiểm tra nếu người dùng không bị cấm
            if not target_user.get('banned', False):
                bot.answer_callback_query(call.id, "❌ Người dùng này không bị cấm.", show_alert=True)
                return
            
            # Bỏ cấm người dùng sử dụng phương pháp trực tiếp nhất
            logger.info(f"Admin {username} (ID: {user_id}) is unbanning user {target_user_id} via callback")
            
            try:
                # Đọc dữ liệu người dùng
                users = db._read_data(config.USERS_FILE)
                
                # Cập nhật trạng thái banned
                user_found = False
                for i, user in enumerate(users):
                    if user.get('id') == target_user_id:
                        users[i]['banned'] = False
                        user_found = True
                        break
                
                if not user_found:
                    bot.answer_callback_query(call.id, "❌ Không thể tìm thấy người dùng trong cơ sở dữ liệu.", show_alert=True)
                    return
                
                # Lưu dữ liệu đã cập nhật
                db._write_data(config.USERS_FILE, users)
                
                # Hiển thị thông báo thành công
                bot.edit_message_text(
                    f"✅ Đã bỏ cấm người dùng thành công!\n\n"
                    f"ID: {target_user['id']}\n"
                    f"Username: @{target_user.get('username', 'Không có')}",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboards.back_button("back_to_user_list")
                )
                
                # Thông báo cho người dùng
                try:
                    bot.send_message(
                        target_user_id,
                        "✅ Tài khoản của bạn đã được bỏ cấm. Bạn có thể sử dụng bot bình thường."
                    )
                except Exception as e:
                    logger.error(f"Không thể gửi thông báo đến người dùng được bỏ cấm: {e}")
            
            except Exception as e:
                logger.error(f"Error unbanning user: {e}")
                bot.answer_callback_query(call.id, f"❌ Đã xảy ra lỗi khi bỏ cấm người dùng: {str(e)}", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"❌ Không tìm thấy người dùng với ID {target_user_id}.", show_alert=True)
    
    elif data.startswith("upload_product_") and is_admin(user_id):
        # Upload tài khoản cho sản phẩm
        product_id = int(data.split("_")[2])
        product = db.get_product(product_id)
        
        if product:
            # Lưu trạng thái để nhận danh sách tài khoản
            user_states[user_id] = {
                'state': 'waiting_for_accounts',
                'product_id': product_id
            }
            
            bot.edit_message_text(
                f"📤 *Upload tài khoản cho sản phẩm*\n\n"
                f"ID: {product['id']}\n"
                f"Tên: {product['name']}\n\n"
                f"Vui lòng nhập danh sách tài khoản, mỗi tài khoản một dòng.\n"
                f"Định dạng: username:password hoặc email:password",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
    
    elif data == "broadcast" and is_admin(user_id):
        # Bắt đầu quá trình gửi thông báo
        user_states[user_id] = {
            'state': 'waiting_for_broadcast',
            'data': {}
        }
        
        bot.edit_message_text(
            "📣 *Gửi thông báo đến tất cả người dùng*\n\n"
            "Vui lòng nhập nội dung thông báo bạn muốn gửi.\n"
            "Bạn có thể sử dụng định dạng Markdown.\n\n"
            "Gửi /cancel để hủy.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    # Thêm xử lý cho nút "Thêm tiền" trong menu quản lý người dùng
    elif data == "add_money" and is_admin(user_id):
        # Hiển thị form nhập ID người dùng để thêm tiền
        user_states[user_id] = {
            'state': 'waiting_for_user_id_to_add_money',
            'data': {}
        }
        
        bot.edit_message_text(
            "💰 *Thêm tiền cho người dùng*\n\n"
            "Vui lòng nhập ID người dùng bạn muốn thêm tiền:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    # Thêm xử lý cho nút xem chi tiết người dùng
    elif data.startswith("view_user_") and is_admin(user_id):
        # Xem chi tiết người dùng
        target_user_id = int(data.split("_")[2])
        target_user = db.get_user(target_user_id)
        
        if target_user:
            # Hiển thị thông tin người dùng
            purchases = target_user.get('purchases', [])
            purchase_count = len(purchases)
            total_spent = sum(p.get('price', 0) for p in purchases)
            status = '🚫 Bị cấm' if target_user.get('banned', False) else '✅ Hoạt động'
            
            user_info = (
                f"👤 *Thông tin người dùng*\n\n"
                f"ID: `{target_user['id']}`\n"
                f"Username: @{target_user.get('username', 'Không có')}\n"
                f"Tên: {target_user.get('first_name', '')} {target_user.get('last_name', '')}\n"
                f"Số dư: {target_user.get('balance', 0)} VNĐ\n"
                f"Trạng thái: {status}"
            )
            
            bot.edit_message_text(
                user_info,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboards.user_detail_keyboard(target_user_id)
            )
    
    elif data == "add_admin" and is_admin(user_id):
        # Yêu cầu admin nhập ID người dùng để thêm làm admin
        user_states[user_id] = {
            'state': 'waiting_for_admin_id',
            'data': {}
        }
        
        bot.edit_message_text(
            "👑 *Thêm quản trị viên mới*\n\n"
            "Vui lòng nhập ID người dùng bạn muốn thêm làm quản trị viên:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    # Sửa phần xử lý nút edit_product trong hàm handle_callback_query
    elif data.startswith("edit_product_") and is_admin(user_id):
        # Lấy ID sản phẩm
        product_id = int(data.split("_")[2])
        product = db.get_product(product_id)
        
        if product:
            # Lưu trạng thái để chỉnh sửa sản phẩm
            user_states[user_id] = {
                'state': 'edit_product_name',
                'product_id': product_id,
                'data': {
                    'id': product_id,
                    'name': product.get('name', ''),
                    'price': product.get('price', 0),
                    'description': product.get('description', '')
                }
            }
            
            bot.edit_message_text(
                f"✏️ *Chỉnh sửa sản phẩm*\n\n"
                f"ID: {product['id']}\n"
                f"Tên hiện tại: {product['name']}\n"
                f"Giá hiện tại: {product['price']:,} {config.CURRENCY}\n"
                f"Mô tả hiện tại: {product.get('description', 'Không có')}\n\n"
                f"Vui lòng nhập tên mới cho sản phẩm (hoặc gõ 'giữ nguyên' để không thay đổi):",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
    
    elif data == "create_product" and is_admin(user_id):
        # Bắt đầu quá trình tạo sản phẩm mới
        user_states[user_id] = {
            'state': 'waiting_for_product_name',
            'data': {}
        }
        
        bot.edit_message_text(
            "➕ *Tạo sản phẩm mới*\n\n"
            "Vui lòng nhập tên sản phẩm:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    elif data == "toggle_premium_visibility" and is_admin(user_id):
        # Lấy cài đặt hiện tại
        settings = db.get_visibility_settings()
        show_premium = settings.get('show_premium', True)
        
        # Đảo ngược trạng thái
        new_status = not show_premium
        db.update_visibility_setting('show_premium', new_status)
        
        status_text = "bật" if new_status else "tắt"
        
        # Thông báo cho admin
        bot.answer_callback_query(
            call.id,
            f"Đã {status_text} hiển thị tài khoản trả phí",
            show_alert=True
        )
        
        # Cập nhật menu admin
        bot.edit_message_text(
            "⚙️ *Bảng điều khiển quản trị*\n\n"
            f"Hiển thị tài khoản trả phí: {'Bật' if new_status else 'Tắt'}",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.admin_panel_keyboard()
        )
    
    # Thêm xử lý cho nút xóa sản phẩm
    elif data.startswith("delete_product_") and is_admin(user_id):
        # Xóa sản phẩm
        product_id = int(data.split("_")[2])
        product = db.get_product(product_id)
        
        if product:
            # Xác nhận xóa sản phẩm
            bot.edit_message_text(
                f"🗑️ *Xác nhận xóa sản phẩm*\n\n"
                f"ID: {product['id']}\n"
                f"Tên: {product['name']}\n"
                f"Giá: {product['price']:,} {config.CURRENCY}\n\n"
                f"Bạn có chắc chắn muốn xóa sản phẩm này?",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboards.confirm_delete_product_keyboard(product_id)
            )
    
    # Thêm xử lý cho nút xác nhận xóa sản phẩm
    elif data.startswith("confirm_delete_product_") and is_admin(user_id):
        # Xác nhận xóa sản phẩm
        product_id = int(data.split("_")[3])
        
        # Xóa sản phẩm
        if db.delete_product(product_id):
            bot.edit_message_text(
                "✅ Đã xóa sản phẩm thành công!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.back_button("back_to_product_list")
            )
        else:
            bot.edit_message_text(
                "❌ Không thể xóa sản phẩm. Vui lòng thử lại sau.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.back_button("back_to_product_list")
            )
    
    # Thêm xử lý cho nút hủy xóa sản phẩm
    elif data == "cancel_delete_product" and is_admin(user_id):
        # Hủy xóa sản phẩm
        bot.edit_message_text(
            "❌ Đã hủy xóa sản phẩm.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.back_button("back_to_product_list")
        )
    
    # Thêm xử lý cho nút tìm kiếm người dùng
    elif data.startswith("user_list_page_"):
        # Xử lý phân trang danh sách người dùng
        page = int(data.split("_")[3])
        user_states[user_id]['page'] = page
        display_user_list_page(bot, user_id, call.message.message_id)

    elif data == "user_list_search":
        # Bắt đầu tìm kiếm người dùng
        user_states[user_id]['state'] = 'searching_user'
        bot.edit_message_text(
            "🔍 *Tìm kiếm người dùng*\n\n"
            "Vui lòng nhập tên người dùng hoặc ID để tìm kiếm:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )

    elif data == "user_list_refresh":
        # Làm mới danh sách người dùng
        users = db.get_all_users()
        user_states[user_id] = {
            'state': 'viewing_user_list',
            'page': 0,
            'users': users,
            'search_query': ''
        }
        display_user_list_page(bot, user_id, call.message.message_id)
    
    elif data == "my_purchases":
        # Hiển thị danh sách tài khoản đã mua
        user = db.get_user(user_id)
        purchases = user.get('purchases', [])
        
        if not purchases:
            bot.edit_message_text(
                "🛒 Bạn chưa mua tài khoản nào.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.back_button("account_menu")
            )
            return
        
        # Lưu trạng thái để xử lý phân trang
        user_states[user_id] = {
            'state': 'viewing_purchases',
            'page': 0,
            'purchases': purchases
        }
        
        bot.edit_message_text(
            "🛒 *Tài khoản đã mua*\n\nChọn một tài khoản để xem chi tiết:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.purchase_history_keyboard(purchases)
        )
    
    elif data.startswith("view_purchase_"):
        # Xem chi tiết tài khoản đã mua
        purchase_idx = int(data.split("_")[2])
        
        # Lấy thông tin mua hàng từ trạng thái người dùng
        state = user_states.get(user_id, {})
        purchases = state.get('purchases', [])
        
        if not purchases or purchase_idx >= len(purchases):
            # Nếu không có thông tin trong trạng thái, lấy từ cơ sở dữ liệu
            user = db.get_user(user_id)
            purchases = user.get('purchases', [])
        
        if purchase_idx >= len(purchases):
            bot.answer_callback_query(call.id, "❌ Không tìm thấy thông tin tài khoản.", show_alert=True)
            return
        
        purchase = purchases[purchase_idx]
        product_name = purchase.get('product_name', 'Không tên')
        price = purchase.get('price', 0)
        account_info = purchase.get('account_data', 'Không có thông tin')
        
        # Định dạng thời gian mua
        timestamp = purchase.get('timestamp', '')
        if timestamp:
            try:
                import datetime
                dt = datetime.datetime.fromisoformat(timestamp)
                date_str = dt.strftime('%d/%m/%Y %H:%M:%S')
            except:
                date_str = 'Không rõ'
        else:
            date_str = 'Không rõ'
        
        bot.edit_message_text(
            f"🛒 *Chi tiết tài khoản đã mua*\n\n"
            f"Sản phẩm: {product_name}\n"
            f"Giá: {price:,} {config.CURRENCY}\n"
            f"Ngày mua: {date_str}\n\n"
            f"📝 *Thông tin tài khoản:*\n"
            f"`{account_info}`",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.back_button("back_to_purchases")
        )
    
    elif data == "back_to_purchases":
        # Quay lại danh sách tài khoản đã mua
        state = user_states.get(user_id, {})
        page = state.get('page', 0)
        purchases = state.get('purchases', [])
        
        if not purchases:
            # Nếu không có thông tin trong trạng thái, lấy từ cơ sở dữ liệu
            user = db.get_user(user_id)
            purchases = user.get('purchases', [])
        
        bot.edit_message_text(
            "🛒 *Tài khoản đã mua*\n\nChọn một tài khoản để xem chi tiết:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.purchase_history_keyboard(purchases, page)
        )
    
    elif data.startswith("purchase_page_"):
        # Xử lý phân trang danh sách tài khoản đã mua
        page = int(data.split("_")[2])
        
        state = user_states.get(user_id, {})
        purchases = state.get('purchases', [])
        
        if not purchases:
            # Nếu không có thông tin trong trạng thái, lấy từ cơ sở dữ liệu
            user = db.get_user(user_id)
            purchases = user.get('purchases', [])
        
        # Cập nhật trang hiện tại
        if user_id in user_states:
            user_states[user_id]['page'] = page
        else:
            user_states[user_id] = {
                'state': 'viewing_purchases',
                'page': page,
                'purchases': purchases
            }
        
        bot.edit_message_text(
            "🛒 *Tài khoản đã mua*\n\nChọn một tài khoản để xem chi tiết:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.purchase_history_keyboard(purchases, page)
        )
    
    # Đánh dấu callback đã được xử lý
    bot.answer_callback_query(call.id)

def add_admin_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /add_admin - Thêm admin mới"""
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    logger.info(f"Admin {username} (ID: {user_id}) started add_admin process")
    
    # Phân tích cú pháp lệnh
    args = message.text.split()
    
    if len(args) < 2:
        bot.send_message(
            user_id,
            "❌ Sử dụng sai cú pháp. Vui lòng sử dụng: /add_admin [user_id]\n"
            "Ví dụ: /add_admin 123456789"
        )
        return
    
    try:
        new_admin_id = int(args[1])
    except ValueError:
        bot.send_message(user_id, "❌ ID người dùng phải là một số.")
        return
    
    # Kiểm tra xem người dùng đã là admin chưa
    if is_admin(new_admin_id):
        bot.send_message(user_id, "❌ Người dùng này đã là admin.")
        return
    
    # Kiểm tra xem người dùng có tồn tại không
    new_admin = db.get_user(new_admin_id)
    if not new_admin:
        bot.send_message(user_id, "❌ Không tìm thấy người dùng với ID này.")
        return
    
    # Thêm người dùng vào danh sách admin
    admin_ids = config.ADMIN_IDS.copy()
    admin_ids.append(new_admin_id)
    
    # Cập nhật file config.py
    try:
        with open('config.py', 'r', encoding='utf-8') as file:
            config_content = file.read()
        
        # Tìm và thay thế dòng ADMIN_IDS
        import re
        new_admin_line = f"ADMIN_IDS = {str(admin_ids)}"
        config_content = re.sub(r'ADMIN_IDS = \[.*?\]', new_admin_line, config_content, flags=re.DOTALL)
        
        with open('config.py', 'w', encoding='utf-8') as file:
            file.write(config_content)
        
        # Cập nhật biến ADMIN_IDS trong config
        config.ADMIN_IDS = admin_ids
        
        bot.send_message(
            user_id,
            f"✅ Đã thêm người dùng ID: {new_admin_id} (@{new_admin.get('username', 'Không có')}) làm admin thành công!\n\n"
            f"⚠️ Lưu ý: Bạn cần khởi động lại bot để áp dụng thay đổi."
        )
        
        # Thông báo cho người dùng mới được thêm làm admin
        try:
            bot.send_message(
                new_admin_id,
                "🎉 Chúc mừng! Bạn đã được thêm làm quản trị viên của bot.\n"
                "Sử dụng /help để xem các lệnh quản trị viên."
            )
        except Exception as e:
            logger.error(f"Không thể gửi thông báo đến người dùng {new_admin_id}: {e}")
            
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật file config.py: {e}")
        bot.send_message(
            user_id,
            "❌ Đã xảy ra lỗi khi thêm admin. Vui lòng thử lại sau hoặc thêm thủ công vào file config.py."
        )

# Thêm hàm tiện ích để gửi thông báo cho tất cả admin
def notify_admins(bot: TeleBot, message: str, parse_mode: str = None) -> None:
    """Gửi thông báo đến tất cả admin"""
    for admin_id in config.ADMIN_IDS:
        try:
            bot.send_message(admin_id, message, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"Không thể gửi thông báo đến admin {admin_id}: {e}")

def debug_user_command(bot: TeleBot, message: Message) -> None:
    """Lệnh debug để kiểm tra dữ liệu người dùng"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "Sử dụng: /debug_user [user_id]")
        return
    
    try:
        target_user_id = int(args[1])
        user = db.get_user(target_user_id)
        if user:
            bot.send_message(user_id, f"User data: {json.dumps(user, indent=2)}")
        else:
            bot.send_message(user_id, f"User with ID {target_user_id} not found")
    except Exception as e:
        bot.send_message(user_id, f"Error: {str(e)}")

def check_ban_command(bot: TeleBot, message: Message) -> None:
    """Lệnh để kiểm tra trạng thái cấm của người dùng"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Bạn không có quyền thực hiện lệnh này.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "Sử dụng: /check_ban [user_id]")
        return
    
    try:
        target_user_id = int(args[1])
        user = db.get_user(target_user_id)
        if user:
            is_banned = is_user_banned(target_user_id)
            bot.send_message(user_id, f"User {target_user_id} banned status: {is_banned}")
        else:
            bot.send_message(user_id, f"User with ID {target_user_id} not found")
    except Exception as e:
        bot.send_message(user_id, f"Error: {str(e)}")

def is_user_banned(user_id: int) -> bool:
    """Kiểm tra xem người dùng có bị cấm không"""
    return db.is_user_banned(user_id)

def force_ban_command(bot: TeleBot, message: Message) -> None:
    """Lệnh cấm người dùng trực tiếp"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Bạn không có quyền thực hiện lệnh này.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "Sử dụng: /force_ban [user_id]")
        return
    
    try:
        target_user_id = int(args[1])
        
        # Kiểm tra người dùng tồn tại
        target_user = db.get_user(target_user_id)
        if not target_user:
            bot.send_message(user_id, f"❌ Không tìm thấy người dùng với ID {target_user_id}.")
            return
        
        # Sử dụng hàm ban_user từ database
        success = db.ban_user(target_user_id)
        
        if success:
            bot.send_message(user_id, f"✅ Đã cấm người dùng {target_user_id} thành công!")
            
            # Thông báo cho người dùng
            try:
                bot.send_message(
                    target_user_id,
                    "⛔ Tài khoản của bạn đã bị cấm. Vui lòng liên hệ quản trị viên."
                )
            except Exception:
                pass  # Không cần xử lý ngoại lệ ở đây
        else:
            bot.send_message(user_id, f"❌ Không thể cấm người dùng với ID {target_user_id}.")
    except Exception as e:
        bot.send_message(user_id, f"Error: {str(e)}")

def generate_qr_code(user_id: int, amount: int = 0) -> Optional[bytes]:
    """
    Tạo QR code chuyển khoản ngân hàng sử dụng API VietQR
    
    Args:
        user_id: ID người dùng (để tạo nội dung giao dịch)
        amount: Số tiền cần chuyển, mặc định là 0 để người dùng tự nhập
    
    Returns:
        bytes: Dữ liệu hình ảnh QR code hoặc None nếu có lỗi
    """
    try:
        # Tạo nội dung chuyển khoản với ID người dùng để dễ đối soát
        add_info = f"NAP TIEN USER {user_id}"
        
        # Chuẩn bị dữ liệu gửi đến API
        payload = {
            "accountNo": config.BANK_ACCOUNT_NO,
            "accountName": config.BANK_ACCOUNT_NAME,
            "acqId": config.BANK_ACQ_ID,
            "addInfo": add_info,
            "amount": str(amount) if amount > 0 else "",
            "template": "compact"
        }
        
        # Headers cho API
        headers = {
            "x-client-id": config.VIETQR_CLIENT_ID,
            "x-api-key": config.VIETQR_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Gửi request đến API
        response = requests.post(
            config.VIETQR_API_URL,
            json=payload,
            headers=headers
        )
        
        # Kiểm tra phản hồi
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "00" and data.get("data"):
                # Lấy dữ liệu base64 của QR code
                qr_data = data.get("data", {}).get("qrDataBase64", "")
                if qr_data:
                    # Chuyển base64 thành bytes
                    return base64.b64decode(qr_data)
        
        # Log lỗi nếu có
        logger.error(f"VietQR API Error: {response.status_code}, {response.text}")
        
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
    
    return None
