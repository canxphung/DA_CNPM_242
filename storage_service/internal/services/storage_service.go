package service

import (
	"context"
	"errors"
	"time"

	"storage-service/internal/models"
	"storage-service/internal/repository/influxdb"
)

type StorageService struct {
	repo *influxdb.Repository
}

// NewStorageService tạo service mới
func NewStorageService(repo *influxdb.Repository) *StorageService {
	return &StorageService{
		repo: repo,
	}
}

// StoreSensorReading lưu một bản ghi
func (s *StorageService) StoreSensorReading(ctx context.Context, reading *models.SensorReading) error {
	// Validate
	if reading.SensorID == "" {
		return errors.New("sensor ID is required")
	}

	// Đặt thời gian nếu không có
	if reading.Timestamp.IsZero() {
		reading.Timestamp = time.Now()
	}

	// Đảm bảo có map values
	if reading.Values == nil {
		reading.Values = make(map[string]float64)
	}

	// Validate các giá trị theo loại cảm biến
	switch reading.SensorType {
	case models.LightSensor:
		// Kiểm tra có giá trị ánh sáng không
		if _, exists := reading.Values["light_intensity"]; !exists {
			return errors.New("light sensor reading must include light_intensity value")
		}
	case models.TempHumiditySensor:
		// Kiểm tra có giá trị nhiệt độ và độ ẩm không
		if _, exists := reading.Values["temperature"]; !exists {
			return errors.New("DHT20 sensor reading must include temperature value")
		}
		if _, exists := reading.Values["humidity"]; !exists {
			return errors.New("DHT20 sensor reading must include humidity value")
		}
	case models.SoilMoistureSensor:
		// Kiểm tra có giá trị độ ẩm đất không
		if _, exists := reading.Values["moisture"]; !exists {
			return errors.New("soil moisture sensor reading must include moisture value")
		}
	default:
		return errors.New("unsupported sensor type")
	}

	// Lưu vào repository
	return s.repo.StoreSensorReading(ctx, reading)
}

// StoreBatchReadings lưu nhiều bản ghi
func (s *StorageService) StoreBatchReadings(ctx context.Context, batch *models.BatchReadings) error {
	// Validate từng bản ghi
	for i, reading := range batch.Readings {
		reading := reading // Tạo bản sao để tránh vấn đề với con trỏ trong loop
		if err := s.StoreSensorReading(ctx, &reading); err != nil {
			return errors.New("validation error in reading " + string(i) + ": " + err.Error())
		}
		batch.Readings[i] = reading // Cập nhật lại trong batch
	}

	// Lưu hàng loạt
	return s.repo.StoreBatchReadings(ctx, batch)
}

// QuerySensorData truy vấn dữ liệu
func (s *StorageService) QuerySensorData(ctx context.Context, params *models.QueryParams) ([]models.SensorReading, error) {
	// Validate
	if params.StartTime.IsZero() {
		// Mặc định 24 giờ trước
		params.StartTime = time.Now().Add(-24 * time.Hour)
	}

	if params.EndTime.IsZero() {
		// Mặc định hiện tại
		params.EndTime = time.Now()
	}

	// Truy vấn repository
	return s.repo.QuerySensorData(ctx, params)
}

// GetSensorDataStats trả về thống kê cho loại cảm biến
func (s *StorageService) GetSensorDataStats(ctx context.Context, sensorType models.SensorType, startTime, endTime time.Time) (map[string]float64, error) {
	params := &models.QueryParams{
		StartTime:   startTime,
		EndTime:     endTime,
		SensorTypes: []models.SensorType{sensorType},
		Aggregation: "mean",
		Interval:    "1d",
	}

	readings, err := s.repo.QuerySensorData(ctx, params)
	if err != nil {
		return nil, err
	}

	stats := make(map[string]float64)

	// Tính giá trị trung bình của mỗi loại dữ liệu
	valueCounts := make(map[string]int)

	for _, reading := range readings {
		for key, value := range reading.Values {
			stats[key] += value
			valueCounts[key]++
		}
	}

	// Tính trung bình
	for key, sum := range stats {
		if count := valueCounts[key]; count > 0 {
			stats[key] = sum / float64(count)
		}
	}

	return stats, nil
}
