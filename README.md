# SẢNH TRUYỆN

**Ứng dụng desktop Windows viết bằng Python + Tkinter**, dành cho quy trình thu thập, biên tập và lưu trữ tiểu thuyết.

Giao diện được thiết kế theo phong cách **Occult Library / Gothic Victorian**: nền tối, đỏ rượu vang, đồng cổ và thanh điều hướng thư viện bên trái.

## Các khu vực

### 1. Tổng quan
Lối vào bốn khu vực chính, thư viện dữ liệu và workspace.

### 2. Cào truyện
- Mở Chrome thật và tiện ích WebToEpub.
- Thu thập truyện thành EPUB.
- Chuyển EPUB sang TXT trong thư mục dự án.
- File RAW gốc không bị ghi đè.

### 3. Dịch truyện
Có hai bộ máy:
- **HachimiMT-60 cục bộ**: chạy bằng CPU, không yêu cầu GPU rời. Cần chạy `install-local-ai.bat` để cài thư viện AI.
- **ChatGPT qua Clipboard**: ứng dụng tạo prompt, người dùng tự gửi trong ChatGPT và nhận kết quả bằng nút **NHẬN CLIPBOARD**. Ứng dụng không đăng nhập, không tự gửi tin nhắn và không đọc phản hồi ChatGPT ở nền.

Hai chế độ xử lý:
- **Dịch raw Trung**.
- **Viết lại convert** thành văn xuôi tiếng Việt tự nhiên.

Bộ đánh số chương liên tục sẽ chuẩn hóa số chương theo thứ tự xuất hiện trên toàn bộ RAW. Khi quyển mới bắt đầu lại ở chương 1, chương đó sẽ tiếp tục số sau chương cuối quyển trước. Tiêu đề quyển được giữ nguyên và file RAW gốc không bị sửa. Nhận diện tiêu đề hiện dựa vào các dòng riêng như `第一章`, `第1章`, `Chương 1` hoặc `Chapter 1`.

### 4. Phòng thu audio
Giao diện phòng thu hiện có:
- Mở TXT hoặc dán nội dung.
- Chọn giọng Nam Minh / Hoài My và tốc độ đọc.
- Khu vực lịch sử, trạng thái GitHub Actions và mở thư mục kết quả.

**Lưu ý quan trọng:** giao diện GitHub Actions đã được dựng, nhưng kết nối thực tế để gửi nội dung, theo dõi workflow và tải MP3 **chưa được tích hợp ở phiên bản này**. Nút tạo audio sẽ thông báo trạng thái chưa kết nối; ứng dụng không gửi văn bản truyện lên repository. Không cần cài hoặc chạy Story-TTS-API cho giao diện hiện tại.

## Cài đặt trên Windows 10/11

### Chuẩn bị
- Python 3.11 64-bit.
- Google Chrome (phục vụ quy trình WebToEpub).

### Cài đặt
1. Tải ZIP từ [SANH-TRUYEN](https://github.com/hantuyet425/SANH-TRUYEN/archive/refs/heads/main.zip).
2. Giải nén vào thư mục mong muốn.
3. Chạy `install.bat`.
4. Khi cài xong, chạy `run.bat`.

Để dùng HachimiMT-60, chạy thêm `install-local-ai.bat`. Lần đầu sử dụng mô hình cần kết nối Internet để tải trọng số.

## Dữ liệu

Dữ liệu cá nhân được lưu trong `data\\`:
- `downloads\\`: EPUB tải về.
- `projects\\`: RAW, bản dịch và audio theo dự án.
- `models\\`: bộ nhớ đệm HachimiMT.
- `chrome_profile\\`: hồ sơ Chrome riêng.
- `logs\\` và `temp\\`: log và file tạm.

Không đẩy truyện, bản dịch, cookie, mật khẩu, token hay API key lên repository công khai.

## Kiểm thử

Trong thư mục dự án:

```bat
.venv\\Scripts\\activate.bat
python -m unittest discover -s tests -v
python -m compileall -q .
```

Các kiểm thử tự động kiểm tra cú pháp và một số logic xử lý văn bản; vẫn cần kiểm thử giao diện trên Windows thực tế.

## Thành phần bên thứ ba

Xem [NOTICE.md](NOTICE.md) và [LICENSE](LICENSE). Chrome, WebToEpub và trọng số HachimiMT-60 không được đóng gói cùng ứng dụng.
