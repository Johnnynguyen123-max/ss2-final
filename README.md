# DDC Books – Bookstore App

Ứng dụng web bán sách trực tuyến xây dựng bằng Django. Tích hợp đầy đủ tính năng: giỏ hàng, đặt hàng, quản lý kho, chat real-time, AI Chatbot tư vấn sách.

---

## Tính Năng

- 🛒 Giỏ hàng và đặt hàng (checkout)
- 📦 Theo dõi đơn hàng (order tracking)
- ❤️ Danh sách sách yêu thích (wishlist)
- 🔍 Tìm kiếm gợi ý tức thì (AJAX search suggestions)
- 💬 Chat real-time giữa khách hàng và nhân viên (AJAX polling)
- 🤖 AI Chatbot tư vấn sách (Claude API)
- ⚡ Flash Sale có giới hạn thời gian
- 👨‍💼 Giao diện quản lý dành cho Staff (quản lý đơn hàng, kho sách)

---

## Yêu Cầu Hệ Thống

- Python 3.11+
- pip

---

## Hướng Dẫn Cài Đặt

### 1. Clone dự án

```bash
git clone <repo-url>
cd SS2_Final
```

### 2. Tạo và kích hoạt môi trường ảo

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Cài đặt thư viện

```bash
pip install -r requirements.txt
```

### 4. Cấu hình biến môi trường

```bash
# Sao chép file mẫu
copy .env.example .env      # Windows
cp .env.example .env        # macOS / Linux
```

Mở file `.env` và điền các giá trị:
```
SECRET_KEY=<chuỗi ký tự ngẫu nhiên dài>
DEBUG=True
ANTHROPIC_API_KEY=<API key từ console.anthropic.com>
```

### 5. Chạy migration và tạo tài khoản admin

```bash
cd bookstore_app
python manage.py migrate
python manage.py createsuperuser
```

### 6. Chạy server

```bash
python manage.py runserver
```

Truy cập: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## Cấu Trúc Dự Án

```
SS2_Final/
├── .env.example        # Mẫu cấu hình biến môi trường
├── .gitignore
├── requirements.txt
└── bookstore_app/
    ├── manage.py
    ├── bookstore_app/  # Cấu hình dự án Django
    │   ├── settings.py
    │   └── urls.py
    └── app/            # Django app chính
        ├── models.py
        ├── views/      # Views được tách theo tính năng
        ├── templates/
        └── static/
```

---

## Phân Quyền

| Vai trò | Quyền |
|---------|-------|
| Khách (Anonymous) | Xem sách, tìm kiếm |
| Khách hàng (User) | Giỏ hàng, đặt hàng, chat, wishlist |
| Nhân viên (Staff) | Quản lý đơn hàng, kho sách, flash sale, chat với khách |
| Admin (Superuser) | Toàn quyền |

> **Tạo tài khoản Staff**: Vào Django Admin → Users → Chọn user → Groups → Thêm vào group **Staff**

---

## Giấy Phép

© 2026 DDC Books Project. Designed by Cường – Đông – Đăng.