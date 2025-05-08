FROM python:3.11-slim

WORKDIR /app

# Cài đặt dependencies
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
EXPOSE 8000

# Command to run
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]