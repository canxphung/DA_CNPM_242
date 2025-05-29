// src/components/Graph.jsx
import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

// Props:
// - data: Array of data points, e.g., [{ time: "03:08", soil: 20, temp: 24, humidity: 60 }, ...]
// - title: Optional title for the graph
const Graph = ({ data, title = "Biểu đồ cảm biến" }) => {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-[360px] bg-white rounded-xl shadow p-4 flex items-center justify-center">
        <p className="text-gray-500">Không có dữ liệu để hiển thị biểu đồ.</p>
      </div>
    );
  }

  return (
    <div className="w-full h-[360px] bg-white rounded-xl shadow p-4">
      <h2 className="text-lg font-semibold mb-2 text-center">
        {title}
      </h2>
      <ResponsiveContainer width="100%" height="85%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis yAxisId="left" orientation="left" stroke="#38bdf8" />
          <YAxis yAxisId="middle" orientation="right" stroke="#f472b6" domain={['dataMin - 2', 'dataMax + 2']} />
          <YAxis yAxisId="right" orientation="right" stroke="#34d399" domain={['dataMin - 5', 'dataMax + 5']} dx={30}/>
          <Tooltip />
          <Legend />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="soil"
            name="Độ ẩm đất (%)"
            stroke="#38bdf8" // Sky blue
            strokeWidth={2}
            dot={false}
          />
          <Line
            yAxisId="middle"
            type="monotone"
            dataKey="temp"
            name="Nhiệt độ (°C)"
            stroke="#f472b6" // Pink
            strokeWidth={2}
            dot={false}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="humidity"
            name="Độ ẩm KK (%)"
            stroke="#34d399" // Green
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default Graph;