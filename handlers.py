from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InputMediaPhoto
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
import requests
import base64
from io import BytesIO
import telebot.apihelper
from modules.files import FileManager

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

db = Database()

# Lưu trạng thái của người dùng
user_states = {}

# Khởi tạo file_manager
file_manager = None

def is_admin(user_id: int) -> bool:
    """Kiểm tra xem người dùng có phải là admin không"""
    return user_id in config.ADMIN_IDS

def register_handlers(bot: TeleBot) -> None:
    """Đăng ký tất cả các handler cho bot"""
    global file_manager
    file_manager = FileManager(bot, db)
    
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
        f"👋 Chào mừng, {username}!\n\n"
        f"Đây là bot mua bán tài khoản. Sử dụng các nút bên dưới để điều hướng.\n\n"
        f"Số dư hiện tại: {user.get('balance', 0):,} {config.CURRENCY}"
    )
    
    bot.send_message(
        user_id,
        welcome_text,
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
    
    # Sắp xếp người dùng theo username (a-z)
    # Đảm bảo sắp xếp không phân biệt chữ hoa/thường và xử lý trường hợp username là None
    users = sorted(users, key=lambda x: str(x.get('username', '')).lower() if x.get('username') is not None else '')
    
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
    try:
        state = user_states.get(user_id, {})
        users = state.get('users', [])
        page = state.get('page', 0)
        search_query = state.get('search_query', '').lower()
        
        # Sắp xếp người dùng theo username (a-z)
        # Đảm bảo sắp xếp không phân biệt chữ hoa/thường và xử lý trường hợp username là None
        users = sorted(users, key=lambda x: str(x.get('username', '')).lower() if x.get('username') is not None else '')
        
        # Cập nhật users đã sắp xếp vào state
        if user_id in user_states:
            user_states[user_id]['users'] = users
        
        # Lọc người dùng theo từ khóa tìm kiếm nếu có
        if search_query:
            filtered_users = []
            for user in users:
                username = str(user.get('username', '')).lower()
                user_id_str = str(user.get('id', ''))
                if search_query in username or search_query in user_id_str:
                    filtered_users.append(user)
            users = filtered_users
        
        # Số người dùng mỗi trang - tăng lên 10
        per_page = 10
        total_pages = max(1, (len(users) + per_page - 1) // per_page)
        
        # Đảm bảo page không vượt quá total_pages
        page = min(page, total_pages - 1)
        if page < 0:
            page = 0
        
        if len(users) == 0:
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
                # Escape special characters in username to prevent Markdown parsing issues
                username = user.get('username', 'Không có')
                # Replace any Markdown special characters with escaped versions
                username = username.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')
                
                user_id_val = user.get('id', 'N/A')
                balance = user.get('balance', 0)
                banned = "🚫" if user.get('banned', False) else "✅"
                
                text += f"{i}. {banned} @{username} (ID: `{user_id_val}`)\n   💰 {balance:,} {config.CURRENCY}\n\n"
            
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
            except telebot.apihelper.ApiTelegramException as e:
                # Bỏ qua lỗi "message is not modified"
                if "message is not modified" not in str(e):
                    logger.error(f"Error updating user list message: {e}")
                    # Nếu lỗi liên quan đến Markdown, thử gửi lại không có parse_mode
                    if "can't parse entities" in str(e):
                        try:
                            bot.edit_message_text(
                                text.replace('*', '').replace('`', ''),  # Remove Markdown formatting
                                user_id,
                                message_id,
                                reply_markup=markup
                            )
                            return
                        except Exception as inner_e:
                            logger.error(f"Error sending plain text message: {inner_e}")
                    
                    # Nếu vẫn không thể, gửi tin nhắn mới
                    bot.send_message(
                        user_id,
                        text,
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
    except Exception as e:
        logger.error(f"Error in display_user_list_page: {e}")
        try:
            # Send a simple message without Markdown formatting
            bot.send_message(
                user_id,
                "❌ Đã xảy ra lỗi khi hiển thị danh sách người dùng. Vui lòng thử lại sau.",
                reply_markup=keyboards.back_button("admin_panel")
            )
        except:
            pass

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
    """Xử lý tin nhắn dựa trên trạng thái của người dùng"""
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    text = message.text
    
    logger.info(f"User {username} (ID: {user_id}) sent message in state {user_states.get(user_id, {}).get('state')}: {text}")
    
    if user_id not in user_states:
        return
    
    state = user_states[user_id]['state']
    
    # Kiểm tra lệnh hủy
    if text == '/cancel':
        del user_states[user_id]
        bot.send_message(user_id, "❌ Đã hủy thao tác.")
        return
    
    # Xử lý các trạng thái
    if state == 'waiting_for_product_name':
        # Lưu tên sản phẩm và chuyển sang trạng thái chờ giá
        user_states[user_id]['data']['name'] = text
        user_states[user_id]['state'] = 'waiting_for_product_price'
        
        bot.send_message(
            user_id,
            f"👍 Đã lưu tên sản phẩm: *{text}*\n\n"
            f"Vui lòng nhập giá cho sản phẩm (số):",
            parse_mode="Markdown"
        )
    
    elif state == 'waiting_for_product_price':
        # Xử lý giá sản phẩm
        try:
            price = float(text)
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
        product_data['description'] = text
        
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
        skipped_count = 0
        
        for user_item in users:
            try:
                target_id = user_item.get('id')
                # Bỏ qua người dùng bị cấm
                if user_item.get('banned', False):
                    skipped_count += 1
                    continue
                
                if target_id != user_id:  # Không gửi cho chính mình
                    # Thử gửi với Markdown
                    try:
                        bot.send_message(
                            target_id,
                            f"📣 *THÔNG BÁO TỪ QUẢN TRỊ VIÊN*\n\n{broadcast_message}",
                            parse_mode="Markdown"
                        )
                    except telebot.apihelper.ApiTelegramException as e:
                        # Nếu lỗi Markdown, thử gửi lại không có định dạng
                        if "can't parse entities" in str(e):
                            bot.send_message(
                                target_id,
                                f"📣 THÔNG BÁO TỪ QUẢN TRỊ VIÊN\n\n{broadcast_message}"
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
            f"- Số người bị bỏ qua (bị cấm): {skipped_count}\n"
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
    
    elif state == 'waiting_for_download_url':
        # Xử lý URL tải file
        # Xóa trạng thái người dùng
        del user_states[user_id]
        
        # Chuyển xử lý cho file_manager
        file_manager.process_download_url(message)
    
    # Thêm các trạng thái khác ở đây

def handle_callback_query(bot: TeleBot, call: CallbackQuery) -> None:
    """Xử lý callback query"""
    user_id = call.from_user.id
    username = call.from_user.username or f"user_{user_id}"
    data = call.data
    
    logger.info(f"User {username} (ID: {user_id}) pressed button: {data}")
    
    # Kiểm tra xem người dùng có bị cấm không
    user = db.get_user(user_id)
    if user and user.get('banned', False):
        bot.answer_callback_query(call.id, "⛔ Tài khoản của bạn đã bị cấm. Vui lòng liên hệ quản trị viên.", show_alert=True)
        return
    
    # Thêm các hàm tiện ích
    def get_statistics():
        """Lấy thống kê hệ thống"""
        # Import datetime trong phạm vi hàm này
        import datetime
        
        users = db.get_all_users()
        total_users = len(users)
        
        # Đếm người dùng mới trong ngày
        today = datetime.datetime.now().date()
        new_users_today = 0
        
        # Giả sử có trường 'created_at' trong dữ liệu người dùng
        for user in users:
            if 'created_at' in user:
                try:
                    created_date = datetime.datetime.fromisoformat(user['created_at']).date()
                    if created_date == today:
                        new_users_today += 1
                except (ValueError, TypeError):
                    pass
        
        # Đếm tổng đơn hàng và doanh thu
        total_orders = 0
        revenue = 0
        for user in users:
            purchases = user.get('purchases', [])
            total_orders += len(purchases)
            for purchase in purchases:
                revenue += purchase.get('price', 0)
        
        return {
            'total_users': total_users,
            'new_users_today': new_users_today,
            'total_orders': total_orders,
            'revenue': revenue
        }
    
    def process_purchase(user_id, product_id):
        """Xử lý quá trình mua hàng"""
        try:
            # Import datetime ở đầu hàm để đảm bảo nó có sẵn trong phạm vi của hàm
            import datetime
            
            user = db.get_user(user_id)
            if not user:
                # Tạo user mới nếu không tồn tại
                user = {
                    'id': user_id,
                    'balance': 0,
                    'purchases': [],
                    'banned': False
                }
                db.add_user(user)
            
            product = db.get_product(product_id)
            if not product:
                return {
                    'success': False,
                    'message': 'Sản phẩm không tồn tại.'
                }
            
            # Kiểm tra số lượng tài khoản còn lại
            available_accounts = db.count_available_accounts(product_id)
            if available_accounts <= 0:
                return {
                    'success': False,
                    'message': 'Sản phẩm đã hết hàng.'
                }
            
            # Kiểm tra nếu là sản phẩm miễn phí, người dùng chỉ được nhận 1 lần
            if product.get('is_free', False):
                user_purchases = user.get('purchases', [])
                for purchase in user_purchases:
                    if purchase.get('product_id') == product_id:
                        return {
                            'success': False,
                            'message': 'Bạn đã nhận sản phẩm miễn phí này rồi. Mỗi người chỉ được nhận 1 lần.'
                        }
            
            # Kiểm tra số dư
            user_balance = user.get('balance', 0)
            product_price = product.get('price', 0)
            
            if product_price > 0 and user_balance < product_price:
                return {
                    'success': False,
                    'message': f'Số dư không đủ. Bạn cần thêm {product_price - user_balance:,} {config.CURRENCY}.'
                }
            
            # Lấy một tài khoản
            account = db.get_available_account(product_id)
            if not account:
                return {
                    'success': False,
                    'message': 'Không thể lấy tài khoản. Vui lòng thử lại sau.'
                }
            
            # Trừ tiền
            if product_price > 0:
                new_balance = user_balance - product_price
                db.update_user(user_id, {'balance': new_balance})
            else:
                new_balance = user_balance
            
            # Lưu lịch sử mua hàng
            purchase_data = {
                'product_id': product_id,
                'product_name': product.get('name', 'Unknown'),
                'price': product_price,
                'account_data': account.get('data', ''),
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            user_purchases = user.get('purchases', [])
            user_purchases.append(purchase_data)
            db.update_user(user_id, {'purchases': user_purchases})
            
            # Trả về kết quả thành công
            return {
                'success': True,
                'product_name': product.get('name', 'Unknown'),
                'price': product_price,
                'new_balance': new_balance,
                'account_info': account.get('data', '')
            }
        except Exception as e:
            logger.error(f"Error in process_purchase: {e}")
            return {
                'success': False,
                'message': 'Đã xảy ra lỗi khi xử lý giao dịch. Vui lòng thử lại sau.'
            }

    # Xử lý các callback data
    if data == "premium_accounts":
        # Hiển thị danh sách tài khoản trả phí
        products = [p for p in db.get_all_products() if not p.get('is_free', False)]
        
        # Lọc sản phẩm có hàng
        products_with_stock = []
        for product in products:
            if db.count_available_accounts(product.get('id', 0)) > 0:
                products_with_stock.append(product)
        
        if not products_with_stock:
            bot.edit_message_text(
                "📦 Hiện tại không có sản phẩm trả phí nào có sẵn.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.back_button()
            )
            return
        
        bot.edit_message_text(
            "🔐 *Tài khoản trả phí*\n\nChọn một sản phẩm để xem chi tiết:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.product_list_keyboard(products_with_stock)
        )
    
    elif data == "free_accounts":
        # Hiển thị danh sách tài khoản miễn phí
        products = [p for p in db.get_all_products() if p.get('is_free', False)]
        
        # Lọc sản phẩm có hàng
        products_with_stock = []
        for product in products:
            if db.count_available_accounts(product.get('id', 0)) > 0:
                products_with_stock.append(product)
        
        if not products_with_stock:
            bot.edit_message_text(
                "📦 Hiện tại không có sản phẩm miễn phí nào có sẵn.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.back_button()
            )
            return
        
        bot.edit_message_text(
            "🆓 *Tài khoản miễn phí*\n\nChọn một sản phẩm để xem chi tiết:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.product_list_keyboard(products_with_stock)
        )
    
    elif data == "tutorial":
        # Hiển thị hướng dẫn sử dụng
        bot.edit_message_text(
            "📚 Hướng dẫn sử dụng:\n\n"
            "1. Chọn loại tài khoản (trả phí/miễn phí)\n"
            "2. Chọn sản phẩm bạn muốn mua\n"
            "3. Xác nhận thanh toán\n"
            "Để được hỗ trợ, vui lòng liên hệ admin: @ngochacoder",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.back_button()
        )
    
    elif data == "balance":
        # Hiển thị số dư tài khoản
        user = db.get_user(user_id)
        balance = user.get('balance', 0)
        
        bot.edit_message_text(
            f"💰 Số dư tài khoản của bạn: {balance:,} {config.CURRENCY}\n\n"
            "Để nạp tiền, vui lòng liên hệ admin @ngochacoder.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.back_button("my_account")  # Thay đổi ở đây
        )
    
    elif data == "admin_panel" and is_admin(user_id):
        # Lấy cài đặt hiển thị
        settings = db.get_visibility_settings()
        show_premium = settings.get('show_premium', True)
        
        # Hiển thị bảng điều khiển quản trị
        bot.edit_message_text(
            "⚙️ *Bảng điều khiển quản trị*\n\n"
            f"Hiển thị tài khoản trả phí: {'Bật' if show_premium else 'Tắt'}\n\n"
            "Chọn một tùy chọn bên dưới:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.admin_panel_keyboard()
        )
    
    elif data == "manage_products" and is_admin(user_id):
        # Hiển thị menu quản lý sản phẩm
        bot.edit_message_text(
            "📦 Quản lý sản phẩm",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.product_management()
        )
    
    elif data == "manage_users" and is_admin(user_id):
        # Hiển thị menu quản lý người dùng
        bot.edit_message_text(
            "👥 *Quản lý người dùng*\n\n"
            "Chọn một tùy chọn bên dưới:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.user_management()
        )
    
    elif data == "statistics" and is_admin(user_id):
        # Hiển thị thống kê
        stats = get_statistics()
        bot.edit_message_text(
            f"📊 Thống kê:\n\n"
            f"Tổng người dùng: {stats['total_users']}\n"
            f"Người dùng mới hôm nay: {stats['new_users_today']}\n"
            f"Tổng đơn hàng: {stats['total_orders']}\n"
            f"Doanh thu: {stats['revenue']} VNĐ",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.back_button("back_to_admin")
        )
    
    elif data == "product_list" and is_admin(user_id):
        # Hiển thị danh sách sản phẩm cho admin
        products = db.get_all_products()
        bot.edit_message_text(
            "📋 Danh sách sản phẩm:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.product_list_keyboard(products, admin=True)
        )
    
    elif data == "user_list":
        # Hiển thị danh sách người dùng
        try:
            users = db.get_all_users()
            
            if not users:
                bot.edit_message_text(
                    "👥 Chưa có người dùng nào.",
                    call.message.chat.id,
                    call.message.message_id
                )
                return
            
            # Sắp xếp người dùng theo username (a-z)
            # Đảm bảo sắp xếp không phân biệt chữ hoa/thường và xử lý trường hợp username là None
            users = sorted(users, key=lambda x: str(x.get('username', '')).lower() if x.get('username') is not None else '')
            
            # Lưu trạng thái để xử lý phân trang
            user_states[user_id] = {
                'state': 'viewing_user_list',
                'page': 0,
                'users': users,
                'search_query': ''
            }
            
            # Hiển thị trang đầu tiên
            display_user_list_page(bot, user_id, call.message.message_id)
        except Exception as e:
            logger.error(f"Error displaying user list: {e}")
            try:
                bot.answer_callback_query(call.id, "Đã xảy ra lỗi khi hiển thị danh sách người dùng.", show_alert=True)
            except:
                pass
    
    # Xử lý các callback có pattern
    elif data.startswith("view_product_"):
        # Xem chi tiết sản phẩm
        product_id = int(data.split("_")[2])
        product = db.get_product(product_id)
        
        if product:
            available_accounts = db.count_available_accounts(product_id)
            bot.edit_message_text(
                f"🏷️ {product['name']}\n\n"
                f"📝 Mô tả: {product['description']}\n"
                f"💰 Giá: {product['price']} VNĐ\n"
                f"📦 Còn lại: {available_accounts} tài khoản",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.product_detail_keyboard(product_id)
            )
    
    elif data.startswith("admin_product_") and is_admin(user_id):
        # Xem chi tiết sản phẩm (admin)
        product_id = int(data.split("_")[2])
        product = db.get_product(product_id)
        
        if product:
            available_accounts = db.count_available_accounts(product_id)
            bot.edit_message_text(
                f"🏷️ {product['name']}\n\n"
                f"📝 Mô tả: {product['description']}\n"
                f"💰 Giá: {product['price']} VNĐ\n"
                f"📦 Còn lại: {available_accounts} tài khoản\n"
                f"🆔 ID: {product['id']}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.product_detail_keyboard(product_id, is_admin=True)
            )
    
    elif data.startswith("admin_user_") and is_admin(user_id):
        # Xem chi tiết người dùng
        target_user_id = int(data.split("_")[2])
        target_user = db.get_user(target_user_id)
        
        if target_user:
            status = "🚫 Đã bị cấm" if target_user.get('banned', False) else "✅ Đang hoạt động"
            bot.edit_message_text(
                f"👤 Thông tin người dùng:\n\n"
                f"ID: {target_user['id']}\n"
                f"Username: @{target_user.get('username', 'Không có')}\n"
                f"Tên: {target_user.get('first_name', '')} {target_user.get('last_name', '')}\n"
                f"Số dư: {target_user.get('balance', 0)} VNĐ\n"
                f"Trạng thái: {status}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.back_button("back_to_user_list")
            )
    
    elif data.startswith("buy_product_"):
        # Mua sản phẩm
        product_id = int(data.split("_")[2])
        product = db.get_product(product_id)
        
        if product:
            bot.edit_message_text(
                f"🛒 Xác nhận mua:\n\n"
                f"Sản phẩm: {product['name']}\n"
                f"Giá: {product['price']} VNĐ\n\n"
                f"Bạn có chắc chắn muốn mua sản phẩm này?",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.confirm_purchase_keyboard(product_id)
            )
    
    elif data.startswith("confirm_purchase_"):
        # Xác nhận mua hàng
        product_id = int(data.split("_")[2])
        
        # Xử lý mua hàng
        result = process_purchase(user_id, product_id)
        
        if result and result.get('success'):
            # Gửi thông tin tài khoản cho người dùng
            bot.edit_message_text(
                f"✅ *Mua hàng thành công!*\n\n"
                f"Sản phẩm: {result['product_name']}\n"
                f"Giá: {result['price']:,} {config.CURRENCY}\n"
                f"Số dư còn lại: {result['new_balance']:,} {config.CURRENCY}\n\n"
                f"📝 *Thông tin tài khoản:*\n"
                f"`{result['account_info']}`\n\n"
                f"Cảm ơn bạn đã sử dụng dịch vụ!",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboards.back_button()
            )
            
            
            # Gửi thông báo cho admin về giao dịch thành công
            # Import datetime
            import datetime
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Escape any special characters in username and product name
            safe_username = username.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')
            safe_product_name = result['product_name'].replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')

            admin_notification = (
                f"💰 *Giao dịch mới thành công!*\n\n"
                f"Người dùng: @{safe_username} (ID: `{user_id}`)\n"
                f"Sản phẩm: {safe_product_name}\n"
                f"Giá: {result['price']:,} {config.CURRENCY}\n"
                f"Thời gian: {current_time}"
            )
            notify_admins(bot, admin_notification, parse_mode="Markdown")
        else:
            # Hiển thị thông báo lỗi
            error_message = result.get('message', 'Đã xảy ra lỗi không xác định') if result else 'Đã xảy ra lỗi không xác định'
            bot.answer_callback_query(call.id, f"❌ {error_message}", show_alert=True)
            
            # Quay lại menu chính
            bot.edit_message_text(
                f"🏠 *Menu chính*\n\nSố dư: {user.get('balance', 0):,} {config.CURRENCY}",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(is_admin(user_id))
            )
    
    # Xử lý các nút quay lại
    elif data == "back_to_main":
        bot.edit_message_text(
            f"🏠 *Menu chính*\n\nSố dư: {user.get('balance', 0):,} {config.CURRENCY}",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.main_menu(is_admin(user_id))
        )
    
    elif data == "back_to_admin":
        bot.edit_message_text(
            "⚙️ Panel quản trị viên",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.admin_panel()
        )
    
    elif data == "back_to_product_management":
        bot.edit_message_text(
            "📦 Quản lý sản phẩm",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.product_management()
        )
    
    elif data == "back_to_user_management":
        # Quay lại menu quản lý người dùng
        bot.edit_message_text(
            "👥 Quản lý người dùng",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.user_management()
        )
    
    elif data == "ban_user" and is_admin(user_id):
        # Lưu trạng thái chờ nhập ID người dùng để cấm
        user_states[user_id] = {
            'state': 'waiting_for_ban_user_id',
            'data': {}
        }
        
        bot.send_message(
                                user_id,
            "🚫 *Cấm người dùng*\n\n"
            "Vui lòng nhập ID người dùng bạn muốn cấm.\n"
            "Ví dụ: `123456789`\n\n"
            "Gửi /cancel để hủy.",
            parse_mode="Markdown"
        )
        
        # Sửa tin nhắn hiện tại để hiển thị trạng thái
        bot.edit_message_text(
            "👥 Quản lý người dùng\n\n"
            "📝 Đang chờ nhập ID người dùng để cấm...",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.back_button("back_to_user_management")
        )
    
    elif data == "unban_user" and is_admin(user_id):
        # Lưu trạng thái chờ nhập ID người dùng để bỏ cấm
        user_states[user_id] = {
            'state': 'waiting_for_unban_user_id',
            'data': {}
        }
        
        bot.send_message(
            user_id,
            "✅ *Bỏ cấm người dùng*\n\n"
            "Vui lòng nhập ID người dùng bạn muốn bỏ cấm.\n"
            "Ví dụ: `123456789`\n\n"
            "Gửi /cancel để hủy.",
            parse_mode="Markdown"
        )
        
        # Sửa tin nhắn hiện tại để hiển thị trạng thái
        bot.edit_message_text(
            "👥 Quản lý người dùng\n\n"
            "📝 Đang chờ nhập ID người dùng để bỏ cấm...",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.back_button("back_to_user_management")
        )
    
    elif data == "back_to_product_list":
        if is_admin(user_id):
            products = db.get_all_products()
            bot.edit_message_text(
                "📋 Danh sách sản phẩm:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.product_list_keyboard(products, admin=True)
            )
        else:
            products = [p for p in db.get_all_products() if not p.get('is_free', False)]
            
            # Lọc sản phẩm có hàng
            products_with_stock = []
            for product in products:
                if db.count_available_accounts(product.get('id', 0)) > 0:
                    products_with_stock.append(product)
            
            if not products_with_stock:
                bot.edit_message_text(
                    "📦 Hiện tại không có sản phẩm trả phí nào có sẵn.",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboards.back_button("back_to_main")
                )
                return
            
            bot.edit_message_text(
                "🔐 Danh sách tài khoản trả phí:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.product_list_keyboard(products_with_stock)
            )
    
    elif data == "cancel_purchase":
        bot.edit_message_text(
            "🏠 Đã hủy giao dịch. Quay lại menu chính",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.main_menu(is_admin(user_id))
        )
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
            
            # Lọc sản phẩm có hàng
            products_with_stock = []
            for product in products:
                if db.count_available_accounts(product.get('id', 0)) > 0:
                    products_with_stock.append(product)
            
            bot.edit_message_text(
                "🔐 Danh sách tài khoản trả phí:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.product_list_keyboard(products_with_stock, page=page)
            )
    
    elif data.startswith("user_page_"):
        # Xử lý phân trang danh sách người dùng
        try:
            page = int(data.split("_")[2])
            
            # Cập nhật trang hiện tại
            if user_id in user_states:
                user_states[user_id]['page'] = page
            
            # Hiển thị trang mới
            display_user_list_page(bot, user_id, call.message.message_id)
        except Exception as e:
            logger.error(f"Error navigating user list: {e}")
            try:
                bot.answer_callback_query(call.id, "Đã xảy ra lỗi khi điều hướng danh sách.", show_alert=True)
            except:
                pass
    
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
                f"Vui lòng nhập số tiền muốn thêm:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.deposit_amount_keyboard()
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
                reply_markup=keyboards.back_button()
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
            reply_markup=keyboards.purchase_history_keyboard(purchases, page, "my_account")  # Thêm tham số để quay lại menu tài khoản
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
    
    elif data == "my_account":
        # Hiển thị menu tài khoản
        user = db.get_user(user_id)
        balance = user.get('balance', 0)
        
        # Escape username để tránh lỗi Markdown
        safe_username = username.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')
        
        try:
            bot.edit_message_text(
                f"👤 *Thông tin tài khoản*\n\n"
                f"ID: `{user_id}`\n"
                f"Username: @{safe_username}\n"
                f"Số dư: {balance:,} {config.CURRENCY}\n\n"
                f"Chọn một tùy chọn bên dưới:",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboards.account_menu()
            )
        except telebot.apihelper.ApiTelegramException as e:
            # Nếu vẫn lỗi, thử gửi không có parse_mode
            if "can't parse entities" in str(e):
                bot.edit_message_text(
                    f"👤 Thông tin tài khoản\n\n"
                    f"ID: {user_id}\n"
                    f"Username: @{username}\n"
                    f"Số dư: {balance:,} {config.CURRENCY}\n\n"
                    f"Chọn một tùy chọn bên dưới:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboards.account_menu()
                )
    
    elif data == "deposit_money":
        # Hiển thị form nạp tiền
        bot.edit_message_text(
            "💰 *Nạp tiền vào tài khoản*\n\n"
            "Vui lòng chọn số tiền bạn muốn nạp:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.deposit_amount_keyboard()
        )

    elif data.startswith("deposit_amount_"):
        # Xử lý số tiền nạp
        try:
            amount = int(data.split("_")[2])
            
            # Tạo mô tả giao dịch
            description = f"Naptien {username} {user_id}"
            
            # Tạo mã QR
            qr_image = generate_payment_qr(user_id, amount, description)
            
            if qr_image:
                # Gửi ảnh QR code
                bot.delete_message(call.message.chat.id, call.message.message_id)
                
                # Tạo bàn phím với nút liên hệ admin và quay lại
                contact_markup = keyboards.payment_contact_keyboard()
                
                bot.send_photo(
                    call.message.chat.id,
                    qr_image,
                    caption=f"📱 *Quét mã QR để nạp tiền*\n\n"
                    f"Số tiền: {amount:,} {config.CURRENCY}\n"
                    f"Nội dung chuyển khoản: `{description}`\n\n"
                    f"⚠️ *Lưu ý:*\n"
                    f"- Vui lòng không thay đổi nội dung chuyển khoản\n"
                    f"- Tiền sẽ được cộng vào tài khoản sau khi admin xác nhận\n"
                    f"- Sử dụng nút bên dưới để liên hệ admin nếu cần hỗ trợ",
                    parse_mode="Markdown",
                    reply_markup=contact_markup
                )
            else:
                bot.answer_callback_query(call.id, "❌ Không thể tạo mã QR. Vui lòng thử lại sau.", show_alert=True)
        except Exception as e:
            logger.error(f"Error processing deposit: {e}")
            bot.answer_callback_query(call.id, "❌ Đã xảy ra lỗi. Vui lòng thử lại sau.", show_alert=True)
    
    # Đánh dấu callback đã được xử lý
    bot.answer_callback_query(call.id)
    
    # Add the file download handlers here, inside the function
    if data == "download_files":
        # Sử dụng file_manager để hiển thị menu tải file
        file_manager.show_download_menu(call.message.chat.id, call.message.message_id)

    elif data == "file_list":
        # Hiển thị danh sách file
        file_manager.show_file_list(call.message.chat.id, call.message.message_id)

    elif data == "search_file":
        # Hiển thị form tìm kiếm file
        file_manager.search_file(call.message.chat.id, call.message.message_id)

    elif data == "popular_files":
        # Hiển thị danh sách file phổ biến
        file_manager.show_popular_files(call.message.chat.id, call.message.message_id)

    elif data == "newest_files":
        # Hiển thị danh sách file mới nhất
        file_manager.show_newest_files(call.message.chat.id, call.message.message_id)

    elif data == "download_from_url":
        # Hiển thị form nhập URL để tải file
        file_manager.download_from_url(call.message.chat.id, call.message.message_id)

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
            # Escape any problematic characters in the message if using Markdown
            if parse_mode == "Markdown":
                # Escape characters that could break Markdown formatting
                message = message.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')
                
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

def generate_payment_qr(user_id: int, amount: int = 0, description: str = "") -> Optional[BytesIO]:
    """Tạo mã QR thanh toán sử dụng VietQR API"""
    try:
        # Tạo mô tả giao dịch
        if not description:
            description = f"Nap tien ID {user_id}"
        
        # Chuẩn bị dữ liệu cho API
        url = config.VIETQR_API_URL
        payload = {
            "accountNo": config.BANK_ACCOUNT_NO,
            "accountName": config.BANK_ACCOUNT_NAME,
            "acqId": config.BANK_ACQ_ID,
            "addInfo": description,
            "amount": str(amount),
            "template": "compact"
        }
        headers = {
            "x-client-id": config.VIETQR_CLIENT_ID,
            "x-api-key": config.VIETQR_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Gửi yêu cầu đến API
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # Kiểm tra phản hồi
        if response.status_code == 200:
            data = response.json()
            qr_data_uri = data.get("data", {}).get("qrDataURL", "")
            
            if qr_data_uri.startswith("data:image"):
                # Chuyển đổi base64 thành dữ liệu hình ảnh
                image_data = base64.b64decode(qr_data_uri.split(",", 1)[1])
                image_buffer = BytesIO(image_data)
                image_buffer.name = "payment_qr.png"
                return image_buffer
        
        logger.error(f"Error generating QR code: {response.text}")
        return None
    except Exception as e:
        logger.error(f"Error in generate_payment_qr: {e}")
        return None
