FROM golang:1.23-alpine

WORKDIR /app

# Copy go mod and sum files
COPY go.mod go.sum ./

# Download all dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN go build -o main ./cmd/server

# Expose port
EXPOSE 8000

# Run the executable
CMD ["./main"]