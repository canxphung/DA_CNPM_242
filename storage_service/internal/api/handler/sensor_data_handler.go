package handlers

import (
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"

	"storage-service/internal/models"
	"storage-service/internal/service"
)

type SensorDataHandler struct {
	service *service.StorageService
}

// NewSensorDataHandler tạo handler mới
func NewSensorDataHandler(service *service.StorageService) *SensorDataHandler {
	return &SensorDataHandler{
		service: service,
	}
}

// StoreSensorReading xử lý POST một bản ghi
func (h *SensorDataHandler) StoreSensorReading(c *gin.Context) {
	var reading models.SensorReading

	if err := c.BindJSON(&reading); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body: " + err.Error()})
		return
	}

	err := h.service.StoreSensorReading(c.Request.Context(), &reading)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to store reading: " + err.Error()})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"status": "success"})
}

// StoreBatchReadings xử lý POST nhiều bản ghi
func (h *SensorDataHandler) StoreBatchReadings(c *gin.Context) {
	var batch models.BatchReadings

	if err := c.BindJSON(&batch); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body: " + err.Error()})
		return
	}

	err := h.service.StoreBatchReadings(c.Request.Context(), &batch)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to store batch readings: " + err.Error()})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"status": "success", "count": len(batch.Readings)})
}

// QuerySensorData xử lý GET dữ liệu cảm biến
func (h *SensorDataHandler) QuerySensorData(c *gin.Context) {
	// Xử lý tham số truy vấn
	params := parseQueryParams(c)

	// Truy vấn dữ liệu
	readings, err := h.service.QuerySensorData(c.Request.Context(), params)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to query data: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  "success",
		"count":   len(readings),
		"results": readings,
	})
}

// GetSensorStats xử lý GET thống kê
func (h *SensorDataHandler) GetSensorStats(c *gin.Context) {
	sensorType := models.SensorType(c.Param("type"))

	// Validate loại cảm biến
	switch sensorType {
	case models.LightSensor, models.TempHumiditySensor, models.SoilMoistureSensor:
		// Valid
	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid sensor type"})
		return
	}

	// Lấy tham số thời gian
	startTimeStr := c.DefaultQuery("start_time", "")
	endTimeStr := c.DefaultQuery("end_time", "")

	startTime := time.Now().Add(-24 * time.Hour)
	endTime := time.Now()

	if startTimeStr != "" {
		if t, err := time.Parse(time.RFC3339, startTimeStr); err == nil {
			startTime = t
		}
	}

	if endTimeStr != "" {
		if t, err := time.Parse(time.RFC3339, endTimeStr); err == nil {
			endTime = t
		}
	}

	// Lấy thống kê
	stats, err := h.service.GetSensorDataStats(c.Request.Context(), sensorType, startTime, endTime)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get sensor stats: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "success",
		"type":   sensorType,
		"stats":  stats,
	})
}

// parseQueryParams chuyển đổi từ HTTP query params sang struct QueryParams
func parseQueryParams(c *gin.Context) *models.QueryParams {
	startTimeStr := c.DefaultQuery("start_time", "")
	endTimeStr := c.DefaultQuery("end_time", "")

	startTime := time.Now().Add(-24 * time.Hour)
	endTime := time.Now()

	if startTimeStr != "" {
		if t, err := time.Parse(time.RFC3339, startTimeStr); err == nil {
			startTime = t
		}
	}

	if endTimeStr != "" {
		if t, err := time.Parse(time.RFC3339, endTimeStr); err == nil {
			endTime = t
		}
	}

	sensorIDs := c.QueryArray("sensor_id")

	var sensorTypes []models.SensorType
	for _, t := range c.QueryArray("sensor_type") {
		sensorTypes = append(sensorTypes, models.SensorType(t))
	}

	locations := c.QueryArray("location")

	limit := 100
	if l := c.Query("limit"); l != "" {
		if parsed, err := parseInt(l, 1, 1000); err == nil {
			limit = parsed
		}
	}

	offset := 0
	if o := c.Query("offset"); o != "" {
		if parsed, err := parseInt(o, 0, 10000); err == nil {
			offset = parsed
		}
	}

	aggregation := c.DefaultQuery("aggregation", "")
	interval := c.DefaultQuery("interval", "")

	return &models.QueryParams{
		StartTime:   startTime,
		EndTime:     endTime,
		SensorIDs:   sensorIDs,
		SensorTypes: sensorTypes,
		Locations:   locations,
		Limit:       limit,
		Offset:      offset,
		Aggregation: aggregation,
		Interval:    interval,
	}
}

// parseInt chuyển đổi string sang int với giới hạn
func parseInt(val string, min, max int) (int, error) {
	var result int
	_, err := fmt.Sscanf(val, "%d", &result)
	if err != nil {
		return 0, err
	}

	if result < min {
		result = min
	}
	if result > max {
		result = max
	}

	return result, nil
}
