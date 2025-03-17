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
        InlineKeyboardButton("💰 Số dư", callback_data="balance")
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
    """Tạo bàn phím danh sách sản phẩm"""
    markup = InlineKeyboardMarkup()
    
    # Hiển thị 5 sản phẩm mỗi trang
    items_per_page = 5
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(products))
    
    for i in range(start_idx, end_idx):
        product = products[i]
        product_name = product.get('name', 'Không tên')
        product_id = product.get('id', 0)
        
        if admin:
            markup.row(InlineKeyboardButton(
                f"{product_name}", 
                callback_data=f"admin_product_{product_id}"
            ))
        else:
            markup.row(InlineKeyboardButton(
                f"{product_name}", 
                callback_data=f"view_product_{product_id}"
            ))
    
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
    """Tạo bàn phím danh sách người dùng"""
    markup = InlineKeyboardMarkup()
    
    # Hiển thị 5 người dùng mỗi trang
    items_per_page = 5
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(users))
    
    for i in range(start_idx, end_idx):
        user = users[i]
        user_name = user.get('username', 'Không tên')
        user_id = user.get('id', 0)
        banned = "🚫 " if user.get('banned', False) else ""
        
        markup.row(InlineKeyboardButton(
            f"{banned}{user_name}", 
            callback_data=f"admin_user_{user_id}"
        ))
    
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