from telebot import TeleBot
from telebot.types import Message, CallbackQuery
import keyboards
import logging
import os
from modules.pikbest_downloader import PikbestDownloader
import config
import json

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self, bot: TeleBot, db):
        self.bot = bot
        self.db = db
        
        # Khởi tạo PikbestDownloader với thông tin đăng nhập từ config
        cookies = getattr(config, 'PIKBEST_COOKIES', None)
        username = getattr(config, 'PIKBEST_USERNAME', None)
        password = getattr(config, 'PIKBEST_PASSWORD', None)
        
        # Thử tải cookie từ file nếu không có cookie trong config
        if not cookies:
            cookies_file = 'pikbest_cookies.json'
            if os.path.exists(cookies_file):
                with open(cookies_file, 'r') as f:
                    cookies = json.load(f)
        
        self.downloader = PikbestDownloader(
            username=username,
            password=password,
            cookies=cookies
        )
        
        # Lưu trạng thái người dùng
        self.user_states = {}
    
    def show_download_menu(self, chat_id: int, message_id: int) -> None:
        """Hiển thị menu tải file"""
        self.bot.edit_message_text(
            "📥 *Menu tải file*\n\n"
            "Chọn một tùy chọn bên dưới để tìm và tải file:",
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.download_files_menu()
        )
    
    def show_file_list(self, chat_id: int, message_id: int) -> None:
        """Hiển thị danh sách file"""
        self.bot.edit_message_text(
            "📁 *Danh sách file*\n\n"
            "Chức năng này đang được phát triển. Vui lòng quay lại sau.",
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.back_button("download_files")
        )
    
    def search_file(self, chat_id: int, message_id: int) -> None:
        """Hiển thị form tìm kiếm file"""
        self.bot.edit_message_text(
            "🔍 *Tìm kiếm file*\n\n"
            "Chức năng này đang được phát triển. Vui lòng quay lại sau.",
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.back_button("download_files")
        )
    
    def show_popular_files(self, chat_id: int, message_id: int) -> None:
        """Hiển thị danh sách file phổ biến"""
        self.bot.edit_message_text(
            "📊 *File phổ biến*\n\n"
            "Chức năng này đang được phát triển. Vui lòng quay lại sau.",
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.back_button("download_files")
        )
    
    def show_newest_files(self, chat_id: int, message_id: int) -> None:
        """Hiển thị danh sách file mới nhất"""
        self.bot.edit_message_text(
            "🆕 *File mới nhất*\n\n"
            "Chức năng này đang được phát triển. Vui lòng quay lại sau.",
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.back_button("download_files")
        )
    
    def download_from_url(self, chat_id: int, message_id: int) -> None:
        """Hiển thị form nhập URL để tải file"""
        # Lưu trạng thái người dùng
        self.user_states[chat_id] = {
            'state': 'waiting_for_download_url'
        }
        
        try:
            # Sử dụng HTML thay vì Markdown để tránh lỗi phân tích cú pháp
            self.bot.edit_message_text(
                "🔗 <b>Tải file từ URL</b>\n\n"
                "Vui lòng gửi URL từ Pikbest.com để tải file.\n\n"
                "Ví dụ: https://pikbest.com/templates/business-card-template_123456.html",
                chat_id,
                message_id,
                parse_mode="HTML",  # Thay đổi từ Markdown sang HTML
                reply_markup=keyboards.back_button("download_files")
            )
        except Exception as e:
            logger.error(f"Lỗi khi hiển thị form tải file: {e}")
            # Thử gửi lại không có định dạng đặc biệt
            try:
                self.bot.edit_message_text(
                    "🔗 Tải file từ URL\n\n"
                    "Vui lòng gửi URL từ Pikbest.com để tải file.\n\n"
                    "Ví dụ: https://pikbest.com/templates/business-card-template_123456.html",
                    chat_id,
                    message_id,
                    parse_mode=None,  # Không sử dụng định dạng đặc biệt
                    reply_markup=keyboards.back_button("download_files")
                )
            except Exception as inner_e:
                logger.error(f"Lỗi khi gửi tin nhắn không định dạng: {inner_e}")
    
    def process_download_url(self, message: Message) -> None:
        """Xử lý URL tải file từ người dùng"""
        chat_id = message.chat.id
        url = message.text.strip()
        
        # Xóa trạng thái người dùng
        if chat_id in self.user_states:
            del self.user_states[chat_id]
        
        # Gửi thông báo đang xử lý
        try:
            processing_msg = self.bot.send_message(
                chat_id,
                "⏳ <b>Đang xử lý yêu cầu tải file...</b> Vui lòng đợi trong giây lát.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo xử lý: {e}")
            processing_msg = self.bot.send_message(
                chat_id,
                "⏳ Đang xử lý yêu cầu tải file... Vui lòng đợi trong giây lát."
            )
        
        # Kiểm tra trạng thái đăng nhập trước
        if not self.downloader.check_login_status():
            try:
                self.bot.edit_message_text(
                    "❌ <b>Lỗi đăng nhập</b>\n\n"
                    "Bot chưa đăng nhập vào Pikbest hoặc phiên đăng nhập đã hết hạn.\n"
                    "Vui lòng liên hệ quản trị viên để cập nhật cookie.",
                    chat_id,
                    processing_msg.message_id,
                    parse_mode="HTML",
                    reply_markup=keyboards.back_button("download_files")
                )
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo lỗi đăng nhập: {e}")
            return
        
        # Tải file
        file_path, error = self.downloader.download_file(url)
        
        if error:
            # Gửi thông báo lỗi
            try:
                self.bot.edit_message_text(
                    f"❌ <b>Lỗi khi tải file</b>\n\n{error}",
                    chat_id,
                    processing_msg.message_id,
                    parse_mode="HTML",
                    reply_markup=keyboards.back_button("download_files")
                )
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo lỗi tải file: {e}")
            return
        
        try:
            # Gửi file cho người dùng
            with open(file_path, 'rb') as file:
                file_name = os.path.basename(file_path)
                
                # Kiểm tra loại file và gửi phù hợp
                if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    self.bot.send_photo(
                        chat_id,
                        file,
                        caption=f"📥 <b>File đã tải:</b> {file_name}",
                        parse_mode="HTML"
                    )
                elif file_path.lower().endswith(('.mp4', '.avi', '.mov')):
                    self.bot.send_video(
                        chat_id,
                        file,
                        caption=f"📥 <b>File đã tải:</b> {file_name}",
                        parse_mode="HTML"
                    )
                else:
                    self.bot.send_document(
                        chat_id,
                        file,
                        caption=f"📥 <b>File đã tải:</b> {file_name}",
                        parse_mode="HTML"
                    )
                
                # Gửi thông báo thành công
                try:
                    self.bot.edit_message_text(
                        "✅ <b>Tải file thành công!</b>\n\n"
                        "Bạn có thể tiếp tục tải file khác hoặc quay lại menu chính.",
                        chat_id,
                        processing_msg.message_id,
                        parse_mode="HTML",
                        reply_markup=keyboards.download_again_keyboard()
                    )
                except Exception as e:
                    logger.error(f"Lỗi khi gửi thông báo thành công: {e}")
        except Exception as e:
            logger.error(f"Lỗi khi gửi file: {e}")
            try:
                self.bot.edit_message_text(
                    f"❌ <b>Lỗi khi gửi file</b>\n\n{str(e)}",
                    chat_id,
                    processing_msg.message_id,
                    parse_mode="HTML",
                    reply_markup=keyboards.back_button("download_files")
                )
            except Exception as inner_e:
                logger.error(f"Lỗi khi gửi thông báo lỗi gửi file: {inner_e}")
        finally:
            # Xóa file sau khi gửi
            self.downloader.cleanup_file(file_path) 