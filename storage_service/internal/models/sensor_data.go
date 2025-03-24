package models

import (
	"time"
)

// SensorType định nghĩa các loại cảm biến
type SensorType string

const (
	LightSensor        SensorType = "light"
	TempHumiditySensor SensorType = "dht20"
	SoilMoistureSensor SensorType = "soil_moisture"
)

// SensorReading chứa thông tin từ một lần đọc cảm biến
type SensorReading struct {
	Timestamp  time.Time          `json:"timestamp"`
	SensorID   string             `json:"sensor_id"`
	SensorType SensorType         `json:"sensor_type"`
	Location   string             `json:"location"`
	Values     map[string]float64 `json:"values"`
	Tags       map[string]string  `json:"tags,omitempty"`
}

// BatchReadings chứa nhiều bản ghi để gửi hàng loạt
type BatchReadings struct {
	Readings []SensorReading `json:"readings"`
}

// QueryParams định nghĩa các tham số truy vấn
type QueryParams struct {
	StartTime   time.Time    `json:"start_time"`
	EndTime     time.Time    `json:"end_time"`
	SensorIDs   []string     `json:"sensor_ids,omitempty"`
	SensorTypes []SensorType `json:"sensor_types,omitempty"`
	Locations   []string     `json:"locations,omitempty"`
	Limit       int          `json:"limit,omitempty"`
	Offset      int          `json:"offset,omitempty"`
	Aggregation string       `json:"aggregation,omitempty"` // mean, max, min, sum
	Interval    string       `json:"interval,omitempty"`    // 1h, 1d, 1w
}
