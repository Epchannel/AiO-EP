import telebot
import config
import handlers
import os
from database import Database

# Khởi tạo bot
bot = telebot.TeleBot(config.TOKEN)

# Khởi tạo cơ sở dữ liệu
db = Database()

def main():
    """Hàm chính để chạy bot"""
    # Đảm bảo thư mục data tồn tại
    os.makedirs("data", exist_ok=True)
    
    # Đăng ký các handler
    handlers.register_handlers(bot)
    
    # Khởi động bot
    print("Bot đã khởi động!")
    bot.polling(none_stop=True, interval=0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Lỗi: {e}")
        # Thử khởi động lại bot
        import time
        time.sleep(10)
        main() 