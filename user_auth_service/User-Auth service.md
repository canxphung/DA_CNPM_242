# API Dịch vụ Người dùng & Xác thực

Một dịch vụ backend mạnh mẽ để quản lý người dùng, xác thực và phân quyền chi tiết (Quyền & Vai trò). Được xây dựng bằng Node.js, Express.js và MongoDB.

## Tính năng

*   **Quản lý Người dùng:**
    *   Các thao tác CRUD (Tạo, Đọc, Cập nhật, Xóa) cho người dùng.
    *   Kích hoạt/Vô hiệu hóa tài khoản người dùng.
    *   Chức năng thay đổi mật khẩu.
*   **Xác thực:**
    *   Đăng ký và đăng nhập người dùng an toàn.
    *   Xác thực dựa trên JWT (Access Token & Refresh Token).
    *   Đăng xuất (vô hiệu hóa refresh token hiện tại).
    *   Đăng xuất khỏi tất cả thiết bị (vô hiệu hóa tất cả refresh token của người dùng).
    *   Lấy thông tin hồ sơ người dùng đã xác thực hiện tại (`/me`).
*   **Phân quyền (RBAC - Role-Based Access Control):**
    *   **Quyền (Permissions):** Định nghĩa các quyền chi tiết (ví dụ: `user:create`, `role:read`).
    *   **Vai trò (Roles):** Nhóm các quyền thành vai trò (ví dụ: `admin`, `manager`, `user`).
    *   Gán vai trò cho người dùng.
    *   Gán quyền tùy chỉnh (ad-hoc) trực tiếp cho người dùng.
    *   Middleware để kiểm tra vai trò và quyền trên các route.
    *   Hỗ trợ hành động `manage` (quyền giống superuser cho một tài nguyên).
*   **Tài liệu API:**
    *   Tài liệu Swagger/OpenAPI có sẵn tại `/api/v1/docs`.
*   **Giám sát & Trạng thái (Monitoring & Health):**
    *   Endpoint `/health` để kiểm tra trạng thái dịch vụ.
    *   Endpoint `/system` để xem thông tin hệ thống chi tiết (Chỉ dành cho Admin).
    *   `express-actuator` cho các endpoint quản lý phổ biến (ví dụ: `/management/info`, `/management/health`).
*   **Bảo mật:**
    *   Mã hóa mật khẩu (bcrypt).
    *   Helmet để bảo vệ HTTP headers.
    *   Cấu hình CORS.
    *   Giới hạn tỷ lệ truy cập (Rate limiting) và làm chậm yêu cầu.
    *   Xác thực dữ liệu đầu vào cho các yêu cầu API.
*   **Cơ sở hạ tầng:**
    *   MongoDB để lưu trữ dữ liệu (sử dụng Mongoose).
    *   Tích hợp Redis (có sẵn, ví dụ: để đưa token vào danh sách đen, caching - mặc dù việc quản lý refresh token hiện tại dựa trên DB).
    *   Ghi log có cấu trúc với Winston.
    *   Cấu hình dựa trên môi trường (`.env`).
    *   Seed dữ liệu ban đầu cho người dùng, quyền và vai trò.
*   **Sẵn sàng cho Microservice (Tùy chọn):**
    *   Tích hợp với Service Registry.
    *   Tích hợp với API Gateway.
    *   (Có thể bật/tắt các tính năng này qua cấu hình).

## Điều kiện tiên quyết

*   Node.js (phiên bản 14.x trở lên được khuyến nghị)
*   npm hoặc yarn
*   Một instance MongoDB đang chạy
*   Một instance Redis đang chạy (tùy chọn, nhưng đã được cấu hình)

## Bắt đầu

1.  **Clone repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Cài đặt các dependency (gói phụ thuộc):**
    ```bash
    npm install
    # hoặc
    yarn install
    ```

3.  **Thiết lập Biến Môi trường:**
    Tạo một tệp `.env` trong thư mục gốc bằng cách sao chép tệp `.env.example` (nếu có, nếu không thì tạo mới).
    Điền các biến môi trường cần thiết:

    ```env
    NODE_ENV=development
    HOST=localhost
    PORT=3001
    API_PREFIX=/api/v1

    # JWT
    JWT_SECRET=your-very-strong-jwt-secret
    JWT_EXPIRATION=1d
    JWT_REFRESH_EXPIRATION=7d

    # Database
    MONGODB_URI=mongodb://localhost:27017/user-auth-service
    REDIS_URI=redis://localhost:6379

    # CORS (danh sách các origin được phép, cách nhau bởi dấu phẩy, hoặc * cho tất cả)
    CORS_ORIGIN=http://localhost:3000

    # Tích hợp Microservice tùy chọn
    API_GATEWAY_ENABLED=false
    API_GATEWAY_URL=http://localhost:8000
    SERVICE_REGISTRY_ENABLED=false
    SERVICE_REGISTRY_URL=http://localhost:3000

    # Giới hạn tỷ lệ truy cập (Rate Limiting)
    RATE_LIMIT_WINDOW_MS=900000 # 15 phút
    RATE_LIMIT_MAX=100
    ```
    Đối với môi trường production, tạo một tệp `.env.production`.

4.  **Seed (khởi tạo) dữ liệu cho database (Tùy chọn nhưng được khuyến nghị cho thiết lập ban đầu):**
    Dịch vụ bao gồm các script để seed người dùng, quyền và vai trò ban đầu.

    *   **Seed người dùng cơ bản (admin, manager, user):**
        ```bash
        npm run seed:users
        # hoặc
        yarn seed:users
        ```
        (Lệnh này có thể cần được thêm vào `scripts` trong `package.json`: `"seed:users": "node src/infrastructure/database/seed.js"`)

    *   **Seed quyền và vai trò, và gán vai trò cho người dùng đã seed:**
        ```bash
        npm run seed:permissions
        # hoặc
        yarn seed:permissions
        ```
        (Lệnh này có thể cần được thêm vào `scripts` trong `package.json`: `"seed:permissions": "node src/infrastructure/database/seed-permissions.js"`)

5.  **Chạy ứng dụng:**
    *   **Chế độ development (với nodemon nếu được cấu hình):**
        ```bash
        npm run dev
        # hoặc
        yarn dev
        ```
    *   **Chế độ production:**
        ```bash
        npm start
        # hoặc
        yarn start
        ```
        (Các lệnh này giả định `scripts` trong `package.json` như:
        `"start": "node src/server.js"`,
        `"dev": "nodemon src/server.js"`)

6.  **Truy cập API:**
    Dịch vụ sẽ chạy tại `http://localhost:3001` (hoặc `HOST` và `PORT` bạn đã cấu hình).
    Các API endpoint có tiền tố là `/api/v1` (hoặc `API_PREFIX` bạn đã cấu hình).
    Tài liệu API (Swagger UI) có sẵn tại `http://localhost:3001/api/v1/docs`.

## Các API Endpoint

Dịch vụ cung cấp các nhóm tài nguyên chính sau:

*   **Xác thực:** `/api/v1/auth`
    *   `POST /login`: Đăng nhập người dùng.
    *   `POST /register`: Đăng ký người dùng.
    *   `POST /refresh-token`: Lấy access token mới.
    *   `POST /logout`: Đăng xuất phiên hiện tại.
    *   `POST /logout-all`: Đăng xuất khỏi tất cả thiết bị.
    *   `GET /me`: Lấy thông tin người dùng đã xác thực hiện tại.
*   **Người dùng (Users):** `/api/v1/users`
    *   Các thao tác CRUD cho người dùng.
    *   Các endpoint để thay đổi mật khẩu, kích hoạt/vô hiệu hóa.
    *   Quản lý vai trò và quyền tùy chỉnh của người dùng (ví dụ: `/api/v1/users/:userId/roles`).
*   **Vai trò (Roles):** `/api/v1/roles`
    *   Các thao tác CRUD cho vai trò.
    *   Quản lý các quyền liên quan đến một vai trò (ví dụ: `/api/v1/roles/:id/permissions`).
*   **Quyền (Permissions):** `/api/v1/permissions`
    *   Các thao tác CRUD cho quyền.
*   **Giám sát (Monitoring):** `/api/v1/monitoring`
    *   `GET /health`: Kiểm tra trạng thái dịch vụ.
    *   `GET /system`: Thông tin hệ thống (chỉ admin).
    *   Các endpoint Actuator dưới `/management/` (ví dụ: `/management/info`, `/management/health`).

Để biết thông số kỹ thuật API chi tiết, định dạng yêu cầu/phản hồi và thử nghiệm các endpoint, vui lòng truy cập **Tài liệu Swagger** tại `/api/v1/docs`.

## Cấu hình

Cấu hình được quản lý thông qua các biến môi trường. Các biến chính bao gồm:

*   `NODE_ENV`: Môi trường ứng dụng (`development`, `production`).
*   `PORT`: Cổng mà server lắng nghe.
*   `MONGODB_URI`: Chuỗi kết nối MongoDB.
*   `JWT_SECRET`: Khóa bí mật để ký JWT.
*   `CORS_ORIGIN`: Các origin được phép cho CORS.
*   ...và các biến khác (xem phần `.env` ở trên).

## Giám sát

*   **Kiểm tra Trạng thái (Health Check):** `GET /api/v1/monitoring/health`
*   **Thông tin Hệ thống (System Info):** `GET /api/v1/monitoring/system` (yêu cầu quyền admin: quyền `system:read`)
*   **Các Endpoint Actuator:** Có sẵn dưới `/management/` (ví dụ: `/management/info`, `/management/prometheus`, `/management/health`).


## Công nghệ sử dụng

*   **Backend:** Node.js, Express.js
*   **Database:** MongoDB (với Mongoose ODM), Redis
*   **Xác thực:** JSON Web Tokens (JWT)
*   **Mã hóa Mật khẩu:** bcrypt
*   **Tài liệu API:** Swagger (OpenAPI) với `swagger-jsdoc` và `swagger-ui-express`
*   **Logging:** Winston
*   **Validation:** `express-validator`
*   **Bảo mật:** Helmet, CORS
*   **Giám sát:** `express-actuator`, `express-status-monitor`
*   **Giới hạn truy cập:** `express-rate-limit`, `express-slow-down`
*   **Tiện ích:** `dotenv`, `compression`, `morgan` (để ghi log HTTP qua Winston)

