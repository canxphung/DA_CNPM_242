# Hướng Dẫn Cài Đặt & Chạy Hệ Thống Web Quản Lý Nhà Kính

## Giới thiệu

Hệ thống Web Quản Lý Nhà Kính là một nền tảng nông nghiệp thông minh được phát triển theo kiến trúc microservices. Mục tiêu của hệ thống là hỗ trợ người nông dân và tổ chức nông nghiệp trong việc giám sát và điều khiển điều kiện môi trường trồng trọt như nhiệt độ, độ ẩm, ánh sáng và độ ẩm đất. 

Các thành phần chính của hệ thống bao gồm API Gateway, dịch vụ xác thực người dùng, dịch vụ xử lý dữ liệu cảm biến, dịch vụ trí tuệ nhân tạo hỗ trợ phân tích môi trường và tư vấn chăm sóc cây trồng, và giao diện người dùng được phát triển bằng React. 

Mỗi thành phần được triển khai bằng một ngôn ngữ lập trình phù hợp (Go, Node.js, Python, JavaScript) và giao tiếp với nhau qua API chuẩn REST hoặc hàng đợi thông điệp. Hệ thống có khả năng mở rộng cao, dễ bảo trì và có thể triển khai trên nền tảng đám mây hoặc máy chủ cục bộ.

---

## Yêu cầu hệ thống

- Git
- Python 3.10+
- Node.js v18+
- Go 1.21+
- MongoDB
- Redis
- Firebase Realtime Database (đã cấu hình sẵn)

## Kiến trúc hệ thống Web

Hệ thống được chia làm 5 thành phần chính:

1. **API Gateway** - Viết bằng Go
2. **User & Authentication Service** - Viết bằng Node.js
3. **Core Operations Service** - Viết bằng Python
4. **Greenhouse AI Service** - Viết bằng Python
5. **Frontend Web (UI)** - Viết bằng React + Vite

---

## 1. Cài đặt & chạy API Gateway (Go)

### Cấu trúc thư mục:
```
api-gateway/
├── cmd/
│   └── server/
│       └── main.go
├── go.mod
└── ...
```

### Cài đặt:
```bash
cd api-gateway
# (Tuỳ chọn) cập nhật module
go mod tidy
```

### Chạy server:
```bash
go run ./cmd/server/main.go
```

---

## 2. Cài đặt & chạy User & Authentication Service (Node.js)

### Cấu trúc thư mục:
```
auth-service/
├── src/
├── package.json
└── ...
```

### Cài đặt:
```bash
cd auth-service
npm install
```

### Chạy server:
```bash
npm run start
```

---

## 3. Cài đặt & chạy Core Operations Service (Python)

### Cấu trúc thư mục:
```
core-operations/
├── main.py
├── requirements.txt
└── ...
```

### Cài đặt môi trường ảo và thư viện:
```bash
cd core-operations
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Chạy server:
```bash
python main.py
```

---

## 4. Cài đặt & chạy Greenhouse AI Service (Python)

### Cấu trúc thư mục:
```
ai-service/
├── main.py
├── requirements.txt
└── ...
```

### Cài đặt môi trường ảo và thư viện:
```bash
cd ai-service
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Chạy server:
```bash
python main.py
```

---

## 5. Cài đặt & chạy Frontend Web (React + Vite)

### Cấu trúc thư mục:
```
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    └── main.jsx
```

### Cài đặt:
```bash
cd frontend
npm install
```

### Chạy frontend:
```bash
npm run dev
```

> Truy cập địa chỉ hiển thị (mặc định http://localhost:5173/) để kiểm tra giao diện web.

---

## Tổng kết

| Service                  | Ngôn ngữ     | Câu lệnh chạy                         |
|-------------------------|--------------|--------------------------------------|
| API Gateway             | Go           | `go run ./cmd/server/main.go`        |
| Auth Service            | Node.js      | `npm run start`                      |
| Core Operations Service | Python       | `python main.py`                     |
| AI Service              | Python       | `python main.py`                     |
| Frontend UI             | React + Vite | `npm run dev`                        |

> 💡 Đảm bảo rằng MongoDB, Redis và Firebase đều đã được cấu hình trước khi chạy các service.
