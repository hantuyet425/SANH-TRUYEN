# SẢNH TRUYỆN

**Ứng dụng desktop Windows** để xử lý tiểu thuyết theo quy trình:

**Chrome thật + WebToEpub → EPUB → TXT → Dịch Trung–Việt → MP3 theo chương.**

> Phiên bản hiện tại: **0.1.0 MVP**. Đây là bản mã nguồn thử nghiệm, chưa phải bản EXE cài đặt một lần. Cần kiểm thử trên máy Windows thực tế trước khi dùng với bộ truyện dài.

## Tải ZIP từ GitHub

1. Mở trang [hantuyet425/SANH-TRUYEN](https://github.com/hantuyet425/SANH-TRUYEN).
2. Nhấn nút **Code** màu xanh.
3. Chọn **Download ZIP**.
4. Giải nén, ví dụ vào `D:\SANH_TRUYEN`.

Bạn không cần fork repository.

## Cài đặt và chạy trên Windows 10/11

### Chuẩn bị

- **Python 3.11 64-bit**: tải tại [python.org](https://www.python.org/downloads/windows/). Khi cài, đánh dấu **Add Python to PATH**.
- **Google Chrome**: cài bản chính thức từ [google.com/chrome](https://www.google.com/chrome/).

### Cài phần mềm

1. Mở thư mục đã giải nén.
2. Nhấn đúp `install.bat`.
3. Chờ chương trình tạo môi trường Python riêng `.venv` và cài thư viện.
4. Khi báo cài xong, nhấn đúp `run.bat`.

Nếu Windows SmartScreen hiện cảnh báo với file BAT tự tạo, hãy chỉ chạy khi đã tải ZIP từ đúng repository này và đã xem nội dung script.

## Ba khu vực

### 1. Cào truyện

- Nhấn **MỞ CHROME THẬT** để mở Chrome cài trên máy với hồ sơ riêng của ứng dụng.
- Nhấn **MỞ WEBTOEPUB** để mở trang tiện ích [WebToEpub trên Chrome Web Store](https://chromewebstore.google.com/detail/webtoepub/akiljllkbielkidmammnifcnibaigelm).
- Cài tiện ích vào hồ sơ Chrome SẢNH TRUYỆN và ghim biểu tượng lên thanh công cụ.
- Trong Chrome, truy cập trang truyện, mở mục lục/chương đầu, nhấn biểu tượng WebToEpub rồi **Pack EPUB**.
- Đặt file tải xuống trong thư mục `data\downloads` nếu Chrome không tự dùng thư mục đó.
- Quay lại ứng dụng, chọn EPUB và chuyển sang TXT.

Ứng dụng dùng thư viện [ffreemt/epub2txt](https://github.com/ffreemt/epub2txt), có thể trích xuất nội dung theo danh sách chương. Không phải website nào cũng tương thích WebToEpub.

### 2. Dịch truyện

- Mở hoặc kéo file TXT tiếng Trung vào khung RAW.
- Chức năng **Sao chép prompt** đưa prompt và đoạn hiện tại vào clipboard.
- Mở ChatGPT, dán prompt, gửi. Khi có kết quả, copy phần bản dịch, quay lại ứng dụng và nhấn **Nhận clipboard**.
- Có thể lưu bản dịch và di chuyển qua từng đoạn.
- Để dịch cục bộ, chạy `install-local-ai.bat`, sau đó chọn mô hình Hachimi và nhấn nút dịch. Mô hình sẽ được tải khi sử dụng lần đầu.

**Giới hạn ChatGPT clipboard:** đây là quy trình bán thủ công. Ứng dụng không đăng nhập tài khoản, không tự gửi tin nhắn và không tự đọc phản hồi ChatGPT trong nền. Không cần cung cấp mật khẩu, cookie hay API key.

**Giới hạn Hachimi:** mô hình chạy CPU và tiêu thụ RAM; tốc độ phụ thuộc cấu hình máy. Nên thử với một đoạn ngắn trước khi dịch cả truyện. Bản MVP chưa có từ điển tên riêng / hồ sơ xưng hô chuyên sâu.

### 3. Tạo Audio

- Mở hoặc kéo TXT tiếng Việt vào khung nội dung.
- Chọn giọng NamMinh hoặc HoaiMy.
- Chọn tốc độ 0.75x, 1.0x, 1.25x, 1.5x hoặc 2.0x.
- Nhấn **Tạo Audio**. Kết quả được lưu thành `AU_001.mp3`, `AU_002.mp3`... trong thư mục audio của dự án.
- Chọn một AU đã hoàn thành rồi nhấn **Nghe thử / Mở MP3**.

Audio dùng [edge-tts](https://github.com/rany2/edge-tts), cần Internet. Đây không phải mô hình TTS offline. Nhận diện chương hiện dựa vào tiêu đề dạng “Chương 1”, “Chapter 1” hoặc một số mẫu tiêu đề tiếng Trung; nếu file không có tiêu đề phù hợp, toàn bộ nội dung được xem là một AU.

## Thư mục dữ liệu

Dữ liệu phát sinh được giữ trong `data\`:

- `downloads\`: EPUB tải từ Chrome.
- `chrome_profile\`: hồ sơ Chrome riêng của ứng dụng.
- `projects\`: RAW, bản dịch và MP3 theo dự án.
- `models\`: bộ nhớ đệm mô hình Hachimi.
- `logs\`, `temp\`: log và file tạm.

Các thư mục dữ liệu cá nhân đã được loại khỏi Git bằng `.gitignore`. Không đẩy truyện có bản quyền, bản dịch cá nhân, cookie trình duyệt, mật khẩu, token hoặc API key lên repository công khai.

## Khắc phục sự cố

- **Không tìm thấy Python:** cài Python 3.11 x64, bật Add Python to PATH, đóng rồi mở lại cửa sổ Explorer.
- **Thiếu thư viện:** chạy lại `install.bat`.
- **Không mở được Chrome:** cài Chrome chính thức; đóng cửa sổ Chrome SẢNH TRUYỆN đang chạy rồi thử lại.
- **Dịch Hachimi lỗi:** kiểm tra Internet khi tải mô hình lần đầu, dung lượng ổ đĩa và RAM; gửi lại nguyên văn thông báo lỗi.
- **Edge TTS lỗi:** kiểm tra Internet và thử lại; dịch vụ bên ngoài có thể thay đổi hoặc giới hạn truy cập.
- **Không kéo thả được file:** dùng nút mở file tương ứng. Kéo thả phụ thuộc `tkinterdnd2` và môi trường Windows.

## Kiểm thử

Chạy trong thư mục dự án:

```bat
.venv\Scripts\activate.bat
python -m unittest discover -s tests -v
python -m compileall -q .
```

Các kiểm thử hiện có chỉ kiểm tra một số hàm xử lý văn bản/chia chương; không thay thế kiểm thử giao diện, Chrome, tải mô hình hoặc TTS trên Windows.

## Thành phần bên thứ ba

Xem [NOTICE.md](NOTICE.md) và [LICENSE](LICENSE). Chrome, WebToEpub và trọng số mô hình không được đóng gói trong repository này; người dùng cần cài/tải riêng và tuân thủ giấy phép/điều khoản tương ứng.
