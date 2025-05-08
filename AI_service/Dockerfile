FROM python:3.11-slim

WORKDIR /app

# Cài đặt các dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Tạo thư mục logs nếu không tồn tại
RUN mkdir -p logs

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Command to run
CMD ["python", "main.py", "--mode", "api"]