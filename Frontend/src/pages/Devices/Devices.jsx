// src/pages/Devices/Devices.jsx
import React, { useState, useCallback } from "react";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Sidebar from "../../components/Sidebar";
import DevicesCard from "./DevicesCard";
import SensorChart from "../../components/SensorChart";
import Loading from "../../components/Loading";
import { useSensorData } from "../../hooks/useSensorData";
import { RefreshCw, Activity, AlertTriangle, TrendingUp, Wifi, WifiOff, Info } from "lucide-react";

const Devices = () => {
  const [selectedChart, setSelectedChart] = useState("temperature");
  const [showPerformancePanel, setShowPerformancePanel] = useState(false);

  const {
    data,
    sensors, // Use sensors instead of data to avoid null issues
    chartData,
    loading,
    error,
    analysis: overallAnalysisSummary,
    recommendations: overallIrrigationRecommendations,
    overallStatus,
    refreshData,
    analyzeSensor,
    lastUpdate: lastUpdated,
    connectionStatus,
    getPerformanceMetrics,
    isAutoRefreshEnabled,
    currentRefreshInterval
  } = useSensorData({
    refreshInterval: 30000,
    enableAutoRefresh: true,
    historyHours: 12
  });

  const createEnhancedCards = useCallback(() => {
    // Create default sensor structure if sensors is empty
    const defaultSensor = {
      value: null,
      unit: "",
      status: "unknown",
      timestamp: null,
      feedId: "N/A",
      analysis: null
    };

    const temperature = sensors.temperature || { ...defaultSensor, unit: "°C", sensor_type: "temperature" };
    const moisture = sensors.moisture || { ...defaultSensor, unit: "%", sensor_type: "moisture" };
    const light = sensors.light || { ...defaultSensor, unit: "Lux", sensor_type: "light" };
    const soil = sensors.soil || { ...defaultSensor, unit: "%", sensor_type: "soil" };
    
    const getSensorSpecificRecommendations = (sensorType) => {
      if (!overallIrrigationRecommendations) return [];
      
      if (Array.isArray(overallIrrigationRecommendations)) {
        return overallIrrigationRecommendations.filter(rec => 
          rec.details?.toLowerCase().includes(sensorType) ||
          (sensorType === "soil" && (rec.action?.includes("water") || rec.details?.toLowerCase().includes("soil")))
        );
      }
      
      if (typeof overallIrrigationRecommendations === 'object' && overallIrrigationRecommendations !== null) {
        if (sensorType === "soil" && overallIrrigationRecommendations.needs_water) {
          return [{
            action: overallIrrigationRecommendations.reason,
            priority: overallIrrigationRecommendations.urgency,
            details: `Recommended water amount: ${overallIrrigationRecommendations.recommended_water_amount}`
          }];
        }
      }
      return [];
    };
    
    const calculateDisplayPercent = (sensorValue, sensorAnalysis, type) => {
      if (sensorValue === null || sensorValue === undefined) return 0;
      
      if (sensorAnalysis && sensorAnalysis.status) {
        switch (sensorAnalysis.status) {
          case "optimal":
          case "normal":
            return 85 + Math.random() * 15;
          case "warning":
          case "warning_low":
          case "warning_high":
            return 40 + Math.random() * 30;
          case "critical":
          case "critical_low":
          case "critical_high":
            return Math.random() * 30;
          default:
            return 50;
        }
      }
      
      const numericValue = parseFloat(sensorValue);
      if (isNaN(numericValue)) return 0;
      
      if (type === "temperature") return Math.min(Math.max(((numericValue - 0) / (50 - 0)) * 100, 0), 100);
      if (type === "moisture" || type === "soil") return Math.min(Math.max(numericValue, 0), 100);
      if (type === "light") return Math.min(Math.max(((numericValue - 0) / (2000 - 0)) * 100, 0), 100);
      return 50;
    };

    const sensorDetailsMap = {
      temperature: "Nhiệt độ môi trường, quan trọng cho sự phát triển của cây.",
      moisture: "Độ ẩm không khí, ảnh hưởng đến hô hấp và bệnh tật của cây.",
      light: "Cường độ ánh sáng, cần thiết cho quá trình quang hợp.",
      soil: "Độ ẩm trong đất, yếu tố chính quyết định nhu cầu tưới."
    };

    return [
      { sensor: temperature, type: "temperature" },
      { sensor: moisture, type: "moisture" },
      { sensor: light, type: "light" },
      { sensor: soil, type: "soil" }
    ].map(({ sensor, type }) => {
      const hasValue = sensor.value !== null && sensor.value !== undefined;
      const displayValue = hasValue ? parseFloat(sensor.value).toFixed(1) : "N/A";
      
      return {
        type: type,
        title: type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' '),
        value: hasValue ? `${displayValue}${sensor.unit || ''}` : "N/A",
        sub: sensor.unit || "",
        percent: calculateDisplayPercent(sensor.value, sensor.analysis, type),
        detail: sensorDetailsMap[type] || "Dữ liệu cảm biến quan trọng.",
        feedId: sensor.feedId || "N/A",
        date: sensor.timestamp ? new Date(sensor.timestamp).toLocaleDateString("vi-VN") : "N/A",
        time: sensor.timestamp ? new Date(sensor.timestamp).toLocaleTimeString("vi-VN") : "N/A",
        status: sensor.status || "unknown",
        analysis: sensor.analysis || { description: hasValue ? "Đang phân tích..." : "Không có dữ liệu" },
        metadata: sensor.metadata || null,
        recommendations: getSensorSpecificRecommendations(type),
      };
    });
  }, [sensors, overallIrrigationRecommendations]);

  const chartConfig = {
    temperature: { title: "Nhiệt độ", lineColor: "rgb(239, 68, 68)", yAxisLabel: "°C" },
    moisture: { title: "Độ ẩm không khí", lineColor: "rgb(59, 130, 246)", yAxisLabel: "%" },
    light: { title: "Cường độ ánh sáng", lineColor: "rgb(234, 179, 8)", yAxisLabel: "Lux" },
    soil: { title: "Độ ẩm đất", lineColor: "rgb(34, 197, 94)", yAxisLabel: "%" }
  };

  const getConnectionStyling = () => {
    switch (connectionStatus) {
      case 'connected':
        return { color: 'text-green-600', bgColor: 'bg-green-50', icon: Wifi, message: 'Kết nối ổn định' };
      case 'connecting':
        return { color: 'text-yellow-600', bgColor: 'bg-yellow-50', icon: Wifi, message: 'Đang kết nối...' };
      case 'error':
        return { color: 'text-red-600', bgColor: 'bg-red-50', icon: WifiOff, message: `Lỗi kết nối${error ? `: ${error.substring(0, 30)}...` : ''}` };
      default:
        return { color: 'text-gray-600', bgColor: 'bg-gray-50', icon: Wifi, message: 'Không rõ' };
    }
  };
  
  const handleAnalyzeSpecificSensor = async (sensorTypeToAnalyze) => {
    console.log(`Requesting analysis for: ${sensorTypeToAnalyze}`);
    const result = await analyzeSensor(sensorTypeToAnalyze);
    if (result.success) {
      alert(`Phân tích cho ${sensorTypeToAnalyze}:\nTrạng thái: ${result.analysis?.status}\nMô tả: ${result.analysis?.description || 'N/A'}`);
    } else {
      alert(`Lỗi phân tích ${sensorTypeToAnalyze}: ${result.error}`);
    }
  };

  const cards = createEnhancedCards();
  const connectionStylingResult = getConnectionStyling();

  // Show loading only on initial load
  if (loading && !data && !sensors.temperature) {
    return <Loading />;
  }

  // Error state with no data at all
  if (error && connectionStatus === 'error' && (!sensors || Object.keys(sensors).length === 0)) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex flex-col flex-1 ml-64">
          <Header />
          <main className="flex-grow container mx-auto py-8 px-4 flex flex-col justify-center items-center">
            <div className="bg-red-50 border border-red-200 p-8 rounded-lg shadow-md text-center max-w-md">
              <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-red-700 mb-2">Lỗi tải dữ liệu sensor</h2>
              <p className="text-red-600 mb-4">{error}</p>
              <button 
                onClick={() => refreshData()}
                className="w-full px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors flex items-center justify-center"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Thử lại
              </button>
            </div>
          </main>
          <Footer />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-col flex-1 ml-64">
        <Header />
        
        <main className="flex-grow container mx-auto py-6 px-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-2">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">
                Bảng điều khiển thiết bị
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Giám sát và phân tích dữ liệu sensor thời gian thực.
                {lastUpdated && ` Cập nhật lần cuối: ${lastUpdated.toLocaleTimeString('vi-VN')}`}
              </p>
            </div>
            
            <div className="flex items-center space-x-2 self-start sm:self-center">
              <div title={connectionStylingResult.message} className={`flex items-center px-3 py-1.5 rounded-lg ${connectionStylingResult.bgColor} text-xs`}>
                <connectionStylingResult.icon className={`w-3.5 h-3.5 mr-1.5 ${connectionStylingResult.color}`} />
                <span className={`font-medium ${connectionStylingResult.color}`}>
                  {connectionStylingResult.message.split(':')[0]}
                </span>
              </div>
              <button 
                onClick={() => refreshData()} 
                disabled={loading}
                className="flex items-center px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 text-sm"
                title="Làm mới dữ liệu"
              >
                <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Đang tải...' : 'Làm mới'}
              </button>
            </div>
          </div>

          {error && !loading && (
            <div className="mb-4 p-3 bg-red-50 border-l-4 border-red-400 text-red-700 text-sm rounded-md">
              <div className="flex items-center">
                <AlertTriangle size={18} className="mr-2" />
                <p><strong className="font-semibold">Lỗi:</strong> {error}</p>
              </div>
            </div>
          )}

          {overallStatus && overallStatus !== 'normal' && overallStatus !== 'error' && overallStatus !== 'unknown' && (
            <div className={`mb-6 p-3 rounded-lg border-l-4 text-sm ${
              overallStatus === 'warning' ? 'bg-yellow-50 border-yellow-400 text-yellow-700' : 
              overallStatus === 'critical' ? 'bg-red-50 border-red-400 text-red-700' : 
              'bg-gray-50 border-gray-400 text-gray-700'
            }`}>
              <div className="flex items-center">
                {overallStatus === 'warning' || overallStatus === 'critical' ? 
                  <AlertTriangle size={18} className="mr-2" /> : 
                  <Info size={18} className="mr-2" />
                }
                <p>
                  <strong className="font-semibold">Trạng thái hệ thống:</strong> {overallStatus.toUpperCase()}. 
                  {overallAnalysisSummary?.general_recommendation || " Kiểm tra các cảm biến."}
                </p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6 mb-8">
            {cards.map((cardProps, index) => (
              <div key={cardProps.type || index} className="h-64">
                <DevicesCard {...cardProps} />
              </div>
            ))}
          </div>

          <div className="mt-6 bg-white rounded-xl shadow-lg p-4 sm:p-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4">
              <h2 className="text-lg sm:text-xl font-semibold text-gray-700">
                Biểu đồ dữ liệu (12 giờ qua)
              </h2>
              <div className="flex items-center space-x-2 mt-2 sm:mt-0">
                <button
                  onClick={() => handleAnalyzeSpecificSensor(selectedChart)}
                  disabled={loading}
                  className="flex items-center px-3 py-1.5 bg-teal-500 text-white rounded-md hover:bg-teal-600 transition-colors text-sm disabled:opacity-50"
                  title={`Phân tích chi tiết ${chartConfig[selectedChart]?.title || selectedChart}`}
                >
                  <TrendingUp className="w-4 h-4 mr-1.5" />
                  Phân tích sâu
                </button>
              </div>
            </div>

            <div className="flex border-b border-gray-200 mb-4 overflow-x-auto no-scrollbar">
              {Object.keys(chartConfig).map((type) => (
                <button
                  key={type}
                  className={`px-3 sm:px-4 py-2.5 font-medium whitespace-nowrap transition-colors text-sm sm:text-base ${
                    selectedChart === type
                      ? "text-blue-600 border-b-2 border-blue-600"
                      : "text-gray-500 hover:text-gray-700 hover:border-b-2 hover:border-gray-300"
                  }`}
                  onClick={() => setSelectedChart(type)}
                >
                  {chartConfig[type].title}
                </button>
              ))}
            </div>

            {chartData && chartData[selectedChart] && chartData[selectedChart].labels && chartData[selectedChart].labels.length > 0 ? (
              <SensorChart
                title=""
                chartData={chartData[selectedChart]}
                yAxisLabel={chartConfig[selectedChart]?.yAxisLabel || "Giá trị"}
                lineColor={chartConfig[selectedChart]?.lineColor || "rgb(75, 192, 192)"}
              />
            ) : (
              <div className="h-72 md:h-80 flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <Activity className="w-10 h-10 mx-auto mb-3 text-gray-400" />
                  <p>
                    {loading ? "Đang tải dữ liệu biểu đồ..." : "Không có dữ liệu cho biểu đồ."}
                  </p>
                  {chartData && chartData[selectedChart]?.error && (
                    <p className="text-xs text-red-500 mt-1">{chartData[selectedChart].error}</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </main>
        <Footer />
      </div>
    </div>
  );
};

export default Devices;