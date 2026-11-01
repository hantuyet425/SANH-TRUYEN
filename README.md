# SẢNH TRUYỆN

Ứng dụng desktop Windows hỗ trợ quy trình xử lý tiểu thuyết:

**Chrome + WebToEpub → EPUB → TXT → dịch Trung–Việt → MP3 theo chương.**

## Tải ứng dụng

[**Tải SẢNH TRUYỆN 0.1.0 MVP (.zip)**](https://github.com/hantuyet425/SANH-TRUYEN/raw/refs/heads/main/SANH-TRUYEN-0.1.0-MVP.zip)

Hoặc mở file `SANH-TRUYEN-0.1.0-MVP.zip` trong danh sách tệp của repository và chọn Download raw file.

## Cài đặt nhanh (Windows 10/11)

1. Cài **Python 3.11 64-bit** và đánh dấu Add Python to PATH.
2. Cài **Google Chrome**.
3. Tải ZIP ở trên, giải nén vào thư mục dễ nhớ (ví dụ `D:\SANH_TRUYEN`).
4. Chạy `install.bat` và đợi cài thư viện hoàn tất.
5. Chạy `run.bat` để mở phần mềm.

Muốn sử dụng HachimiMT-60 cục bộ trên CPU, chạy thêm `install-local-ai.bat`. Mô hình sẽ tải về khi dùng lần đầu.

## Ba khu vực chức năng

- **Cào truyện:** mở Chrome thật bằng hồ sơ riêng, dùng tiện ích WebToEpub để đóng gói EPUB, sau đó chuyển EPUB thành TXT.
- **Dịch truyện:** nhận file RAW, dịch bằng ChatGPT qua clipboard (thao tác thủ công) hoặc HachimiMT-60 chạy CPU cục bộ.
- **Tạo Audio:** dùng Edge TTS với giọng NamMinh/HoaiMy, tốc độ 0.75x–2.0x, xuất MP3 theo từng chương/AU.

## Lưu ý quan trọng

- Đây là bản **0.1.0 MVP**, chưa phải bản ổn định cuối cùng; cần kiểm thử thực tế trên Windows.
- ChatGPT clipboard không tự đăng nhập, tự gửi hay đọc phản hồi trong nền.
- HachimiMT-60 cần tải mô hình lần đầu và tiêu thụ RAM/CPU.
- Edge TTS cần Internet; đây không phải TTS offline.
- Không đưa truyện cá nhân, mật khẩu, cookie, token hoặc API key lên repository công khai.
- Chỉ thu thập và xử lý nội dung mà bạn có quyền truy cập/sử dụng; không vượt paywall, DRM hay cơ chế bảo vệ truy cập.

## Tài liệu

Mã nguồn, hướng dẫn chi tiết, phụ thuộc và giấy phép của bản MVP đều nằm trong ZIP. Xem thêm [GitHub repository](https://github.com/hantuyet425/SANH-TRUYEN).
