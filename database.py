import json
import os
from typing import Dict, List, Any, Optional
import config

class Database:
    def __init__(self):
        # Đảm bảo thư mục data tồn tại
        os.makedirs("data", exist_ok=True)
        
        # Khởi tạo các file nếu chưa tồn tại
        self._init_file(config.USERS_FILE, [])
        self._init_file(config.PRODUCTS_FILE, [])
        self._init_file(config.ACCOUNTS_FILE, [])
    
    def _init_file(self, file_path: str, default_data: Any) -> None:
        """Khởi tạo file nếu chưa tồn tại"""
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=4)
    
    def _read_data(self, file_path: str) -> Any:
        """Đọc dữ liệu từ file JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Nếu file không tồn tại hoặc không hợp lệ, tạo mới
            default_data = [] if file_path != config.USERS_FILE else {}
            self._write_data(file_path, default_data)
            return default_data
    
    def _write_data(self, file_path: str, data: Any) -> None:
        """Ghi dữ liệu vào file JSON"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    # === User methods ===
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Lấy thông tin người dùng theo ID"""
        users = self._read_data(config.USERS_FILE)
        for user in users:
            if user.get('id') == user_id:
                return user
        return None
    
    def add_user(self, user_data: Dict) -> None:
        """Thêm người dùng mới"""
        users = self._read_data(config.USERS_FILE)
        # Kiểm tra xem người dùng đã tồn tại chưa
        for i, user in enumerate(users):
            if user.get('id') == user_data['id']:
                # Cập nhật thông tin người dùng
                users[i] = user_data
                self._write_data(config.USERS_FILE, users)
                return
        # Thêm người dùng mới
        users.append(user_data)
        self._write_data(config.USERS_FILE, users)
    
    def update_user(self, user_id: int, update_data: Dict) -> bool:
        """Cập nhật thông tin người dùng"""
        users = self._read_data(config.USERS_FILE)
        for i, user in enumerate(users):
            if user.get('id') == user_id:
                users[i].update(update_data)
                self._write_data(config.USERS_FILE, users)
                return True
        return False
    
    def get_all_users(self) -> List[Dict]:
        """Lấy danh sách tất cả người dùng"""
        return self._read_data(config.USERS_FILE)
    
    def ban_user(self, user_id: int) -> bool:
        """Cấm người dùng"""
        return self.update_user(user_id, {'banned': True})
    
    def unban_user(self, user_id: int) -> bool:
        """Bỏ cấm người dùng"""
        return self.update_user(user_id, {'banned': False})
    
    def add_money(self, user_id: int, amount: float) -> bool:
        """Thêm tiền cho người dùng"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        current_balance = user.get('balance', 0)
        return self.update_user(user_id, {'balance': current_balance + amount})
    
    # === Product methods ===
    def get_product(self, product_id: int) -> Optional[Dict]:
        """Lấy thông tin sản phẩm theo ID"""
        products = self._read_data(config.PRODUCTS_FILE)
        for product in products:
            if product.get('id') == product_id:
                return product
        return None
    
    def get_all_products(self) -> List[Dict]:
        """Lấy danh sách tất cả sản phẩm"""
        return self._read_data(config.PRODUCTS_FILE)
    
    def create_product(self, product_data: Dict) -> int:
        """Tạo sản phẩm mới hoặc cập nhật sản phẩm hiện có"""
        products = self._read_data(config.PRODUCTS_FILE)
        
        # Đảm bảo các trường cần thiết
        if 'name' not in product_data or 'price' not in product_data:
            raise ValueError("Sản phẩm phải có tên và giá")
        
        # Thêm trường is_free dựa trên giá
        product_data['is_free'] = product_data['price'] <= 0
        
        # Nếu không có mô tả, thêm mô tả mặc định
        if 'description' not in product_data:
            product_data['description'] = f"Sản phẩm: {product_data['name']}"
        
        # Nếu có ID và sản phẩm tồn tại, cập nhật
        if 'id' in product_data:
            for i, product in enumerate(products):
                if product.get('id') == product_data['id']:
                    # Giữ lại các trường khác nếu không được cung cấp
                    for key in product:
                        if key not in product_data:
                            product_data[key] = product[key]
                    
                    products[i] = product_data
                    self._write_data(config.PRODUCTS_FILE, products)
                    return product_data['id']
        
        # Tạo ID mới nếu không có
        if 'id' not in product_data:
            product_data['id'] = 1
            if products:
                product_data['id'] = max(p.get('id', 0) for p in products) + 1
        
        # Thêm sản phẩm mới
        products.append(product_data)
        self._write_data(config.PRODUCTS_FILE, products)
        return product_data['id']
    
    def delete_product(self, product_id: int) -> bool:
        """Xóa sản phẩm"""
        products = self._read_data(config.PRODUCTS_FILE)
        for i, product in enumerate(products):
            if product.get('id') == product_id:
                products.pop(i)
                self._write_data(config.PRODUCTS_FILE, products)
                return True
        return False
    
    # === Account methods ===
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Lấy tất cả tài khoản"""
        return self._read_data(config.ACCOUNTS_FILE)
    
    def save_accounts(self, accounts: List[Dict[str, Any]]) -> None:
        """Lưu danh sách tài khoản"""
        self._write_data(config.ACCOUNTS_FILE, accounts)
    
    def add_accounts(self, product_id: int, accounts: List[str]) -> int:
        """Thêm tài khoản cho sản phẩm"""
        all_accounts = self._read_data(config.ACCOUNTS_FILE)
        
        # Tạo danh sách tài khoản mới
        new_accounts = []
        for account in accounts:
            new_accounts.append({
                'product_id': product_id,
                'data': account,
                'sold': False
            })
        
        all_accounts.extend(new_accounts)
        self._write_data(config.ACCOUNTS_FILE, all_accounts)
        return len(new_accounts)
    
    def get_available_account(self, product_id: int) -> Optional[Dict]:
        """Lấy một tài khoản chưa bán của sản phẩm"""
        accounts = self._read_data(config.ACCOUNTS_FILE)
        for i, account in enumerate(accounts):
            if account.get('product_id') == product_id and not account.get('sold', False):
                # Đánh dấu tài khoản đã bán
                accounts[i]['sold'] = True
                self._write_data(config.ACCOUNTS_FILE, accounts)
                return account
        return None
    
    def count_available_accounts(self, product_id: int) -> int:
        """Đếm số lượng tài khoản còn lại của sản phẩm"""
        accounts = self._read_data(config.ACCOUNTS_FILE)
        count = 0
        for account in accounts:
            if account.get('product_id') == product_id and not account.get('sold', False):
                count += 1
        return count
    
    def mark_account_sold(self, account_data: str) -> bool:
        """Đánh dấu tài khoản đã bán"""
        accounts = self._read_data(config.ACCOUNTS_FILE)
        for account in accounts:
            if account['data'] == account_data and not account['sold']:
                account['sold'] = True
                self._write_data(config.ACCOUNTS_FILE, accounts)
                return True
        return False
    
    def get_visibility_settings(self) -> dict:
        """Lấy cài đặt hiển thị từ cơ sở dữ liệu"""
        # Đây là ví dụ, bạn cần triển khai theo cơ sở dữ liệu của mình
        settings = self.get_settings()
        return settings or {'show_premium': True}  # Giá trị mặc định
    
    def update_visibility_setting(self, key: str, value: bool) -> None:
        """Cập nhật cài đặt hiển thị trong cơ sở dữ liệu"""
        # Đây là ví dụ, bạn cần triển khai theo cơ sở dữ liệu của mình
        self.update_setting(key, value) 