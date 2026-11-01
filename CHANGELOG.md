# Nhật ký thay đổi

## 0.2.0-mvp
- Tách phần tổng hợp giọng đọc thành dịch vụ HTTP riêng trong repository Story-TTS-API.
- Gửi từng chương/AU đến API, theo dõi tiến độ phân đoạn và tải MP3 hoàn chỉnh về.
- Không còn cài Edge-TTS trực tiếp trong SẢNH TRUYỆN.
- API mặc định chia AU thành đoạn tối đa 5.000 ký tự, xử lý 4 đoạn đồng thời và ghép lại theo thứ tự nguồn.

## 0.1.0-mvp
- Tạo giao diện desktop ba khu vực Cào truyện / Dịch truyện / Tạo Audio.
- Mở Google Chrome thật với hồ sơ và thư mục EPUB riêng.
- Chuyển EPUB sang TXT bằng epub2txt.
- Dịch từng đoạn bằng clipboard ChatGPT hoặc HachimiMT CTranslate2 INT8 trên CPU.
- Tạo MP3 theo chương bằng Edge TTS, hai giọng NamMinh/HoaiMy và năm mức tốc độ (luồng audio cục bộ cũ).
- Lưu dữ liệu theo thư mục dự án.
