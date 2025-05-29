import React from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale, // Trục X (thời gian/labels)
  LinearScale, // Trục Y (giá trị)
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler, // Để tô màu vùng dưới đường line (nếu cần)
} from "chart.js";

// Đăng ký các thành phần cần thiết cho ChartJS
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const SensorChart = ({
  title,
  chartData,
  yAxisLabel = "Value",
  lineColor = "rgb(75, 192, 192)",
}) => {
  const options = {
    responsive: true, // Biểu đồ tự điều chỉnh kích thước
    maintainAspectRatio: false, // Cho phép tỉ lệ khung hình thay đổi
    plugins: {
      legend: {
        display: false, // Ẩn chú giải mặc định (chỉ có 1 đường dữ liệu)
      },
      title: {
        display: true,
        text: title, // Hiển thị tiêu đề biểu đồ
        font: {
          size: 16,
        },
        color: "#333",
        padding: {
          top: 10,
          bottom: 15,
        },
      },
      tooltip: {
        mode: "index",
        intersect: false,
        callbacks: {
          label: function (context) {
            let label = context.dataset.label || "";
            if (label) {
              label += ": ";
            }
            if (context.parsed.y !== null) {
              label += `${context.parsed.y} ${
                yAxisLabel === "Value" ? "" : yAxisLabel
              }`; // Thêm đơn vị vào tooltip
            }
            return label;
          },
        },
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: "Thời gian (Giờ trong ngày)",
          font: {
            size: 12,
          },
          color: "#666",
        },
        grid: {
          display: false, // Ẩn lưới dọc
        },
      },
      y: {
        title: {
          display: true,
          text: yAxisLabel, // Nhãn trục Y
          font: {
            size: 14,
          },
          color: "#666",
        },
        beginAtZero: true, // Bắt đầu trục Y từ 0 (tùy chỉnh nếu cần)
        // Có thể thêm min, max ở đây nếu cần cố định khoảng giá trị trục Y
        // min: 0,
        // max: 50
      },
    },
    interaction: {
      mode: "nearest",
      axis: "x",
      intersect: false,
    },
  };

  const data = {
    labels: chartData.labels || [], // Nhãn trục X (vd: ['00:00', '02:00', ...])
    datasets: [
      {
        label: title, // Nhãn cho dataset (hiển thị trong tooltip)
        data: chartData.values || [], // Mảng giá trị trục Y
        borderColor: lineColor,
        backgroundColor: lineColor
          .replace("rgb", "rgba")
          .replace(")", ", 0.1)"), // Màu nền dưới đường line (nhạt hơn)
        tension: 0.3, // Làm mịn đường line
        borderWidth: 2,
        pointBackgroundColor: lineColor,
        pointRadius: 3,
        pointHoverRadius: 5,
        // fill: true, // Tô màu vùng dưới đường line
      },
    ],
  };

  // Cần có container với chiều cao xác định để biểu đồ hiển thị
  return (
    <div className="bg-white p-4 rounded-lg shadow h-72 md:h-80">
      {/* Đặt chiều cao cố định hoặc min-height */}
      <Line options={options} data={data} />
    </div>
  );
};

export default SensorChart;
