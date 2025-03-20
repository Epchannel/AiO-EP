import telebot
from telebot import apihelper
import config
import handlers
import os
import logging
from database import Database

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bật middleware
apihelper.ENABLE_MIDDLEWARE = True

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
    logger.info("Bot đã khởi động!")
    
    # Thêm handler cho tin nhắn
    @bot.middleware_handler(update_types=['message'])
    def log_messages(bot_instance, message):
        """Log tất cả các tin nhắn"""
        logger.info(f"Received message from {message.from_user.username or 'Unknown'} (ID: {message.from_user.id}): {message.text or '<no text>'}")
        return message
    
    # Thêm handler cho callback query
    @bot.middleware_handler(update_types=['callback_query'])
    def log_callbacks(bot_instance, callback):
        """Log tất cả các callback"""
        logger.info(f"Received callback from {callback.from_user.username or 'Unknown'} (ID: {callback.from_user.id}): {callback.data}")
        return callback
    
    # Bắt đầu polling
    bot.polling(none_stop=True, interval=0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Lỗi: {e}", exc_info=True)
        # Thử khởi động lại bot
        import time
        time.sleep(10)
        main()