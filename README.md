# SẢNH TRUYỆN

**Ứng dụng desktop Windows** để xử lý tiểu thuyết theo quy trình:

**Chrome thật + WebToEpub → EPUB → TXT → Dịch Trung–Việt → Story TTS API riêng → MP3 theo chương.**

> Phiên bản hiện tại: **0.2.0 MVP**. Đây là bản mã nguồn thử nghiệm, chưa phải bản EXE cài đặt một lần. Cần kiểm thử trên máy Windows thực tế trước khi dùng với bộ truyện dài.

## Tải ZIP từ GitHub

**Tải ZIP trực tiếp:** [SANH-TRUYEN-main.zip](https://github.com/hantuyet425/SANH-TRUYEN/archive/refs/heads/main.zip).

Hoặc tải thủ công:
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
- Nhấn **Gửi tạo Audio**. SẢNH TRUYỆN gửi mỗi chương (một AU) sang [Story-TTS-API](https://github.com/hantuyet425/Story-TTS-API). Dịch vụ chia AU thành các đoạn tối đa 5.000 ký tự, mặc định tổng hợp tối đa 100 đoạn song song, ghép theo đúng thứ tự rồi trả một MP3 hoàn chỉnh về thư mục audio của dự án.
- Chọn một AU đã hoàn thành rồi nhấn **Nghe thử / Mở MP3**.

Story-TTS-API dùng Edge TTS, cần Internet; đây không phải TTS offline. Nhận diện chương hiện dựa vào tiêu đề dạng “Chương 1”, “Chapter 1” hoặc một số mẫu tiêu đề tiếng Trung; nếu file không có tiêu đề phù hợp, toàn bộ nội dung được xem là một AU.

## Kết nối Story-TTS-API

Audio được xử lý bởi repository riêng, không chạy bộ tổng hợp giọng đọc trong SẢNH TRUYỆN.

### Chạy API trên cùng máy Windows

1. Tải [Story-TTS-API ZIP](https://github.com/hantuyet425/Story-TTS-API/archive/refs/heads/main.zip) và giải nén, ví dụ vào `D:\STORY-TTS-API`.
2. Cài Python 3.11 64-bit nếu chưa có.
3. Mở thư mục API và chạy `install-windows.bat`.
4. Cuối quá trình, cửa sổ sẽ hiện API key riêng của máy. Sao chép key này; nếu quên, chạy `show-api-key.bat` trong thư mục API để xem lại.
5. Chạy `run-windows.bat` và giữ cửa sổ đó mở trong khi tạo audio.
6. Trong SẢNH TRUYỆN → Tạo Audio, nhập API URL `http://127.0.0.1:8000`, dán API key rồi nhấn **Lưu & Kiểm tra**.

API cấp mã tác vụ, cung cấp tiến độ số đoạn đã hoàn tất và trả liên kết MP3 khi xong. SẢNH TRUYỆN tải MP3 về máy và giữ mã AU theo chương.

Nếu triển khai Story-TTS-API trên Render hoặc máy chủ riêng, thay URL localhost bằng URL máy chủ và dùng API key do máy chủ cấp. Không commit API key vào GitHub, không đưa key vào README hoặc ảnh chụp công khai.

Mặc định API chia AU thành đoạn tối đa 5.000 ký tự và xử lý tối đa 100 đoạn đồng thời. Mức này khá cao: nếu Edge TTS trả lỗi 403/429, giảm `MAX_PARALLEL_CHUNKS` trong file `.env` của Story-TTS-API xuống 20, 10, 4, 2 hoặc 1 rồi khởi động lại API.

## Thư mục dữ liệu

Dữ liệu phát sinh được giữ trong `data\`:

- `downloads\`: EPUB tải từ Chrome.
- `chrome_profile\`: hồ sơ Chrome riêng của ứng dụng.
- `projects\`: RAW, bản dịch và MP3 theo dự án.
- `models\`: bộ nhớ đệm mô hình Hachimi.
- `logs\`, `temp\`: log và file tạm.
- `settings.json`: URL/API key của Story-TTS-API, chỉ lưu cục bộ và được `.gitignore` loại khỏi Git.

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
