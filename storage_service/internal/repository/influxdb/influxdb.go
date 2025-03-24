package influxdb

import (
	"context"
	"fmt"
	"time"

	"github.com/influxdata/influxdb-client-go/v2/api"

	"storage-service/internal/models"
)

type Repository struct {
	client   influxdb2.Client
	writeAPI api.WriteAPI
	queryAPI api.QueryAPI
	org      string
	bucket   string
}

// NewRepository tạo kết nối mới tới InfluxDB
func NewRepository(url, token, org, bucket string) (*Repository, error) {
	client := influxdb2.NewClient(url, token)

	// Kiểm tra kết nối
	health, err := client.Health(context.Background())
	if err != nil {
		return nil, fmt.Errorf("failed to connect to InfluxDB: %w", err)
	}
	if health.Status != "pass" {
		return nil, fmt.Errorf("InfluxDB is not healthy: %s", health.Status)
	}

	// Tạo writeAPI cho ghi không đồng bộ
	writeAPI := client.WriteAPI(org, bucket)
	// Tạo queryAPI cho truy vấn
	queryAPI := client.QueryAPI(org)

	return &Repository{
		client:   client,
		writeAPI: writeAPI,
		queryAPI: queryAPI,
		org:      org,
		bucket:   bucket,
	}, nil
}

// Close đóng kết nối
func (r *Repository) Close() {
	r.client.Close()
}

// StoreSensorReading lưu một bản ghi cảm biến
func (r *Repository) StoreSensorReading(ctx context.Context, reading *models.SensorReading) error {
	// Tạo point
	p := influxdb2.NewPointWithMeasurement(string(reading.SensorType))
	p.SetTime(reading.Timestamp)

	// Thêm tags
	p.AddTag("sensor_id", reading.SensorID)
	p.AddTag("location", reading.Location)

	// Thêm tags tùy chọn khác
	for k, v := range reading.Tags {
		p.AddTag(k, v)
	}

	// Thêm các giá trị
	for k, v := range reading.Values {
		p.AddField(k, v)
	}

	// Ghi không đồng bộ
	r.writeAPI.WritePoint(p)

	return nil
}

// StoreBatchReadings lưu nhiều bản ghi cùng lúc
func (r *Repository) StoreBatchReadings(ctx context.Context, batch *models.BatchReadings) error {
	for _, reading := range batch.Readings {
		err := r.StoreSensorReading(ctx, &reading)
		if err != nil {
			return err
		}
	}

	// Flush để đảm bảo tất cả dữ liệu được ghi
	r.writeAPI.Flush()

	return nil
}

// QuerySensorData truy vấn dữ liệu theo các tham số
func (r *Repository) QuerySensorData(ctx context.Context, params *models.QueryParams) ([]models.SensorReading, error) {
	// Xây dựng truy vấn Flux
	query := buildFluxQuery(params, r.bucket)

	// Thực hiện truy vấn
	result, err := r.queryAPI.Query(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("query failed: %w", err)
	}

	// Xử lý kết quả
	var readings []models.SensorReading
	for result.Next() {
		record := result.Record()

		reading := models.SensorReading{
			Timestamp:  record.Time(),
			SensorID:   record.ValueByKey("sensor_id").(string),
			SensorType: models.SensorType(record.Measurement()),
			Location:   record.ValueByKey("location").(string),
			Values:     make(map[string]float64),
			Tags:       make(map[string]string),
		}

		// Xử lý fields
		for k, v := range record.Values() {
			// Bỏ qua các fields đã xử lý
			if k == "sensor_id" || k == "location" || k == "_time" || k == "_measurement" {
				continue
			}

			// Xử lý tags và values
			if fv, ok := v.(float64); ok {
				reading.Values[k] = fv
			} else if sv, ok := v.(string); ok {
				reading.Tags[k] = sv
			}
		}

		readings = append(readings, reading)
	}

	if result.Err() != nil {
		return nil, fmt.Errorf("error parsing results: %w", result.Err())
	}

	return readings, nil
}

// buildFluxQuery xây dựng truy vấn Flux từ tham số
func buildFluxQuery(params *models.QueryParams, bucket string) string {
	// Truy vấn cơ bản
	query := fmt.Sprintf(`
		from(bucket: "%s")
		|> range(start: %s, stop: %s)
	`, bucket, params.StartTime.Format(time.RFC3339), params.EndTime.Format(time.RFC3339))

	// Lọc theo loại cảm biến
	if len(params.SensorTypes) > 0 {
		query += "\n|> filter(fn: (r) => "
		for i, sType := range params.SensorTypes {
			if i > 0 {
				query += " or "
			}
			query += fmt.Sprintf(`r._measurement == "%s"`, sType)
		}
		query += ")"
	}

	// Lọc theo ID cảm biến
	if len(params.SensorIDs) > 0 {
		query += "\n|> filter(fn: (r) => "
		for i, id := range params.SensorIDs {
			if i > 0 {
				query += " or "
			}
			query += fmt.Sprintf(`r.sensor_id == "%s"`, id)
		}
		query += ")"
	}

	// Lọc theo vị trí
	if len(params.Locations) > 0 {
		query += "\n|> filter(fn: (r) => "
		for i, loc := range params.Locations {
			if i > 0 {
				query += " or "
			}
			query += fmt.Sprintf(`r.location == "%s"`, loc)
		}
		query += ")"
	}

	// Tính toán tổng hợp (nếu có)
	if params.Aggregation != "" && params.Interval != "" {
		query += fmt.Sprintf(`
			|> aggregateWindow(
				every: %s,
				fn: %s,
				createEmpty: false
			)
		`, params.Interval, params.Aggregation)
	}

	// Giới hạn và phân trang
	if params.Limit > 0 {
		query += fmt.Sprintf("\n|> limit(n: %d)", params.Limit)
	}
	if params.Offset > 0 {
		query += fmt.Sprintf("\n|> offset(n: %d)", params.Offset)
	}

	return query
}
