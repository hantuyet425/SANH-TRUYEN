# SẢNH TRUYỆN

Ứng dụng desktop Windows hỗ trợ quy trình xử lý tiểu thuyết:

**Chrome + WebToEpub → EPUB → TXT → dịch Trung–Việt → MP3 theo chương.**

## Trạng thái dự án

Repository này là trang dự án công khai của **SẢNH TRUYỆN**. Bản mã nguồn đang ở giai đoạn MVP; gói ZIP thử nghiệm chưa được phát hành trực tiếp trong GitHub.

## Mục tiêu chức năng

- **Cào truyện:** mở Chrome thật bằng hồ sơ riêng, dùng tiện ích WebToEpub để đóng gói EPUB, sau đó chuyển EPUB thành TXT.
- **Dịch truyện:** nhận file RAW, dịch bằng ChatGPT qua clipboard (thao tác thủ công) hoặc HachimiMT-60 chạy CPU cục bộ.
- **Tạo Audio:** dùng Edge TTS với giọng NamMinh/HoaiMy, tốc độ 0.75x–2.0x, xuất MP3 theo từng chương/AU.

## Môi trường dự kiến

- Windows 10/11
- Python 3.11 64-bit
- Google Chrome
- Edge TTS cần Internet; đây không phải TTS offline.
- HachimiMT-60 cần tải mô hình lần đầu và tiêu thụ RAM/CPU.
- ChatGPT clipboard không tự đăng nhập, tự gửi hay đọc phản hồi trong nền.

## An toàn và quyền sử dụng

- Không đưa truyện cá nhân, mật khẩu, cookie, token hoặc API key lên repository công khai.
- Chỉ thu thập và xử lý nội dung mà bạn có quyền truy cập/sử dụng; không vượt paywall, DRM hay cơ chế bảo vệ truy cập.

## Tải bản MVP hiện có

Bản ZIP thử nghiệm được đính kèm trong cuộc trò chuyện ChatGPT đã tạo ra bản này. Repository hiện chưa chứa file ZIP để tải trực tiếp từ GitHub.

