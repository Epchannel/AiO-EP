import json
import os
import datetime
import config
from database import Database

# Khởi tạo database
db = Database()

# Danh sách người dùng cần khôi phục
users_to_restore = [
    {"id": 1307757183, "username": "dhvu1990", "time": "2025-03-17 18:57:34"},
    {"id": 6220854723, "username": "yukii2000", "time": "2025-03-17 18:57:38"},
    {"id": 1916382374, "username": "maithisla", "time": "2025-03-17 18:57:48"},
    {"id": 5249925579, "username": "occoloc", "time": "2025-03-17 18:57:48"},
    {"id": 2141675254, "username": "QUANGSANG36", "time": "2025-03-17 18:57:59"},
    {"id": 1181061580, "username": "Kietphanz", "time": "2025-03-17 18:57:59"},
    {"id": 1682663961, "username": "Rayiiz", "time": "2025-03-17 18:58:02"},
    {"id": 1088826189, "username": "risketlucio", "time": "2025-03-17 18:58:03"},
    {"id": 949940973, "username": "hwinxz", "time": "2025-03-17 18:58:10"},
    {"id": 7538691623, "username": "autogpmok", "time": "2025-03-17 18:58:13"},
    {"id": 1509851649, "username": "davidkush28", "time": "2025-03-17 18:58:34"},
    {"id": 1146919564, "username": "atus1506", "time": "2025-03-17 18:58:35"},
    {"id": 904593176, "username": "kengi2311", "time": "2025-03-17 18:58:53"},
    {"id": 1921587118, "username": "hxhiu", "time": "2025-03-17 18:58:56"},
    {"id": 5295694116, "username": "sananchi", "time": "2025-03-17 18:59:04"},
    {"id": 777280724, "username": "lucylatui", "time": "2025-03-17 18:59:05"},
    {"id": 593553203, "username": "tofuzz", "time": "2025-03-17 18:59:23"},
    {"id": 5117006532, "username": "vanson9556", "time": "2025-03-17 18:59:26"},
    {"id": 7930249556, "username": "suxinjily", "time": "2025-03-17 18:59:27"},
    {"id": 397428588, "username": "dzung1", "time": "2025-03-17 18:59:27"},
    {"id": 879966314, "username": "quit9898", "time": "2025-03-17 18:59:36"},
    {"id": 1331261560, "username": "panikpikachu", "time": "2025-03-17 18:59:38"},
    {"id": 7637670077, "username": "uyennlee", "time": "2025-03-17 18:59:38"},
    {"id": 350130295, "username": "luc1frr", "time": "2025-03-17 18:59:44"},
    {"id": 6198540572, "username": "Unlockmeta", "time": "2025-03-17 18:59:48"},
    {"id": 813559603, "username": "Id09st", "time": "2025-03-17 18:59:49"},
    {"id": 337790424, "username": "rocky3414", "time": "2025-03-17 18:59:51"},
    {"id": 904558945, "username": "longmiker", "time": "2025-03-17 18:59:58"},
    {"id": 713177588, "username": "tendernat", "time": "2025-03-17 19:00:06"},
    {"id": 6815733629, "username": "ductaihjhj", "time": "2025-03-17 19:00:11"},
    {"id": 5070021487, "username": "harrytienthereal", "time": "2025-03-17 19:00:13"},
    {"id": 2080232783, "username": "nguyenanhtun", "time": "2025-03-17 21:13:59"},
    {"id": 5677537156, "username": "QDT69", "time": "2025-03-17 21:13:59"},
    {"id": 975486085, "username": "vinhleduc", "time": "2025-03-17 21:38:38"},
    {"id": 5833992737, "username": "TriAbcxyz", "time": "2025-03-17 22:01:19"},
    {"id": 6143639983, "username": "damri9358", "time": "2025-03-17 22:52:38"},
    {"id": 7144979238, "username": "datnguyen24", "time": "2025-03-17 22:52:39"},
    {"id": 6809524658, "username": "vietdung2708", "time": "2025-03-17 22:55:50"},
    {"id": 7140814657, "username": "ngochacoder", "time": "2025-03-17 22:55:50"}
]

# Đọc dữ liệu người dùng hiện tại
try:
    current_users = db._read_data(config.USERS_FILE)
    print(f"Đã đọc {len(current_users)} người dùng từ database.")
except Exception as e:
    print(f"Lỗi khi đọc dữ liệu người dùng: {e}")
    current_users = []

# Danh sách ID người dùng hiện tại
current_user_ids = [user.get('id') for user in current_users]

# Khôi phục người dùng
restored_count = 0
for user_data in users_to_restore:
    user_id = user_data["id"]
    
    # Kiểm tra xem người dùng đã tồn tại chưa
    if user_id not in current_user_ids:
        # Tạo dữ liệu người dùng mới
        new_user = {
            'id': user_id,
            'username': user_data["username"],
            'balance': 0,
            'banned': False,
            'purchases': [],
            'created_at': user_data["time"]
        }
        
        # Thêm người dùng vào database
        if db.add_user(new_user):
            print(f"Đã khôi phục người dùng: {user_data['username']} (ID: {user_id})")
            restored_count += 1
        else:
            print(f"Không thể khôi phục người dùng: {user_data['username']} (ID: {user_id})")
    else:
        print(f"Người dùng đã tồn tại: {user_data['username']} (ID: {user_id})")

print(f"\nĐã khôi phục thành công {restored_count} người dùng.")
print(f"Tổng số người dùng hiện tại: {len(db._read_data(config.USERS_FILE))}") 