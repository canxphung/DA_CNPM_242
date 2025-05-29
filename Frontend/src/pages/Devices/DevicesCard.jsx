// src/pages/Devices/DevicesCard.jsx
import React, { useState } from "react";
import { AlertTriangle, CheckCircle, Clock, Info } from "lucide-react"; // Removed TrendingUp, TrendingDown, Minus
import "./FlipCard.css";

const DevicesCard = ({
  title,
  value,
  sub, // unit
  percent,
  detail,
  feedId,
  date, // from timestamp
  time, // from timestamp
  status = "unknown", // 'normal', 'optimal', 'warning', 'critical', 'unknown'
  analysis = null,    // Object from sensor.analysis specific to this sensor
  metadata = null,
  recommendations = [], // Specific recommendations for this sensor
}) => {
  const [flipped, setFlipped] = useState(false);

  const getStatusStyling = () => {
    // Using the status directly passed (which should come from sensor.status in API)
    switch (status) {
      case "normal":
      case "optimal":
        return {
          color: "#10b981", 
          bgColor: "bg-emerald-50",
          borderColor: "border-emerald-200",
          icon: CheckCircle,
          message: analysis?.description || "Tình trạng tốt" // Use analysis description if available
        };
      case "warning": // Covers warning_low, warning_high if backend uses them
      case "warning_low":
      case "warning_high":
        return {
          color: "#f59e0b",
          bgColor: "bg-amber-50",
          borderColor: "border-amber-200",
          icon: AlertTriangle,
          message: analysis?.description || "Cần theo dõi"
        };
      case "critical": // Covers critical_low, critical_high
      case "critical_low":
      case "critical_high":
        return {
          color: "#ef4444",
          bgColor: "bg-red-50",
          borderColor: "border-red-200",
          icon: AlertTriangle,
          message: analysis?.description || "Cần can thiệp"
        };
      default: // unknown or other statuses
        return {
          color: "#6b7280",
          bgColor: "bg-gray-50",
          borderColor: "border-gray-200",
          icon: Clock,
          message: "Đang cập nhật..."
        };
    }
  };
  
  const getStrokeColor = () => {
    const statusStylingResult = getStatusStyling();
    if (status !== "unknown") {
      return statusStylingResult.color;
    }
    // Fallback percent logic (might be redundant if status is always set)
    if (percent < 30) return "#ef4444"; 
    if (percent < 70) return "#f59e0b";
    return "#10b981";
  };

  const formatAnalysisInfoForCard = () => {
    if (!analysis) return null;
    const info = [];
    // Extract relevant fields from the specific sensor's 'analysis' object
    // This depends on the structure of analysis.{sensor_type}.result from snapshot
    // Example: if analysis is { value, unit, status, description, needs_water, risk_level }
    if (analysis.description && analysis.status !== 'normal' && analysis.status !== 'optimal') {
        info.push({ label: "Đánh giá", value: analysis.description, color: getStatusStyling().color });
    }
    if (typeof analysis.needs_water === 'boolean') {
      info.push({ label: "Cần tưới", value: analysis.needs_water ? "Có" : "Không", color: analysis.needs_water ? "#ef4444" : "#10b981" });
    }
    if (analysis.risk_level) {
      info.push({ label: "Rủi ro", value: analysis.risk_level, color: analysis.risk_level === 'high' ? '#ef4444' : (analysis.risk_level === 'medium' ? '#f59e0b' : '#10b981') });
    }
    if (analysis.growth_condition) {
        info.push({label: "Điều kiện tăng trưởng", value: analysis.growth_condition.replace(/_/g, ' ')})
    }
    // Add more fields if they are present in individual sensor analysis result
    return info.slice(0, 3); // Show limited info on back
  };


  const statusStylingResult = getStatusStyling();
  const safePercent = Math.min(Math.max(percent || 0, 0), 100);
  const analysisDetailsForCard = formatAnalysisInfoForCard();

  return (
    <div className="perspective h-full" onClick={() => setFlipped(!flipped)}> {/* Ensure card takes full height */}
      <div
        className={`relative w-full h-full transition-transform duration-700 transform-style-preserve-3d ${
          flipped ? "rotate-y-180" : ""
        }`}
      >
        {/* Front Side */}
        <div className={`absolute inset-0 bg-white rounded-lg p-4 sm:p-6 shadow-lg border-2 ${statusStylingResult.bgColor} ${statusStylingResult.borderColor} backface-hidden flex flex-col`}>
          <div className="flex justify-between items-start mb-2 sm:mb-4">
            <h2 className="text-md sm:text-lg font-semibold text-gray-800">{title}</h2>
            <statusStylingResult.icon size={20} style={{ color: statusStylingResult.color }} className="sm:w-6 sm:h-6"/>
          </div>

          <div className="flex flex-col items-center justify-center flex-grow relative my-2">
            <svg className="w-20 h-20 sm:w-24 sm:h-24 transform -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="45" strokeWidth="8" fill="none" className="text-gray-200" stroke="currentColor"/>
              <circle
                cx="50"
                cy="50"
                r="45"
                stroke={getStrokeColor()}
                strokeWidth="8"
                fill="none"
                strokeDasharray="282.6"
                strokeDashoffset={282.6 - (safePercent / 100) * 282.6}
                strokeLinecap="round"
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center flex-col">
              <div className="text-xl sm:text-2xl font-bold text-gray-800">{value}</div>
              <p className="text-xs text-gray-500 mt-1">{sub}</p>
            </div>
          </div>

          <div className="mt-2 sm:mt-4 text-center">
            <p className="text-sm font-medium" style={{ color: statusStylingResult.color }}>
              {statusStylingResult.message}
            </p>
             {/* Can add a simple trend hint if backend provides it */}
            {analysis && analysis.trend_short_term && (
                <p className="text-xs text-gray-500 mt-0.5">Xu hướng gần: {analysis.trend_short_term}</p>
            )}
          </div>
        </div>

        {/* Back Side */}
        <div className="absolute inset-0 bg-white rounded-lg p-4 shadow-lg transform rotate-y-180 backface-hidden overflow-y-auto text-xs sm:text-sm">
          <h2 className="text-base sm:text-lg font-bold mb-2 text-gray-800">Chi tiết: {title}</h2>
          <p className="text-gray-600 mb-3">{detail}</p>
          
          <div className="space-y-1.5 mb-3">
            <div className="flex justify-between"><span className="text-gray-500">Ngày:</span><span className="text-gray-700 font-medium">{date}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Giờ:</span><span className="text-gray-700 font-medium">{time}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Feed ID:</span><span className="text-gray-700 font-mono text-xs">{feedId}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Giá trị:</span><span className="text-gray-700 font-bold">{value} {sub}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Trạng thái API:</span><span className="font-semibold" style={{color: statusStylingResult.color}}>{status}</span></div>
          </div>

          {analysisDetailsForCard && analysisDetailsForCard.length > 0 && (
            <div className="mb-3 pt-2 border-t">
              <h3 className="font-semibold text-gray-700 mb-1.5">Phân tích nhanh:</h3>
              <div className="space-y-1">
                {analysisDetailsForCard.map((info, index) => (
                  <div key={index} className="flex justify-between">
                    <span className="text-gray-600">{info.label}:</span>
                    <span style={{ color: info.color }} className="font-semibold text-right">{info.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {recommendations && recommendations.length > 0 && (
            <div className="mb-3 pt-2 border-t">
              <h3 className="font-semibold text-gray-700 mb-1.5">Gợi ý:</h3>
               {recommendations.slice(0,1).map((rec, index) => ( // Show only first one on card back
                  <div key={index} className="p-1.5 bg-blue-50 rounded border-l-2 border-blue-300">
                    <p className="text-blue-800 font-medium">{rec.action || rec.message}</p>
                    {rec.details && <p className="text-blue-600 mt-0.5 text-xs">{rec.details}</p>}
                  </div>
                ))}
            </div>
          )}
          
          {metadata && (
             <div className="pt-2 border-t text-gray-500">
                <h3 className="font-semibold text-gray-700 mb-1">Metadata:</h3>
                {Object.entries(metadata).map(([key, val]) =>(
                    <div key={key} className="flex justify-between text-xs"><span className="capitalize">{key.replace(/_/g, ' ')}:</span><span>{String(val)}</span></div>
                ))}
             </div>
          )}
          <p className="mt-3 text-center text-xs text-gray-400">Chạm để lật</p>
        </div>
      </div>
    </div>
  );
};

export default DevicesCard;