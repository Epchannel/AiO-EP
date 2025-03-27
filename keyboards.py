from typing import List, Dict, Any
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Database

def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Tạo bàn phím menu chính"""
    db = Database()
    
    # Lấy cài đặt hiển thị
    settings = db.get_visibility_settings()
    show_premium = settings.get('show_premium', True)
    
    markup = InlineKeyboardMarkup()
    
    # Chỉ hiển thị nút "Tài khoản trả phí" nếu cài đặt cho phép
    if show_premium:
        markup.row(
            InlineKeyboardButton("🔐 Tài khoản trả phí", callback_data="premium_accounts"),
            InlineKeyboardButton("🆓 Tài khoản miễn phí", callback_data="free_accounts")
        )
    else:
        # Nếu không hiển thị tài khoản trả phí, chỉ hiển thị tài khoản miễn phí
        markup.row(
            InlineKeyboardButton("🆓 Tài khoản miễn phí", callback_data="free_accounts")
        )
    
    markup.row(
        InlineKeyboardButton("📚 Hướng dẫn", callback_data="tutorial"),
        InlineKeyboardButton("👤 Tài khoản", callback_data="my_account")
    )
    
    if is_admin:
        markup.row(
            InlineKeyboardButton("⚙️ Quản trị viên", callback_data="admin_panel")
        )
    
    return markup

def admin_panel() -> InlineKeyboardMarkup:
    """Tạo bàn phím panel quản trị"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📦 Quản lý sản phẩm", callback_data="manage_products"),
        InlineKeyboardButton("👥 Quản lý người dùng", callback_data="manage_users")
    )
    markup.row(
        InlineKeyboardButton("📊 Thống kê", callback_data="statistics"),
        InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_main")
    )
    return markup

def product_management() -> InlineKeyboardMarkup:
    """Tạo bàn phím quản lý sản phẩm"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("➕ Tạo sản phẩm", callback_data="create_product"),
        InlineKeyboardButton("📋 Danh sách sản phẩm", callback_data="product_list")
    )
    markup.row(
        InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_admin")
    )
    return markup

def user_management() -> InlineKeyboardMarkup:
    """Tạo bàn phím quản lý người dùng"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📋 Danh sách người dùng", callback_data="user_list"),
        InlineKeyboardButton("💰 Thêm tiền", callback_data="add_money")
    )
    markup.row(
        InlineKeyboardButton("🚫 Cấm người dùng", callback_data="ban_user"),
        InlineKeyboardButton("✅ Bỏ cấm người dùng", callback_data="unban_user")
    )
    markup.row(
        InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_admin")
    )
    return markup

def product_list_keyboard(products: List[Dict[str, Any]], page: int = 0, admin: bool = False) -> InlineKeyboardMarkup:
    """Tạo bàn phím danh sách sản phẩm với hiển thị 2 cột"""
    markup = InlineKeyboardMarkup()
    
    # Hiển thị 10 sản phẩm mỗi trang (thay vì 5)
    items_per_page = 10
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(products))
    
    # Lấy danh sách sản phẩm cho trang hiện tại
    current_products = products[start_idx:end_idx]
    
    # Hiển thị sản phẩm theo 2 cột
    for i in range(0, len(current_products), 2):
        row_buttons = []
        
        # Sản phẩm đầu tiên trong hàng
        product = current_products[i]
        product_id = product.get('id', 0)
        product_name = product.get('name', 'Không tên')
        
        # Lấy số lượng tài khoản còn lại
        db = Database()
        available_count = db.count_available_accounts(product_id)
        
        # Thêm số lượng vào tên sản phẩm
        display_name = f"{product_name} ({available_count})"
        
        # Tạo nút cho sản phẩm đầu tiên
        callback_data = f"admin_product_{product_id}" if admin else f"view_product_{product_id}"
        row_buttons.append(InlineKeyboardButton(display_name, callback_data=callback_data))
        
        # Nếu còn sản phẩm thứ hai trong hàng
        if i + 1 < len(current_products):
            product = current_products[i + 1]
            product_id = product.get('id', 0)
            product_name = product.get('name', 'Không tên')
            
            # Lấy số lượng tài khoản còn lại
            available_count = db.count_available_accounts(product_id)
            
            # Thêm số lượng vào tên sản phẩm
            display_name = f"{product_name} ({available_count})"
            
            # Tạo nút cho sản phẩm thứ hai
            callback_data = f"admin_product_{product_id}" if admin else f"view_product_{product_id}"
            row_buttons.append(InlineKeyboardButton(display_name, callback_data=callback_data))
        
        # Thêm hàng vào bàn phím
        markup.row(*row_buttons)
    
    # Nút điều hướng trang
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Trước", callback_data=f"product_page_{page-1}"))
    
    if end_idx < len(products):
        nav_buttons.append(InlineKeyboardButton("➡️ Sau", callback_data=f"product_page_{page+1}"))
    
    if nav_buttons:
        markup.row(*nav_buttons)
    
    # Nút quay lại
    if admin:
        markup.row(InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_product_management"))
    else:
        markup.row(InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_main"))
    
    return markup

def user_list_keyboard(users: List[Dict[str, Any]], page: int = 0) -> InlineKeyboardMarkup:
    """Tạo bàn phím danh sách người dùng với hiển thị 2 cột"""
    markup = InlineKeyboardMarkup()
    
    # Hiển thị 10 người dùng mỗi trang (thay vì 5)
    items_per_page = 10
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(users))
    
    # Lấy danh sách người dùng cho trang hiện tại
    current_users = users[start_idx:end_idx]
    
    # Hiển thị người dùng theo 2 cột
    for i in range(0, len(current_users), 2):
        row_buttons = []
        
        # Người dùng đầu tiên trong hàng
        user = current_users[i]
        user_name = user.get('username', 'Không tên')
        user_id = user.get('id', 0)
        banned = "🚫 " if user.get('banned', False) else ""
        
        # Tạo nút cho người dùng đầu tiên
        row_buttons.append(InlineKeyboardButton(
            f"{banned}{user_name}", 
            callback_data=f"admin_user_{user_id}"
        ))
        
        # Nếu còn người dùng thứ hai trong hàng
        if i + 1 < len(current_users):
            user = current_users[i + 1]
            user_name = user.get('username', 'Không tên')
            user_id = user.get('id', 0)
            banned = "🚫 " if user.get('banned', False) else ""
            
            # Tạo nút cho người dùng thứ hai
            row_buttons.append(InlineKeyboardButton(
                f"{banned}{user_name}", 
                callback_data=f"admin_user_{user_id}"
            ))
        
        # Thêm hàng vào bàn phím
        markup.row(*row_buttons)
    
    # Nút điều hướng trang
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Trước", callback_data=f"user_page_{page-1}"))
    
    if end_idx < len(users):
        nav_buttons.append(InlineKeyboardButton("➡️ Sau", callback_data=f"user_page_{page+1}"))
    
    if nav_buttons:
        markup.row(*nav_buttons)
    
    # Nút quay lại
    markup.row(InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_user_management"))
    
    return markup

def product_detail_keyboard(product_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Tạo bàn phím chi tiết sản phẩm"""
    markup = InlineKeyboardMarkup()
    
    if is_admin:
        markup.row(
            InlineKeyboardButton("✏️ Chỉnh sửa", callback_data=f"edit_product_{product_id}"),
            InlineKeyboardButton("🗑️ Xóa", callback_data=f"delete_product_{product_id}")
        )
        markup.row(
            InlineKeyboardButton("📤 Upload tài khoản", callback_data=f"upload_product_{product_id}")
        )
    else:
        markup.row(
            InlineKeyboardButton("🛒 Mua ngay", callback_data=f"buy_product_{product_id}")
        )
    
    # Nút quay lại
    if is_admin:
        markup.row(InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_product_list"))
    else:
        markup.row(InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_product_list"))
    
    return markup

def confirm_purchase_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Tạo bàn phím xác nhận mua hàng"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Xác nhận", callback_data=f"confirm_purchase_{product_id}"),
        InlineKeyboardButton("❌ Hủy", callback_data=f"cancel_purchase")
    )
    return markup

def back_button(callback_data: str = "back_to_main") -> InlineKeyboardMarkup:
    """Tạo nút quay lại"""
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔙 Quay lại", callback_data=callback_data))
    return markup

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Tạo bàn phím panel quản trị"""
    from database import Database
    db = Database()
    
    # Lấy cài đặt hiển thị
    settings = db.get_visibility_settings()
    show_premium = settings.get('show_premium', True)
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("👥 Quản lý người dùng", callback_data="manage_users"),
        InlineKeyboardButton("🏷️ Quản lý sản phẩm", callback_data="manage_products")
    )
    markup.row(
        InlineKeyboardButton("📊 Thống kê", callback_data="statistics"),
        InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_main")
    )
    
    # Thêm nút bật/tắt hiển thị tài khoản trả phí
    status_text = "✅" if show_premium else "❌"
    markup.row(
        InlineKeyboardButton(f"{status_text} Hiển thị tài khoản trả phí", callback_data="toggle_premium_visibility")
    )
    
    return markup

def confirm_delete_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Tạo bàn phím xác nhận xóa sản phẩm"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Xác nhận", callback_data=f"confirm_delete_product_{product_id}"),
        InlineKeyboardButton("❌ Hủy", callback_data="cancel_delete_product")
    )
    return markup

def user_list_navigation_keyboard(current_page: int, total_pages: int, search_query: str = '') -> InlineKeyboardMarkup:
    """Tạo bàn phím điều hướng cho danh sách người dùng"""
    markup = InlineKeyboardMarkup(row_width=5)
    buttons = []
    
    # Nút tìm kiếm
    search_button = InlineKeyboardButton("🔍 Tìm kiếm", callback_data="user_list_search")
    
    # Nút làm mới
    refresh_button = InlineKeyboardButton("🔄 Làm mới", callback_data="user_list_refresh")
    
    # Nút điều hướng trang
    if total_pages > 1:
        # Nút trang đầu
        if current_page > 0:
            buttons.append(InlineKeyboardButton("⏮️", callback_data="user_list_page_0"))
        
        # Nút trang trước
        if current_page > 0:
            buttons.append(InlineKeyboardButton("◀️", callback_data=f"user_list_page_{current_page-1}"))
        
        # Nút trang hiện tại
        buttons.append(InlineKeyboardButton(f"{current_page+1}/{total_pages}", callback_data="noop"))
        
        # Nút trang sau
        if current_page < total_pages - 1:
            buttons.append(InlineKeyboardButton("▶️", callback_data=f"user_list_page_{current_page+1}"))
        
        # Nút trang cuối
        if current_page < total_pages - 1:
            buttons.append(InlineKeyboardButton("⏭️", callback_data=f"user_list_page_{total_pages-1}"))
    
    # Thêm các nút vào bàn phím
    if buttons:
        markup.add(*buttons)
    
    # Thêm nút tìm kiếm và làm mới
    markup.add(search_button, refresh_button)
    
    # Hiển thị trạng thái tìm kiếm nếu có
    if search_query:
        markup.add(InlineKeyboardButton(f"🔍 Đang tìm: '{search_query}'", callback_data="noop"))
    
    # Nút quay lại
    markup.add(InlineKeyboardButton("🔙 Quay lại", callback_data="admin_panel"))
    
    return markup

def purchase_history_keyboard(purchases: List[Dict[str, Any]], page: int = 0, back_to: str = "back_to_main") -> InlineKeyboardMarkup:
    """Tạo bàn phím danh sách tài khoản đã mua"""
    markup = InlineKeyboardMarkup()
    
    # Hiển thị 5 tài khoản mỗi trang
    items_per_page = 5
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(purchases))
    
    for i in range(start_idx, end_idx):
        purchase = purchases[i]
        product_name = purchase.get('product_name', 'Không tên')
        purchase_id = i  # Sử dụng index làm ID
        
        # Hiển thị tên sản phẩm và thời gian mua
        timestamp = purchase.get('timestamp', '')
        if timestamp:
            try:
                import datetime
                dt = datetime.datetime.fromisoformat(timestamp)
                date_str = dt.strftime('%d/%m/%Y')
            except:
                date_str = ''
        else:
            date_str = ''
        
        button_text = f"{product_name}"
        if date_str:
            button_text += f" ({date_str})"
        
        markup.row(InlineKeyboardButton(
            button_text, 
            callback_data=f"view_purchase_{purchase_id}"
        ))
    
    # Nút điều hướng trang
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Trước", callback_data=f"purchase_page_{page-1}"))
    
    if end_idx < len(purchases):
        nav_buttons.append(InlineKeyboardButton("➡️ Sau", callback_data=f"purchase_page_{page+1}"))
    
    if nav_buttons:
        markup.row(*nav_buttons)
    
    # Nút quay lại
    markup.row(InlineKeyboardButton("🔙 Quay lại", callback_data=back_to))
    
    return markup

def account_menu() -> InlineKeyboardMarkup:
    """Tạo bàn phím menu tài khoản"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💰 Nạp tiền", callback_data="deposit_money"),
        InlineKeyboardButton("🛒 Tài khoản đã mua", callback_data="my_purchases")
    )
    markup.row(
        InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_main")
    )
    return markup

def deposit_amount_keyboard() -> InlineKeyboardMarkup:
    """Tạo bàn phím chọn số tiền nạp"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("50,000 VND", callback_data="deposit_amount_50000"),
        InlineKeyboardButton("100,000 VND", callback_data="deposit_amount_100000")
    )
    markup.row(
        InlineKeyboardButton("200,000 VND", callback_data="deposit_amount_200000"),
        InlineKeyboardButton("500,000 VND", callback_data="deposit_amount_500000")
    )
    markup.row(
        InlineKeyboardButton("1,000,000 VND", callback_data="deposit_amount_1000000")
    )
    markup.row(
        InlineKeyboardButton("🔙 Quay lại", callback_data="my_account")
    )
    return markup

def payment_contact_keyboard() -> InlineKeyboardMarkup:
    """Tạo bàn phím liên hệ admin và quay lại cho trang thanh toán"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("👨‍💼 Liên hệ Admin", url="https://t.me/ngochacoder")
    )
    return markup 