import os
import requests
import time
import logging
from bs4 import BeautifulSoup
import re
import json

logger = logging.getLogger(__name__)

class PikbestDownloader:
    def __init__(self, username=None, password=None, cookies=None):
        self.base_url = "https://pikbest.com"
        self.session = requests.Session()
        
        # Thêm User-Agent để tránh bị chặn
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://pikbest.com/'
        })
        
        self.download_folder = os.path.join(os.getcwd(), "downloads")
        
        # Đảm bảo thư mục tải xuống tồn tại
        os.makedirs(self.download_folder, exist_ok=True)
        
        # Thiết lập session với cookies nếu được cung cấp
        if cookies:
            # Nếu cookies là chuỗi JSON, chuyển đổi thành dict
            if isinstance(cookies, str):
                try:
                    cookies = json.loads(cookies)
                except:
                    pass
            
            # Thiết lập cookies cho session
            self.session.cookies.update(cookies)
            logger.info("Đã thiết lập cookies cho session")
            
            # Kiểm tra xem đã đăng nhập thành công chưa
            self.check_login_status()
        elif username and password:
            logger.warning("Đăng nhập tự động không được hỗ trợ. Vui lòng sử dụng cookies.")
            # Không cố gắng đăng nhập tự động nữa
    
    def check_login_status(self):
        """Kiểm tra trạng thái đăng nhập"""
        try:
            # Sử dụng URL chính xác để kiểm tra trạng thái đăng nhập
            response = self.session.get(f"{self.base_url}/?m=home&a=userInfo")
            response.raise_for_status()
            
            # Kiểm tra nếu có chuyển hướng đến trang đăng nhập
            if "login" in response.url.lower():
                logger.warning("Chưa đăng nhập vào Pikbest (chuyển hướng đến trang đăng nhập)")
                return False
            
            # Kiểm tra nội dung trang để xác định đã đăng nhập
            if "Log Out" in response.text or "My Account" in response.text or "Sign Out" in response.text or "Logout" in response.text:
                logger.info("Đã đăng nhập vào Pikbest thành công")
                return True
            
            # Kiểm tra thêm bằng cách tìm tên người dùng hoặc avatar
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tìm các phần tử chỉ xuất hiện khi đã đăng nhập
            user_avatar = soup.find('img', class_='avatar') or soup.find('div', class_='user-avatar')
            user_info = soup.find('div', class_='user-info') or soup.find('div', class_='user-center')
            
            if user_avatar or user_info:
                logger.info("Đã đăng nhập vào Pikbest thành công (phát hiện thông tin người dùng)")
                return True
            
            # Kiểm tra nếu có nút "Premium" hoặc thông tin người dùng
            premium_btn = soup.find('a', string=re.compile('Premium', re.IGNORECASE))
            if premium_btn:
                logger.info("Đã đăng nhập vào Pikbest thành công (phát hiện nút Premium)")
                return True
            
            # Lưu HTML để debug
            with open('pikbest_response.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.warning("Đã lưu HTML phản hồi vào pikbest_response.html để debug")
            
            # Kiểm tra thêm các dấu hiệu đăng nhập khác
            if "user" in response.text.lower() and "account" in response.text.lower():
                logger.info("Có thể đã đăng nhập vào Pikbest (phát hiện từ khóa user/account)")
                return True
            
            logger.warning("Chưa đăng nhập vào Pikbest. Vui lòng kiểm tra lại cookies.")
            return False
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra trạng thái đăng nhập: {e}")
            return False
    
    def is_valid_pikbest_url(self, url):
        """Kiểm tra URL có phải là URL Pikbest hợp lệ không"""
        return url.startswith("https://pikbest.com/") or "pikbest.com" in url
    
    def extract_file_info(self, url):
        """Trích xuất thông tin file từ URL Pikbest"""
        try:
            logger.info(f"===== BẮT ĐẦU TRÍCH XUẤT THÔNG TIN FILE =====")
            logger.info(f"Đang truy cập URL sản phẩm: {url}")
            
            # Thêm headers để mô phỏng trình duyệt
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://pikbest.com/'
            }
            
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Đã nhận phản hồi từ trang sản phẩm: {response.status_code}")
            
            # Lưu HTML để debug
            with open('pikbest_product_page.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info("Đã lưu HTML trang sản phẩm vào pikbest_product_page.html để debug")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tìm tiêu đề
            title_elem = soup.find('h1', class_='detail-title')
            if not title_elem:
                title_elem = soup.find('h1')  # Tìm bất kỳ thẻ h1 nào
            
            title = title_elem.text.strip() if title_elem else "Unknown Title"
            logger.info(f"Đã tìm thấy tiêu đề: {title}")
            
            # Tìm nút tải xuống sử dụng XPath đã cung cấp
            download_btn = None
            
            # Phương pháp 1: Sử dụng CSS selector tương đương với XPath
            logger.info("Tìm nút tải xuống bằng CSS selector tương đương với XPath: /html/body/div[3]/div/div[2]/div[2]/div/div[1]/div/a")
            download_btn = soup.select_one('div.detail-download-btn a')
            if download_btn:
                logger.info(f"Đã tìm thấy nút tải xuống bằng CSS selector 'div.detail-download-btn a': {download_btn}")
            else:
                download_btn = soup.select_one('div > div > div > div > div > div > a')
                if download_btn:
                    logger.info(f"Đã tìm thấy nút tải xuống bằng CSS selector 'div > div > div > div > div > div > a': {download_btn}")
            
            # Phương pháp 2: Tìm tất cả các nút có thể là nút tải xuống
            if not download_btn:
                logger.info("Không tìm thấy nút tải xuống bằng CSS selector, thử tìm bằng từ khóa")
                potential_buttons = soup.find_all('a', href=True)
                logger.info(f"Tìm thấy {len(potential_buttons)} nút có href")
                
                for i, btn in enumerate(potential_buttons):
                    href = btn.get('href', '').lower()
                    text = btn.text.lower()
                    classes = ' '.join(btn.get('class', []))
                    
                    # Log để debug
                    if 'download' in href or 'download' in text or 'download' in classes:
                        logger.info(f"Nút tiềm năng #{i+1}: Text='{btn.text}', Href='{btn.get('href')}', Class='{classes}'")
                    
                    if ('download' in href or 'download' in text or 'btn' in classes) and not download_btn:
                        download_btn = btn
                        logger.info(f"Đã chọn nút tải xuống #{i+1}: {btn}")
                        break
            
            # Phương pháp 3: Tìm nút có chứa từ khóa "Download" hoặc "Free Download"
            if not download_btn:
                logger.info("Thử tìm nút có text chứa 'Download' hoặc 'Free Download'")
                for i, btn in enumerate(soup.find_all('a')):
                    if btn.text and ('Download' in btn.text or 'Free Download' in btn.text):
                        download_btn = btn
                        logger.info(f"Đã tìm thấy nút tải xuống #{i+1} qua text: '{btn.text}', Href: '{btn.get('href')}'")
                        break
            
            # Phương pháp 4: Tìm nút trong div có class chứa "download"
            if not download_btn:
                logger.info("Thử tìm nút trong div có class chứa 'download'")
                download_divs = soup.find_all('div', class_=lambda c: c and 'download' in c.lower())
                logger.info(f"Tìm thấy {len(download_divs)} div có class chứa 'download'")
                
                for i, div in enumerate(download_divs):
                    btn = div.find('a', href=True)
                    if btn:
                        download_btn = btn
                        logger.info(f"Đã tìm thấy nút tải xuống #{i+1} trong div download: Text='{btn.text}', Href='{btn.get('href')}'")
                        break
            
            download_url = download_btn['href'] if download_btn else None
            
            if download_url:
                logger.info(f"Đã tìm thấy URL tải xuống: {download_url}")
                
                # Nếu URL tải xuống là đường dẫn tương đối, thêm domain
                if not download_url.startswith('http'):
                    old_url = download_url
                    if download_url.startswith('/'):
                        download_url = f"https://pikbest.com{download_url}"
                    else:
                        download_url = f"https://pikbest.com/{download_url}"
                    logger.info(f"Đã chuyển đổi URL tương đối '{old_url}' thành URL tuyệt đối: {download_url}")
            else:
                logger.warning("Không tìm thấy URL tải xuống!")
            
            # Tìm loại file
            file_type = "unknown"
            if "templates" in url or "template" in url:
                file_type = "template"
            elif "video" in url:
                file_type = "video"
            elif "png-images" in url or "image" in url or "photo" in url:
                file_type = "image"
            elif "music" in url or "audio" in url or "sound" in url:
                file_type = "audio"
            
            logger.info(f"Loại file: {file_type}")
            logger.info(f"===== KẾT THÚC TRÍCH XUẤT THÔNG TIN FILE =====")
            
            return {
                'title': title,
                'download_url': download_url,
                'file_type': file_type
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất thông tin file: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def download_file(self, url):
        """Tải file từ URL Pikbest và trả về đường dẫn đến file đã tải"""
        try:
            logger.info(f"===== BẮT ĐẦU TẢI FILE =====")
            logger.info(f"URL gốc: {url}")
            
            # Kiểm tra URL hợp lệ
            if not self.is_valid_pikbest_url(url):
                logger.error(f"URL không hợp lệ: {url}")
                return None, "URL không hợp lệ. Vui lòng cung cấp URL từ Pikbest.com"
            
            # Kiểm tra trạng thái đăng nhập
            login_status = self.check_login_status()
            if not login_status:
                logger.warning("Đang thử tải file mà không cần đăng nhập...")
            else:
                logger.info("Đã đăng nhập vào Pikbest")
            
            # Trích xuất thông tin file
            logger.info("Bước 1: Trích xuất thông tin file")
            file_info = self.extract_file_info(url)
            if not file_info or not file_info['download_url']:
                logger.error("Không thể tìm thấy link tải xuống")
                return None, "Không thể tìm thấy link tải xuống. Vui lòng kiểm tra URL hoặc đăng nhập lại."
            
            # Xử lý trang xác nhận tải xuống nếu cần
            logger.info("Bước 2: Xử lý trang xác nhận tải xuống")
            logger.info(f"URL tải xuống ban đầu: {file_info['download_url']}")
            download_url = self.handle_download_confirmation(file_info['download_url'])
            logger.info(f"URL tải xuống sau khi xử lý trang xác nhận: {download_url}")
            
            # Nếu URL tải xuống không thay đổi, thử thêm một bước nữa
            if download_url == file_info['download_url']:
                logger.info("Bước 3: URL tải xuống không thay đổi sau khi xử lý trang xác nhận, thử thêm một bước nữa")
                
                # Truy cập URL tải xuống để xem có chuyển hướng không
                logger.info(f"Truy cập URL tải xuống: {download_url}")
                download_response = self.session.get(download_url, allow_redirects=True)
                
                # Nếu có chuyển hướng, sử dụng URL cuối cùng
                if download_response.url != download_url:
                    logger.info(f"Đã chuyển hướng đến: {download_response.url}")
                    download_url = download_response.url
                
                # Lưu HTML để debug
                with open('pikbest_download_page.html', 'w', encoding='utf-8') as f:
                    f.write(download_response.text)
                logger.info("Đã lưu HTML trang tải xuống vào pikbest_download_page.html để debug")
                
                # Kiểm tra xem có nút tải xuống trong trang này không
                download_soup = BeautifulSoup(download_response.text, 'html.parser')
                
                # Tìm tất cả các link có thể là link tải xuống
                download_links = []
                for i, link in enumerate(download_soup.find_all('a', href=True)):
                    href = link.get('href', '').lower()
                    if 'download' in href or '.zip' in href or '.psd' in href:
                        download_links.append((i, link))
                        logger.info(f"Link tải xuống tiềm năng #{i+1}: Text='{link.text}', Href='{link.get('href')}'")
                
                logger.info(f"Tìm thấy {len(download_links)} link có thể là link tải xuống")
                
                if download_links:
                    # Lấy link đầu tiên
                    i, final_download_btn = download_links[0]
                    logger.info(f"Chọn link tải xuống #{i+1}: Text='{final_download_btn.text}', Href='{final_download_btn.get('href')}'")
                    
                    if final_download_btn and final_download_btn.get('href'):
                        final_url = final_download_btn['href']
                        
                        # Nếu URL là đường dẫn tương đối, thêm domain
                        if not final_url.startswith('http'):
                            old_url = final_url
                            if final_url.startswith('/'):
                                final_url = f"https://pikbest.com{final_url}"
                            else:
                                final_url = f"https://pikbest.com/{final_url}"
                            logger.info(f"Đã chuyển đổi URL tương đối '{old_url}' thành URL tuyệt đối: {final_url}")
                        
                        logger.info(f"Đã tìm thấy URL tải xuống cuối cùng: {final_url}")
                        download_url = final_url
            
            # Tạo tên file an toàn
            safe_title = re.sub(r'[^\w\-_.]', '_', file_info['title'])
            temp_filename = f"{int(time.time())}_{safe_title}"
            logger.info(f"Tên file tạm thời: {temp_filename}")
            
            # Tải file
            logger.info(f"Bước 4: Bắt đầu tải file từ: {download_url}")
            
            # Thêm headers để mô phỏng trình duyệt
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': url,
                'Origin': 'https://pikbest.com'
            }
            
            logger.info(f"Gửi request tải file với headers: {headers}")
            download_response = self.session.get(download_url, stream=True, headers=headers)
            download_response.raise_for_status()
            
            # Lưu headers để debug
            logger.info(f"Headers phản hồi: {dict(download_response.headers)}")
            
            # Xác định phần mở rộng file từ Content-Disposition hoặc URL
            content_disposition = download_response.headers.get('Content-Disposition', '')
            logger.info(f"Content-Disposition: {content_disposition}")
            
            extension = ""
            if 'filename=' in content_disposition:
                filename = re.findall('filename="(.+)"', content_disposition)
                if filename:
                    logger.info(f"Tìm thấy tên file trong Content-Disposition: {filename[0]}")
                    extension = os.path.splitext(filename[0])[1]
                else:
                    logger.info(f"Không tìm thấy tên file trong Content-Disposition, sử dụng URL: {download_url}")
                    extension = os.path.splitext(download_url)[1]
            else:
                logger.info(f"Không có Content-Disposition, sử dụng URL: {download_url}")
                extension = os.path.splitext(download_url)[1]
            
            logger.info(f"Phần mở rộng file từ URL/Content-Disposition: {extension}")
            
            if not extension:
                # Đoán phần mở rộng từ loại file
                logger.info(f"Không tìm thấy phần mở rộng, đoán từ loại file: {file_info['file_type']}")
                if file_info['file_type'] == 'template':
                    extension = '.zip'
                elif file_info['file_type'] == 'video':
                    extension = '.mp4'
                elif file_info['file_type'] == 'image':
                    extension = '.png'
                elif file_info['file_type'] == 'audio':
                    extension = '.mp3'
                else:
                    extension = '.zip'
                logger.info(f"Đã đoán phần mở rộng file: {extension}")
            
            # Đường dẫn đầy đủ đến file
            file_path = os.path.join(self.download_folder, f"{temp_filename}{extension}")
            logger.info(f"Đường dẫn file đầy đủ: {file_path}")
            
            # Lưu file
            logger.info("Bắt đầu lưu file...")
            total_size = 0
            with open(file_path, 'wb') as f:
                for chunk in download_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
                        if total_size % (1024 * 1024) == 0:  # Log mỗi 1MB
                            logger.info(f"Đã tải {total_size / (1024 * 1024):.2f} MB")
            
            # Kiểm tra kích thước file
            file_size = os.path.getsize(file_path)
            logger.info(f"Kích thước file cuối cùng: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
            
            if file_size < 1000:  # Nếu file nhỏ hơn 1KB, có thể là lỗi
                logger.warning(f"File có kích thước nhỏ ({file_size} bytes), kiểm tra nội dung")
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1000)  # Đọc 1000 ký tự đầu tiên
                    logger.warning(f"Nội dung file: {content}")
                    
                    # Kiểm tra nếu nội dung chứa thông báo lỗi
                    if "login" in content.lower() or "sign in" in content.lower():
                        logger.error("File yêu cầu đăng nhập")
                        return None, "Cần đăng nhập để tải file này. Vui lòng cập nhật cookie."
                    
                    # Kiểm tra nếu nội dung là HTML thay vì file thực
                    if "<html" in content.lower() or "<!doctype" in content.lower():
                        logger.error("Nhận được trang HTML thay vì file")
                        return None, "Nhận được trang HTML thay vì file. Có thể cần xác thực hoặc có bước tải xuống bổ sung."
            
            logger.info(f"Đã tải file thành công: {file_path}")
            logger.info(f"===== KẾT THÚC TẢI FILE =====")
            return file_path, None
            
        except Exception as e:
            logger.error(f"Lỗi khi tải file: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None, f"Lỗi khi tải file: {str(e)}"
    
    def cleanup_file(self, file_path):
        """Xóa file sau khi đã gửi"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Đã xóa file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Lỗi khi xóa file: {e}")
            return False

    def save_cookies(self, file_path='pikbest_cookies.json'):
        """Lưu cookie hiện tại vào file"""
        try:
            cookies_dict = {c.name: c.value for c in self.session.cookies}
            with open(file_path, 'w') as f:
                json.dump(cookies_dict, f)
            logger.info(f"Đã lưu cookies vào {file_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cookies: {e}")
            return False

    def load_cookies(self, file_path='pikbest_cookies.json'):
        """Tải cookie từ file"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    cookies = json.load(f)
                self.session.cookies.update(cookies)
                logger.info(f"Đã tải cookies từ {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Lỗi khi tải cookies: {e}")
            return False

    def handle_download_confirmation(self, url):
        """Xử lý trang xác nhận tải xuống nếu cần"""
        try:
            logger.info(f"===== BẮT ĐẦU XỬ LÝ TRANG XÁC NHẬN TẢI XUỐNG =====")
            logger.info(f"Kiểm tra trang xác nhận tải xuống: {url}")
            
            # Thêm headers để mô phỏng trình duyệt
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://pikbest.com/'
            }
            
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Đã nhận phản hồi từ trang xác nhận: {response.status_code}")
            
            # Lưu HTML để debug
            with open('pikbest_confirmation_page.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info("Đã lưu HTML trang xác nhận vào pikbest_confirmation_page.html để debug")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tìm nút "Start Download" trong popup
            logger.info("Tìm nút 'Start Download' trong popup với XPath: /html/body/div[20]/div/div/div/a")
            
            # Tìm tất cả các div có thể chứa nút Start Download
            popup_divs = soup.find_all('div', class_=lambda c: c and ('modal' in c.lower() or 'popup' in c.lower() or 'download' in c.lower()))
            logger.info(f"Tìm thấy {len(popup_divs)} div có thể chứa nút Start Download")
            
            # CSS Selector tương đương với XPath
            start_download_btn = None
            selectors = [
                'div.download-popup a', 
                'div.modal-content a', 
                'div.download-modal a',
                'div[class*="download"] a',
                'div[class*="modal"] a'
            ]
            
            for selector in selectors:
                btn = soup.select_one(selector)
                if btn:
                    logger.info(f"Đã tìm thấy nút với selector '{selector}': Text='{btn.text}', Href='{btn.get('href')}'")
                    start_download_btn = btn
                    break
            
            # Nếu tìm thấy nút Start Download
            if start_download_btn and start_download_btn.get('href'):
                download_url = start_download_btn['href']
                
                # Nếu URL là đường dẫn tương đối, thêm domain
                if not download_url.startswith('http'):
                    old_url = download_url
                    if download_url.startswith('/'):
                        download_url = f"https://pikbest.com{download_url}"
                    else:
                        download_url = f"https://pikbest.com/{download_url}"
                    logger.info(f"Đã chuyển đổi URL tương đối '{old_url}' thành URL tuyệt đối: {download_url}")
                
                logger.info(f"Đã tìm thấy nút Start Download với URL: {download_url}")
                logger.info(f"===== KẾT THÚC XỬ LÝ TRANG XÁC NHẬN TẢI XUỐNG =====")
                return download_url
            
            # Nếu không tìm thấy nút Start Download, tìm các nút khác có thể là nút tải xuống
            logger.info("Không tìm thấy nút Start Download, tìm các nút khác có thể là nút tải xuống")
            confirm_btn = None
            
            # Tìm tất cả các nút có href chứa "download" hoặc text chứa "download"
            download_links = []
            for i, btn in enumerate(soup.find_all('a', href=True)):
                href = btn.get('href', '').lower()
                text = btn.text.lower()
                
                if 'download' in href or 'download' in text:
                    download_links.append((i, btn))
                    logger.info(f"Nút tải xuống tiềm năng #{i+1}: Text='{btn.text}', Href='{btn.get('href')}'")
            
            logger.info(f"Tìm thấy {len(download_links)} nút có thể là nút tải xuống")
            
            if download_links:
                # Lấy nút đầu tiên
                i, confirm_btn = download_links[0]
                logger.info(f"Chọn nút tải xuống #{i+1}: Text='{confirm_btn.text}', Href='{confirm_btn.get('href')}'")
            
            if confirm_btn:
                download_url = confirm_btn['href']
                
                # Nếu URL là đường dẫn tương đối, thêm domain
                if not download_url.startswith('http'):
                    old_url = download_url
                    if download_url.startswith('/'):
                        download_url = f"https://pikbest.com{download_url}"
                    else:
                        download_url = f"https://pikbest.com/{download_url}"
                    logger.info(f"Đã chuyển đổi URL tương đối '{old_url}' thành URL tuyệt đối: {download_url}")
                
                logger.info(f"Đã tìm thấy URL xác nhận tải xuống: {download_url}")
                logger.info(f"===== KẾT THÚC XỬ LÝ TRANG XÁC NHẬN TẢI XUỐNG =====")
                return download_url
            
            # Nếu không tìm thấy nút nào, kiểm tra xem có form nào không
            logger.info("Không tìm thấy nút tải xuống, kiểm tra xem có form nào không")
            download_forms = soup.find_all('form')
            logger.info(f"Tìm thấy {len(download_forms)} form")
            
            download_form = None
            for i, form in enumerate(download_forms):
                action = form.get('action', '').lower()
                logger.info(f"Form #{i+1}: Action='{action}'")
                if action and 'download' in action:
                    download_form = form
                    logger.info(f"Đã chọn form #{i+1} với action: {action}")
                    break
            
            if download_form:
                form_action = download_form.get('action', '')
                if form_action:
                    # Nếu URL là đường dẫn tương đối, thêm domain
                    if not form_action.startswith('http'):
                        old_url = form_action
                        if form_action.startswith('/'):
                            form_action = f"https://pikbest.com{form_action}"
                        else:
                            form_action = f"https://pikbest.com/{form_action}"
                        logger.info(f"Đã chuyển đổi URL form tương đối '{old_url}' thành URL tuyệt đối: {form_action}")
                    
                    logger.info(f"Đã tìm thấy form tải xuống với action: {form_action}")
                    
                    # Gửi POST request đến form action
                    form_data = {}
                    for input_tag in download_form.find_all('input'):
                        name = input_tag.get('name')
                        value = input_tag.get('value', '')
                        if name:
                            form_data[name] = value
                    
                    logger.info(f"Gửi form data: {form_data}")
                    form_response = self.session.post(form_action, data=form_data)
                    form_response.raise_for_status()
                    
                    logger.info(f"Đã nhận phản hồi từ form: {form_response.status_code}")
                    
                    # Kiểm tra nếu response có URL chuyển hướng
                    if form_response.url != form_action:
                        logger.info(f"Form đã chuyển hướng đến: {form_response.url}")
                        logger.info(f"===== KẾT THÚC XỬ LÝ TRANG XÁC NHẬN TẢI XUỐNG =====")
                        return form_response.url
                    
                    # Lưu HTML phản hồi để debug
                    with open('pikbest_form_response.html', 'w', encoding='utf-8') as f:
                        f.write(form_response.text)
                    logger.info("Đã lưu HTML phản hồi form vào pikbest_form_response.html để debug")
                    
                    # Phân tích HTML phản hồi để tìm URL tải xuống
                    form_soup = BeautifulSoup(form_response.text, 'html.parser')
                    download_links = []
                    
                    for i, link in enumerate(form_soup.find_all('a', href=True)):
                        href = link.get('href', '').lower()
                        if 'download' in href:
                            download_links.append((i, link))
                            logger.info(f"Link tải xuống tiềm năng #{i+1} từ form: Text='{link.text}', Href='{link.get('href')}'")
                    
                    if download_links:
                        # Lấy link đầu tiên
                        i, download_link = download_links[0]
                        logger.info(f"Chọn link tải xuống #{i+1} từ form: Text='{download_link.text}', Href='{download_link.get('href')}'")
                        
                        if download_link and download_link.get('href'):
                            download_url = download_link['href']
                            
                            # Nếu URL là đường dẫn tương đối, thêm domain
                            if not download_url.startswith('http'):
                                old_url = download_url
                                if download_url.startswith('/'):
                                    download_url = f"https://pikbest.com{download_url}"
                                else:
                                    download_url = f"https://pikbest.com/{download_url}"
                                logger.info(f"Đã chuyển đổi URL tương đối '{old_url}' thành URL tuyệt đối: {download_url}")
                            
                            logger.info(f"Đã tìm thấy URL tải xuống từ form: {download_url}")
                            logger.info(f"===== KẾT THÚC XỬ LÝ TRANG XÁC NHẬN TẢI XUỐNG =====")
                            return download_url
            
            # Nếu không tìm thấy nút hoặc form nào, trả về URL gốc
            logger.warning(f"Không tìm thấy nút Start Download hoặc form tải xuống, sử dụng URL gốc: {url}")
            logger.info(f"===== KẾT THÚC XỬ LÝ TRANG XÁC NHẬN TẢI XUỐNG =====")
            return url
        except Exception as e:
            logger.error(f"Lỗi khi xử lý trang xác nhận tải xuống: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return url 