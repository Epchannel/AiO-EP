from telebot import TeleBot
from telebot.types import Message, CallbackQuery
import config
from database import Database
import keyboards
import re
import datetime
from typing import Dict, List, Optional, Any
import logging
import time

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
    
    # Callback query handlers
    bot.register_callback_query_handler(lambda call: handle_callback_query(bot, call), func=lambda call: True)
    
    # State handlers
    bot.register_message_handler(lambda msg: handle_state(bot, msg), content_types=['text'], func=lambda msg: msg.from_user.id in user_states)

def start_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /start"""
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    logger.info(f"User {username} (ID: {user_id}) started the bot")
    
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
        db.add_user(user_data)
        user = user_data
    
    # Kiểm tra xem người dùng có bị cấm không
    if user and user.get('banned', False):
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
    
    if is_admin(user_id):
        help_text += (
            "\n\n*Lệnh quản trị viên:*\n"
            "/create_product [tên] [giá] - Tạo/sửa sản phẩm\n"
            "/product_list - Xem danh sách sản phẩm\n"
            "/upload_product [product_id] - Upload tài khoản cho sản phẩm\n"
            "/add_money [user_id] [số tiền] - Thêm tiền cho người dùng\n"
            "/user_list - Xem danh sách người dùng\n"
            "/ban_user [user_id] - Cấm người dùng\n"
            "/unban_user [user_id] - Bỏ cấm người dùng"
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
    
    bot.send_message(
        user_id,
        "👥 *Danh sách người dùng*\n\nChọn một người dùng để xem chi tiết:",
        parse_mode="Markdown",
        reply_markup=keyboards.user_list_keyboard(users)
    )

def ban_user_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /ban_user"""
    user_id = message.from_user.id
    
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
    
    # Cấm người dùng
    success = db.ban_user(target_user_id)
    if success:
        bot.send_message(
            user_id,
            f"✅ Đã cấm người dùng {target_user.get('username', target_user_id)}."
        )
        
        # Thông báo cho người dùng
        bot.send_message(
            target_user_id,
            "⛔ Tài khoản của bạn đã bị cấm. Vui lòng liên hệ quản trị viên."
        )
    else:
        bot.send_message(user_id, "❌ Không thể cấm người dùng này.")

def unban_user_command(bot: TeleBot, message: Message) -> None:
    """Xử lý lệnh /unban_user"""
    user_id = message.from_user.id
    
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
    
    # Bỏ cấm người dùng
    success = db.unban_user(target_user_id)
    if success:
        bot.send_message(
            user_id,
            f"✅ Đã bỏ cấm người dùng {target_user.get('username', target_user_id)}."
        )
        
        # Thông báo cho người dùng
        bot.send_message(
            target_user_id,
            "✅ Tài khoản của bạn đã được bỏ cấm. Bạn có thể sử dụng bot bình thường."
        )
    else:
        bot.send_message(user_id, "❌ Không thể bỏ cấm người dùng này.")

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
    
    state = user_states.get(user_id, {}).get('state')
    
    # Kiểm tra lệnh hủy
    if text == '/cancel':
        del user_states[user_id]
        bot.send_message(user_id, "❌ Đã hủy thao tác.")
        return
    
    # Xử lý các trạng thái
    if state == 'waiting_for_accounts':
        product_id = user_states[user_id]['product_id']
        
        # Xử lý danh sách tài khoản
        accounts = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not accounts:
            bot.send_message(user_id, "❌ Không tìm thấy tài khoản nào. Vui lòng thử lại.")
            return
        
        # Thêm tài khoản vào cơ sở dữ liệu
        count = db.add_accounts(product_id, accounts)
        
        # Xóa trạng thái
        del user_states[user_id]
        
        product = db.get_product(product_id)
        bot.send_message(
            user_id,
            f"✅ Đã thêm {count} tài khoản cho sản phẩm *{product['name']}*.",
            parse_mode="Markdown"
        )
    
    elif state == 'waiting_for_add_money' and is_admin(user_id):
        # Xử lý thêm tiền cho người dùng
        target_user_id = user_states[user_id]['target_user_id']
        
        try:
            amount = float(text)
            if amount <= 0:
                bot.send_message(user_id, "❌ Số tiền phải lớn hơn 0.")
                return
        except ValueError:
            bot.send_message(user_id, "❌ Số tiền không hợp lệ. Vui lòng nhập một số.")
            return
        
        # Xóa trạng thái
        del user_states[user_id]
        
        # Thêm tiền cho người dùng
        target_user = db.get_user(target_user_id)
        if target_user:
            new_balance = target_user.get('balance', 0) + amount
            db.update_user(target_user_id, {'balance': new_balance})
            
            bot.send_message(
                user_id,
                f"✅ Đã thêm {amount:,} {config.CURRENCY} cho người dùng thành công!\n\n"
                f"ID: {target_user['id']}\n"
                f"Username: @{target_user.get('username', 'Không có')}\n"
                f"Số dư mới: {new_balance:,} {config.CURRENCY}"
            )
            
            # Thông báo cho người dùng
            try:
                bot.send_message(
                    target_user_id,
                    f"💰 Tài khoản của bạn vừa được cộng {amount:,} {config.CURRENCY}.\n"
                    f"Số dư hiện tại: {new_balance:,} {config.CURRENCY}"
                )
            except Exception as e:
                logger.error(f"Không thể gửi thông báo đến người dùng {target_user_id}: {e}")
        else:
            bot.send_message(user_id, "❌ Không thể thêm tiền cho người dùng này.")
    
    elif state == 'waiting_for_product_name':
        # Lưu tên sản phẩm và chuyển sang trạng thái chờ giá
        user_states[user_id]['product_name'] = text
        user_states[user_id]['state'] = 'waiting_for_product_price'
        
        bot.send_message(
            user_id,
            f"📝 Tên sản phẩm: *{text}*\n\nVui lòng nhập giá sản phẩm (số):",
            parse_mode="Markdown"
        )
    
    elif state == 'waiting_for_product_price':
        try:
            price = float(text)
        except ValueError:
            bot.send_message(user_id, "❌ Giá phải là một số. Vui lòng thử lại.")
            return
        
        product_name = user_states[user_id]['product_name']
        
        # Tạo sản phẩm mới
        product_data = {
            'name': product_name,
            'price': price,
            'is_free': price <= 0,
            'description': f"Sản phẩm: {product_name}"
        }
        
        # Nếu đang chỉnh sửa sản phẩm
        if 'edit_product_id' in user_states[user_id]:
            product_data['id'] = user_states[user_id]['edit_product_id']
        
        product_id = db.create_product(product_data)
        
        # Xóa trạng thái
        del user_states[user_id]
        
        bot.send_message(
            user_id,
            f"✅ Đã {'cập nhật' if 'edit_product_id' in user_states.get(user_id, {}) else 'tạo'} sản phẩm thành công!\n\n"
            f"ID: {product_id}\n"
            f"Tên: {product_name}\n"
            f"Giá: {price:,} {config.CURRENCY}\n"
            f"Loại: {'Miễn phí' if price <= 0 else 'Trả phí'}"
        )
    
    elif state == 'waiting_for_user_id':
        try:
            target_user_id = int(text)
        except ValueError:
            bot.send_message(user_id, "❌ ID người dùng phải là một số. Vui lòng thử lại.")
            return
        
        # Kiểm tra người dùng tồn tại
        target_user = db.get_user(target_user_id)
        if not target_user:
            bot.send_message(user_id, f"❌ Không tìm thấy người dùng với ID {target_user_id}.")
            return
        
        # Lưu ID người dùng và chuyển sang trạng thái chờ số tiền
        user_states[user_id]['target_user_id'] = target_user_id
        user_states[user_id]['state'] = 'waiting_for_amount'
        
        bot.send_message(
            user_id,
            f"👤 Người dùng: {target_user.get('username', target_user_id)}\n\n"
            f"Vui lòng nhập số tiền muốn thêm (số):"
        )
    
    elif state == 'waiting_for_amount':
        try:
            amount = float(text)
        except ValueError:
            bot.send_message(user_id, "❌ Số tiền phải là một số. Vui lòng thử lại.")
            return
        
        if amount <= 0:
            bot.send_message(user_id, "❌ Số tiền phải lớn hơn 0. Vui lòng thử lại.")
            return
        
        target_user_id = user_states[user_id]['target_user_id']
        
        # Thêm tiền cho người dùng
        success = db.add_money(target_user_id, amount)
        
        # Xóa trạng thái
        del user_states[user_id]
        
        if success:
            target_user = db.get_user(target_user_id)
            new_balance = target_user.get('balance', 0)
            
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
    
    elif state == 'waiting_for_broadcast' and is_admin(user_id):
        # Xử lý gửi thông báo đến tất cả người dùng
        broadcast_message = text
        
        # Xóa trạng thái
        del user_states[user_id]
        
        # Lấy danh sách tất cả người dùng
        users = db.get_all_users()
        success_count = 0
        fail_count = 0
        
        # Gửi tin nhắn xác nhận trước
        confirm_msg = bot.send_message(
            user_id,
            f"🔄 Đang gửi thông báo đến {len(users)} người dùng...",
        )
        
        # Gửi thông báo đến từng người dùng
        for user in users:
            try:
                # Bỏ qua người dùng bị cấm
                if user.get('banned', False):
                    continue
                
                # Gửi thông báo
                bot.send_message(
                    user['id'],
                    f"📣 *THÔNG BÁO*\n\n{broadcast_message}",
                    parse_mode="Markdown"
                )
                success_count += 1
                
                # Tránh bị giới hạn tốc độ của Telegram
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Không thể gửi thông báo đến người dùng {user.get('id')}: {e}")
                fail_count += 1
        
        # Cập nhật tin nhắn xác nhận
        bot.edit_message_text(
            f"✅ Đã gửi thông báo thành công!\n\n"
            f"📊 Thống kê:\n"
            f"- Tổng số người dùng: {len(users)}\n"
            f"- Gửi thành công: {success_count}\n"
            f"- Gửi thất bại: {fail_count}",
            user_id,
            confirm_msg.message_id
        )

    elif state == 'waiting_for_user_id_to_add_money' and is_admin(user_id):
        # Xử lý nhập ID người dùng để thêm tiền
        try:
            target_user_id = int(text)
            target_user = db.get_user(target_user_id)
            
            if not target_user:
                bot.send_message(user_id, "❌ Không tìm thấy người dùng với ID này.")
                return
            
            # Cập nhật trạng thái
            user_states[user_id] = {
                'state': 'waiting_for_add_money',
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
            bot.send_message(user_id, "❌ ID người dùng không hợp lệ. Vui lòng nhập một số.")

    elif state == 'waiting_for_admin_id' and is_admin(user_id):
        # Xử lý thêm admin mới
        try:
            new_admin_id = int(text)
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
        
        # Xóa trạng thái
        del user_states[user_id]
        
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

def handle_callback_query(bot: TeleBot, call: CallbackQuery) -> None:
    """Xử lý các callback query từ bàn phím inline"""
    user_id = call.from_user.id
    username = call.from_user.username or f"user_{user_id}"
    data = call.data
    
    logger.info(f"User {username} (ID: {user_id}) pressed button: {data}")
    
    # Kiểm tra xem người dùng có bị cấm không
    user = db.get_user(user_id)
    if user and user.get('banned', False) and not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔ Tài khoản của bạn đã bị cấm. Vui lòng liên hệ quản trị viên.")
        return
    
    # Thêm các hàm tiện ích
    def get_statistics():
        """Lấy thống kê hệ thống"""
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
        """Xử lý mua hàng"""
        user = db.get_user(user_id)
        product = db.get_product(product_id)
        
        if not product:
            return {'success': False, 'message': 'Sản phẩm không tồn tại'}
        
        # Kiểm tra số lượng tài khoản còn lại
        available_accounts = db.count_available_accounts(product_id)
        if available_accounts <= 0:
            return {'success': False, 'message': 'Sản phẩm đã hết hàng'}
        
        # Kiểm tra số dư
        if product.get('price', 0) > 0:  # Nếu là sản phẩm trả phí
            if user.get('balance', 0) < product.get('price', 0):
                return {'success': False, 'message': 'Số dư không đủ'}
            
            # Trừ tiền
            new_balance = user.get('balance', 0) - product.get('price', 0)
            db.update_user(user_id, {'balance': new_balance})
        
        # Lấy tài khoản
        account = db.get_available_account(product_id)
        if not account:
            return {'success': False, 'message': 'Không thể lấy tài khoản'}
        
        # Cập nhật lịch sử mua hàng
        purchase = {
            'product_id': product_id,
            'product_name': product.get('name', ''),
            'price': product.get('price', 0),
            'account_data': account.get('data', ''),
            'purchased_at': datetime.datetime.now().isoformat()
        }
        
        purchases = user.get('purchases', [])
        purchases.append(purchase)
        db.update_user(user_id, {'purchases': purchases})
        
        return {
            'success': True,
            'product_name': product.get('name', ''),
            'account_info': account.get('data', '')
        }
    
    # Xử lý các callback data
    if data == "premium_accounts":
        # Hiển thị danh sách tài khoản trả phí
        products = [p for p in db.get_all_products() if not p.get('is_free', False)]
        
        if not products:
            bot.edit_message_text(
                "📦 Chưa có sản phẩm trả phí nào.",
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
            reply_markup=keyboards.product_list_keyboard(products)
        )
    
    elif data == "free_accounts":
        # Hiển thị danh sách tài khoản miễn phí
        products = [p for p in db.get_all_products() if p.get('is_free', False)]
        
        if not products:
            bot.edit_message_text(
                "📦 Chưa có sản phẩm miễn phí nào.",
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
            reply_markup=keyboards.product_list_keyboard(products)
        )
    
    elif data == "tutorial":
        # Hiển thị hướng dẫn sử dụng
        bot.edit_message_text(
            "📚 Hướng dẫn sử dụng:\n\n"
            "1. Chọn loại tài khoản (trả phí/miễn phí)\n"
            "2. Chọn sản phẩm bạn muốn mua\n"
            "3. Xác nhận thanh toán\n"
            "4. Nhận thông tin tài khoản",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.back_button()
        )
    
    elif data == "balance":
        # Hiển thị số dư tài khoản
        user = db.get_user(user_id)
        balance = user.get('balance', 0)
        
        bot.edit_message_text(
            f"💰 Số dư tài khoản của bạn: {balance} VNĐ\n\n"
            "Để nạp tiền, vui lòng liên hệ admin.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.back_button()
        )
    
    elif data == "admin_panel" and is_admin(user_id):
        # Hiển thị panel quản trị
        bot.edit_message_text(
            "⚙️ Panel quản trị viên",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.admin_panel()
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
    
    elif data == "user_list" and is_admin(user_id):
        # Hiển thị danh sách người dùng
        users = db.get_all_users()
        bot.edit_message_text(
            "📋 *Danh sách người dùng*\n\n"
            "Chọn một người dùng để xem chi tiết:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.user_list_keyboard(users)
        )
    
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
        user_id = int(data.split("_")[2])
        user = db.get_user(user_id)
        
        if user:
            status = "🚫 Đã bị cấm" if user.get('banned', False) else "✅ Đang hoạt động"
            bot.edit_message_text(
                f"👤 Thông tin người dùng:\n\n"
                f"ID: {user['id']}\n"
                f"Username: @{user.get('username', 'Không có')}\n"
                f"Tên: {user.get('first_name', '')} {user.get('last_name', '')}\n"
                f"Số dư: {user.get('balance', 0)} VNĐ\n"
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
        result = process_purchase(user_id, product_id)
        
        if result['success']:
            bot.edit_message_text(
                f"✅ Mua hàng thành công!\n\n"
                f"Sản phẩm: {result['product_name']}\n"
                f"Thông tin tài khoản:\n"
                f"```\n{result['account_info']}\n```\n\n"
                f"Cảm ơn bạn đã mua hàng!",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboards.back_button()
            )
        else:
            bot.edit_message_text(
                f"❌ Mua hàng thất bại: {result['message']}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.back_button()
            )
    
    # Xử lý các nút quay lại
    elif data == "back_to_main":
        bot.edit_message_text(
            "🏠 Menu chính",
            call.message.chat.id,
            call.message.message_id,
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
        bot.edit_message_text(
            "👥 Quản lý người dùng",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboards.user_management()
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
            bot.edit_message_text(
                "🔐 Danh sách tài khoản trả phí:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.product_list_keyboard(products)
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
                f"Vui lòng nhập số tiền muốn thêm:",
                call.message.chat.id,
                call.message.message_id
            )
    
    elif data.startswith("ban_user_") and is_admin(user_id):
        # Cấm người dùng
        target_user_id = int(data.split("_")[2])
        target_user = db.get_user(target_user_id)
        
        if target_user:
            # Không cho phép cấm admin
            if is_admin(target_user_id):
                bot.answer_callback_query(call.id, "⛔ Không thể cấm quản trị viên khác.")
                return
            
            # Cấm người dùng
            db.update_user(target_user_id, {'banned': True})
            
            bot.edit_message_text(
                f"✅ Đã cấm người dùng thành công!\n\n"
                f"ID: {target_user['id']}\n"
                f"Username: @{target_user.get('username', 'Không có')}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.back_button("back_to_user_list")
            )
    
    elif data.startswith("unban_user_") and is_admin(user_id):
        # Bỏ cấm người dùng
        target_user_id = int(data.split("_")[2])
        target_user = db.get_user(target_user_id)
        
        if target_user:
            # Bỏ cấm người dùng
            db.update_user(target_user_id, {'banned': False})
            
            bot.edit_message_text(
                f"✅ Đã bỏ cấm người dùng thành công!\n\n"
                f"ID: {target_user['id']}\n"
                f"Username: @{target_user.get('username', 'Không có')}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboards.back_button("back_to_user_list")
            )
    
    elif data.startswith("upload_accounts_") and is_admin(user_id):
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
                f"📤 Upload tài khoản cho sản phẩm:\n\n"
                f"ID: {product['id']}\n"
                f"Tên: {product['name']}\n\n"
                f"Vui lòng nhập danh sách tài khoản, mỗi tài khoản một dòng.\n"
                f"Định dạng: username:password hoặc email:password",
                call.message.chat.id,
                call.message.message_id
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
        # Yêu cầu admin nhập ID người dùng
        user_states[user_id] = {
            'state': 'waiting_for_user_id_to_add_money',
            'data': {}
        }
        
        bot.edit_message_text(
            "💰 *Thêm tiền cho người dùng*\n\n"
            "Vui lòng nhập ID người dùng:",
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
            
            user_info = (
                f"👤 *Thông tin người dùng*\n\n"
                f"ID: `{target_user['id']}`\n"
                f"Username: @{target_user.get('username', 'Không có')}\n"
                f"Số dư: {target_user.get('balance', 0):,} {config.CURRENCY}\n"
                f"Trạng thái: {'🚫 Bị cấm' if target_user.get('banned', False) else '✅ Hoạt động'}\n"
                f"Ngày tham gia: {target_user.get('created_at', 'Không rõ').split('T')[0]}\n"
                f"Tổng đơn hàng: {purchase_count}\n"
                f"Tổng chi tiêu: {total_spent:,} {config.CURRENCY}"
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