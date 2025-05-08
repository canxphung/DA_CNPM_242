# Hướng dẫn sử dụng Docker cho dự án DA_CNPM_242

## Giới thiệu

Dự án DA_CNPM_242 là một hệ thống IoT với nhiều microservices. Dự án bao gồm các thành phần sau:

1. **AI_service**: Dịch vụ AI phân tích dữ liệu và đưa ra khuyến nghị (Python, FastAPI)
2. **api_gateway**: Gateway API cho toàn bộ hệ thống (Golang)
3. **data_processor**: Dịch vụ xử lý dữ liệu từ cảm biến (Python, FastAPI)
4. **user_auth_service**: Dịch vụ xác thực người dùng (Node.js, Express)

## Cài đặt và Chạy

### Yêu cầu

- Docker
- Docker Compose

### Các bước chạy

1. Đảm bảo bạn đã có tất cả các file .env cần thiết trong mỗi thư mục service
2. Chạy toàn bộ hệ thống:

```bash
docker-compose up -d
```

3. Để dừng hệ thống:

```bash
docker-compose down
```

## Cổng truy cập

- **API Gateway**: http://localhost:8000
- **AI Service**: http://localhost:8080
- **Data Processor**: http://localhost:8001
- **User Auth Service**: http://localhost:3000

## Các dịch vụ hỗ trợ

- **Redis**: localhost:6379
- **PostgreSQL**: localhost:5432
- **MongoDB**: localhost:27017
- **Firebase Emulator**: localhost:9000, localhost:9099

## Volumes

Các dữ liệu quan trọng sẽ được lưu trữ trong Docker volumes:

- **ai_service_data**: Dữ liệu từ AI Service
- **data_processor_logs**: Logs từ Data Processor
- **redis_data**: Dữ liệu Redis
- **postgres_data**: Dữ liệu PostgreSQL
- **mongodb_data**: Dữ liệu MongoDB

## Khắc phục sự cố

### Logs

Để xem logs của một dịch vụ cụ thể:

```bash
docker-compose logs -f <tên_service>
```

Ví dụ: `docker-compose logs -f ai_service`

### Khởi động lại một dịch vụ

```bash
docker-compose restart <tên_service>
```

### Xây dựng lại một dịch vụ

Nếu bạn thay đổi Dockerfile hoặc requirements:

```bash
docker-compose build <tên_service>
docker-compose up -d <tên_service>
```

## Môi trường phát triển

Để phát triển, bạn có thể chạy một dịch vụ cụ thể mà không cần Docker:

```bash
# Chạy các dịch vụ hỗ trợ (Redis, PostgreSQL, MongoDB)
docker-compose up -d redis postgres mongodb

# Phát triển một dịch vụ cụ thể trên máy local
cd <thư_mục_service>
# Cài đặt dependencies và chạy service
```