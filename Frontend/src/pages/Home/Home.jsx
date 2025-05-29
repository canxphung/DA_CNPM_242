// src/pages/Home/Home.jsx
import React, { useState, useEffect, useCallback } from "react"; // Added useCallback
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Sidebar from "../../components/Sidebar";
import BubbleIcon from "../../components/BubbleIcon";
import { useSensorData } from "../../hooks/useSensorData";
import Loading from "../../components/Loading";
import DevicesCard from "../Devices/DevicesCard"; // Using the updated DevicesCard
import NotificationButton from "../../components/NotificationButton";
import { AlertTriangle, CheckCircle, Activity, Lightbulb, Droplet, Info, Wifi, WifiOff, RefreshCw } from "lucide-react"; // Added some icons

const Home = () => {
  const [showDetailedAlerts, setShowDetailedAlerts] = useState(false); // Renamed from recommendations
  const [priorityAlerts, setPriorityAlerts] = useState([]);

  const { 
    data, 
    loading, 
    error, 
    analysis: overallAnalysisSummary, // Renamed for clarity { temperature: {analysis_for_temp}, ... }
    recommendations: overallIrrigationRecommendations, // Irrigation recommendations array
    overallStatus, // String status: 'normal', 'warning', 'critical'
    refreshData, 
    connectionStatus,
    lastUpdate
  } = useSensorData({
    refreshInterval: 45000,
    enableAutoRefresh: true,
    historyHours: 6 
  });

  // Deconstruct sensor data AFTER checking for loading/error for initial state
  const { temperature = {}, moisture = {}, light = {}, soil = {} } = data || {};


  useEffect(() => {
    const alerts = [];
    if (!data || Object.keys(data).length === 0) {
        setPriorityAlerts([]);
        return;
    }

    // Lấy trực tiếp từ data thay vì dùng destructured variables
    const { temperature, moisture, light, soil } = data;

    // Helper to format sensor values consistently
    const formatVal = (sensor) => sensor && typeof sensor.value !== 'undefined' ? parseFloat(sensor.value).toFixed(1) : 'N/A';

    if (soil?.status === 'critical' || soil?.status === 'critical_low') {
      alerts.push({
        id: 'soil_critical', type: 'critical', icon: Droplet, title: 'Đất rất khô',
        message: `Độ ẩm đất rất thấp: ${formatVal(soil)}%`, action: 'Cần tưới khẩn cấp!', priority: 1
      });
    }
    if (temperature.status === 'critical' || temperature.status === 'critical_high' || temperature.status === 'critical_low') {
      const tempVal = formatVal(temperature);
      alerts.push({
        id: 'temp_critical', type: 'critical', icon: AlertTriangle, title: tempVal > 38 ? 'Nhiệt độ quá cao' : (tempVal < 10 ? 'Nhiệt độ quá thấp' : 'Nhiệt độ nguy hiểm'),
        message: `Nhiệt độ ở mức nguy hiểm: ${tempVal}°C`, action: 'Điều chỉnh nhiệt độ ngay!', priority: 1
      });
    }
    // ... add more warning level alerts based on soil.status, moisture.status etc.
    if (soil.status === 'warning' || soil.status === 'warning_low') {
      alerts.push({
        id: 'soil_warning', type: 'warning', icon: Droplet, title: 'Đất đang khô dần',
        message: `Độ ẩm đất: ${formatVal(soil)}%`, action: 'Xem xét tưới sớm.', priority: 2
      });
    }
     if (moisture.status === 'warning' || moisture.status === 'warning_low' || moisture.status === 'warning_high') {
      alerts.push({
        id: 'humidity_warning', type: 'warning', icon: Activity, title: 'Độ ẩm không khí bất thường',
        message: `Độ ẩm không khí: ${formatVal(moisture)}%`, action: 'Kiểm tra hệ thống thông gió/tạo ẩm.', priority: 2
      });
    }

    if (connectionStatus === 'error' && error) { // Use the error state from the hook
      alerts.push({
        id: 'connection_error', type: 'warning', icon: WifiOff, title: 'Mất kết nối cảm biến',
        message: error.substring(0, 100) + (error.length > 100 ? "..." : ""), // Show part of the error
        action: 'Kiểm tra kết nối mạng và refresh.', priority: 2
      });
    }

    alerts.sort((a, b) => a.priority - b.priority);
    setPriorityAlerts(alerts.slice(0, 3));
}, [data, overallStatus, connectionStatus, error]); // Add specific sensor data as dependencies

  
  const createEnhancedCardsForHome = useCallback(() => {
    if (!data || Object.keys(data).length === 0 || !temperature?.feedId) { // Check if data is populated
      return [];
    }
     // Reusing helper from Devices.jsx, assuming it's broadly applicable
    const calculateDisplayPercent = (sensorValue, sensorAnalysis, type) => {
        if (sensorAnalysis && sensorAnalysis.status) {
            switch (sensorAnalysis.status) {
                case "optimal": case "normal": return 85 + Math.random() * 15;
                case "warning": case "warning_low": case "warning_high": return 40 + Math.random() * 30;
                case "critical": case "critical_low": case "critical_high": return Math.random() * 30;
                default: return 50;
            }
        }
        if (type === "temperature") return Math.min(Math.max(((parseFloat(sensorValue) - 0) / (50 - 0)) * 100, 0), 100);
        if (type === "moisture" || type === "soil") return Math.min(Math.max(parseFloat(sensorValue), 0), 100);
        if (type === "light") return Math.min(Math.max(((parseFloat(sensorValue) - 0) / (2000 - 0)) * 100, 0), 100);
        return 50;
    };
    const sensorDetailsMap = {
        temperature: "Nhiệt độ không khí trong nhà kính.",
        moisture: "Độ ẩm không khí hiện tại.",
        light: "Mức độ ánh sáng cho cây quang hợp.",
        soil: "Độ ẩm của đất, chỉ số tưới tiêu."
    };

    // The `data` object from `useSensorData` now contains:
    // data.temperature = { value, unit, status, timestamp, feedId, analysis (specific for temp) }
    // data.moisture = { value, unit, status, timestamp, feedId, analysis (specific for moisture/humidity) }
    // etc.
    // overallAnalysisSummary contains { temperature: analysis_for_temp, moisture: analysis_for_moisture }

    return [temperature, moisture, light, soil].map(sensorData => {
      if (!sensorData || typeof sensorData.value === 'undefined') {
          let type = "unknown_sensor"; // Default, then try to determine from reference
            if(sensorData === temperature) type="temperature";
            if(sensorData === moisture) type="moisture";
            if(sensorData === light) type="light";
            if(sensorData === soil) type="soil";
         return {
             type, title: "Cảm biến", value: "N/A", sub: "", percent: 0, detail: "Thiếu dữ liệu",
             feedId: "N/A", date: "N/A", time: "N/A", status: "error", analysis: null, recommendations: []
         };
      }
      // Determine the primary type key ('temperature', 'moisture', 'light', 'soil')
      let typeKey = sensorData.sensor_type || 'unknown'; // 'humidity' or 'soil_moisture' or 'light' or 'temperature'
      if (typeKey === 'humidity') typeKey = 'moisture';
      if (typeKey === 'soil_moisture') typeKey = 'soil';

      // analysis specific to this sensor is directly in sensorData.analysis if populated by sensorService
      const specificAnalysis = sensorData.analysis;

      return {
        type: typeKey,
        title: typeKey.charAt(0).toUpperCase() + typeKey.slice(1).replace('_', ' '),
        value: `${parseFloat(sensorData.value).toFixed(1)}${sensorData.unit || ''}`,
        sub: sensorData.unit || "",
        percent: calculateDisplayPercent(sensorData.value, specificAnalysis, typeKey),
        detail: sensorDetailsMap[typeKey] || "Dữ liệu cảm biến quan trọng.",
        feedId: sensorData.feedId || "N/A",
        date: sensorData.timestamp ? new Date(sensorData.timestamp).toLocaleDateString("vi-VN") : "N/A",
        time: sensorData.timestamp ? new Date(sensorData.timestamp).toLocaleTimeString("vi-VN") : "N/A",
        status: sensorData.status || "unknown",
        analysis: specificAnalysis, // Pass the specific analysis for this sensor
        metadata: sensorData.metadata, // If available
        // For Home cards, general recommendations or very specific ones for this sensor
        // overallIrrigationRecommendations are usually for 'soil' primarily
        recommendations: typeKey === 'soil' && overallIrrigationRecommendations ? 
            (Array.isArray(overallIrrigationRecommendations) ? overallIrrigationRecommendations : [overallIrrigationRecommendations]) 
            : (specificAnalysis?.recommendations || [])
      };
    });
  }, [data, overallIrrigationRecommendations]);


  const getSystemStatusSummary = useCallback(() => { // Converted to useCallback
    if (overallStatus === 'error') {
        return { status: 'error', message: error || "Lỗi hệ thống, không thể xác định trạng thái.", color: 'text-red-600', bgColor: 'bg-red-50', borderColor: 'border-red-200', icon: AlertTriangle};
    }
    const criticalCount = priorityAlerts.filter(alert => alert.type === 'critical').length;
    const warningCount = priorityAlerts.filter(alert => alert.type === 'warning').length;
    
    if (overallStatus === 'critical' || criticalCount > 0) {
      return { status: 'critical', message: `Hệ thống có ${criticalCount || 1} vấn đề nghiêm trọng!`, color: 'text-red-600', bgColor: 'bg-red-50', borderColor: 'border-red-200', icon: AlertTriangle };
    }
    if (overallStatus === 'warning' || warningCount > 0) {
      return { status: 'warning', message: `Hệ thống có ${warningCount || 1} cảnh báo cần chú ý.`, color: 'text-yellow-600', bgColor: 'bg-yellow-50', borderColor: 'border-yellow-200', icon: AlertTriangle };
    }
    return { status: 'normal', message: 'Tất cả hệ thống hoạt động bình thường.', color: 'text-green-600', bgColor: 'bg-green-50', borderColor: 'border-green-200', icon: CheckCircle };
  }, [overallStatus, priorityAlerts, error]);


  const generateSmartRecommendationsForHome = useCallback(() => {
    if (!data || Object.keys(data).length === 0) return [];
    let recs = [];

    // From overall irrigation recommendation (snapshot)
    if (overallIrrigationRecommendations) {
        const recArray = Array.isArray(overallIrrigationRecommendations) ? overallIrrigationRecommendations : [overallIrrigationRecommendations];
        recArray.forEach(rec => {
            if (rec.action_items && Array.isArray(rec.action_items)) { // If snapshot provides action_items
                recs = recs.concat(rec.action_items.map(item => ({
                    icon: item.action?.includes("water") ? Droplet : Info,
                    title: item.action?.replace(/_/g, ' ') || "Hành động được gợi ý",
                    description: item.details || rec.reason || "Dựa trên phân tích AI.",
                    action: item.priority ? `Ưu tiên: ${item.priority}` : "Nên thực hiện sớm",
                    priority: item.priority || 'medium'
                })));
            } else if (rec.needs_water) { // Fallback to direct irrigation recommendation
                 recs.push({
                    icon: Droplet, title: 'Khuyến nghị tưới',
                    description: rec.reason || `Độ ẩm đất cần điều chỉnh.`,
                    action: `Tưới với lượng ${rec.recommended_water_amount || 'phù hợp'}. Ưu tiên ${rec.urgency || 'trung bình'}`,
                    priority: rec.urgency || 'medium'
                });
            }
        });
    }

    // Add recommendations from individual sensor analyses if available
    // Example: Check temperature analysis
    const tempAnalysis = overallAnalysisSummary?.temperature;
    if (tempAnalysis && (tempAnalysis.status === 'warning' || tempAnalysis.status === 'critical')) {
        recs.push({
            icon: AlertTriangle, title: 'Nhiệt độ bất thường',
            description: tempAnalysis.description || `Nhiệt độ hiện tại ${tempAnalysis.value}°C.`,
            action: tempAnalysis.stress_level === 'high' ? 'Cần điều chỉnh nhiệt độ gấp!' : 'Theo dõi và điều chỉnh nhiệt độ.',
            priority: tempAnalysis.stress_level === 'high' ? 'high' : 'medium'
        });
    }
     // Light analysis
    const lightAnalysis = overallAnalysisSummary?.light;
    if (lightAnalysis && (lightAnalysis.status === 'warning' || lightAnalysis.status === 'critical')) {
        recs.push({
            icon: Lightbulb, title: 'Ánh sáng không tối ưu',
            description: lightAnalysis.description || `Cường độ sáng ${lightAnalysis.value} Lux.`,
            action: lightAnalysis.plant_impact !== 'good_growth' ? 'Điều chỉnh nguồn sáng bổ sung/che chắn.' : 'Theo dõi thêm.',
            priority: lightAnalysis.plant_impact !== 'good_growth' ? 'medium' : 'low'
        });
    }

    // If no specific recs, show a general status or a "good" status.
    if (recs.length === 0 && overallStatus === 'normal') {
        recs.push({
            icon: CheckCircle, title: "Hệ thống ổn định",
            description: "Các chỉ số môi trường trong ngưỡng tối ưu.",
            action: "Tiếp tục theo dõi định kỳ.",
            priority: 'low'
        });
    }
    // Sort by priority (assuming high, medium, low strings)
    const priorityOrder = { 'high': 1, 'medium': 2, 'low': 3 };
    recs.sort((a, b) => (priorityOrder[a.priority] || 4) - (priorityOrder[b.priority] || 4));
    return recs.slice(0, 3); // Show top 3
  }, [data, overallIrrigationRecommendations, overallAnalysisSummary, overallStatus]);


  const homeCards = createEnhancedCardsForHome();
  const systemStatusSummary = getSystemStatusSummary();
  const smartRecsForHome = generateSmartRecommendationsForHome();


  if (loading && !data?.temperature?.feedId) { // Show loading only if there's no initial data yet
    return <Loading />;
  }
  
  const connectionStyling = () => { // Local function for Home page
     switch (connectionStatus) {
      case 'connected': return { color: 'text-green-600', icon: Wifi };
      case 'connecting': return { color: 'text-yellow-500', icon: Wifi }; // Pulsing or different animation?
      case 'error': return { color: 'text-red-500', icon: WifiOff };
      default: return { color: 'text-gray-500', icon: Wifi };
    }
  };
  const currentConnectionStyling = connectionStyling();


  return (
    <div className="flex min-h-screen">
      <Sidebar />
      
      <div className="flex flex-col flex-1 md:ml-64"> {/* Ensure content flows correctly with fixed sidebar */}
        <Header />
        <NotificationButton /> {/* Assume this is absolutely positioned */}

        <main className="flex-grow p-4 sm:p-6 bg-gray-100">
          <div className="mb-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-3">
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-gray-800">Tổng quan Nhà kính</h1>
                <p className="text-sm text-gray-500 mt-1 flex items-center">
                  <currentConnectionStyling.icon size={16} className={`mr-1.5 ${currentConnectionStyling.color}`} />
                  {connectionStatus === 'connected' ? 'Đã kết nối' : connectionStatus === 'error' ? `Lỗi kết nối` : 'Đang kết nối...'}
                  {lastUpdate && (<span className="hidden sm:inline"> &nbsp;• Cập nhật: {lastUpdate.toLocaleTimeString('vi-VN')}</span>)}
                </p>
              </div>
              
              <button
                onClick={() => refreshData()} // This is clearCacheAndRefresh from useSensorData
                className="mt-2 sm:mt-0 flex items-center px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm disabled:opacity-60"
                disabled={loading}
              >
                <RefreshCw className={`w-4 h-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Đang cập nhật...' : 'Làm mới'}
              </button>
            </div>

            {error && !loading && ( // Show error if not actively loading a fresh state
                 <div className="mb-4 p-3 bg-red-50 border-l-4 border-red-400 text-red-700 text-sm rounded-md">
                    <div className="flex items-center"><AlertTriangle size={18} className="mr-2"/><p>{error}</p></div>
                </div>
            )}

            <div className={`p-4 rounded-lg border ${systemStatusSummary.bgColor} ${systemStatusSummary.borderColor} mb-6 shadow-sm`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <systemStatusSummary.icon className={`w-6 h-6 mr-3 ${systemStatusSummary.color}`} />
                  <div>
                    <p className={`font-semibold ${systemStatusSummary.color}`}>
                      Trạng thái hệ thống
                    </p>
                    <p className={`text-sm ${systemStatusSummary.color.replace('600', '700')}`}>
                      {systemStatusSummary.message}
                    </p>
                  </div>
                </div>
                {priorityAlerts.length > 0 && (
                  <button
                    onClick={() => setShowDetailedAlerts(!showDetailedAlerts)}
                    className={`px-3 py-1 rounded text-sm font-medium hover:bg-opacity-20 transition-colors
                                ${systemStatusSummary.color === 'text-red-600' ? 'text-red-600 hover:bg-red-100' :
                                  systemStatusSummary.color === 'text-yellow-600' ? 'text-yellow-600 hover:bg-yellow-100' :
                                  'text-green-600 hover:bg-green-100'}`}
                  >
                    {showDetailedAlerts ? 'Ẩn' : 'Chi tiết'} ({priorityAlerts.length})
                  </button>
                )}
              </div>
            </div>
          </div>

          {showDetailedAlerts && priorityAlerts.length > 0 && (
            <div className="mb-6 space-y-3 animate-fadeIn">
              <h3 className="text-md font-semibold text-gray-700 mb-1">Cảnh báo ưu tiên:</h3>
              {priorityAlerts.map((alert) => (
                <div key={alert.id} className={`p-3 rounded-lg border-l-4 shadow-sm ${
                  alert.type === 'critical' ? 'bg-red-50 border-red-500' : 'bg-yellow-50 border-yellow-500'
                }`}>
                  <div className="flex items-start">
                    <alert.icon className={`w-5 h-5 mr-2.5 mt-0.5 flex-shrink-0 ${
                      alert.type === 'critical' ? 'text-red-500' : 'text-yellow-500'
                    }`} />
                    <div className="flex-1">
                      <p className={`font-medium text-sm ${
                        alert.type === 'critical' ? 'text-red-800' : 'text-yellow-800'
                      }`}>{alert.title}</p>
                      <p className={`text-xs mt-0.5 ${
                        alert.type === 'critical' ? 'text-red-700' : 'text-yellow-700'
                      }`}>{alert.message}</p>
                      <p className={`text-xs font-semibold mt-1 ${
                        alert.type === 'critical' ? 'text-red-600' : 'text-yellow-600'
                      }`}>➡️ {alert.action}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6 mb-8">
            {homeCards.map((cardProps, index) => (
              <div key={cardProps.type || index} className="h-64"> {/* Fixed height for cards */}
                <DevicesCard {...cardProps} />
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-xl shadow-lg">
              <h2 className="text-lg font-semibold mb-4 text-gray-700 flex items-center">
                <Activity className="w-5 h-5 mr-2 text-blue-500" />
                Trạng thái Hoạt động Dự kiến
              </h2>
              <div className="space-y-3 text-sm text-gray-600">
                {[
                  { label: "Bơm tưới", 
                    status: (soil?.analysis?.needs_water || overallIrrigationRecommendations?.needs_water) ? "Sắp tưới" : "Không cần tưới", 
                    color: (soil?.analysis?.needs_water || overallIrrigationRecommendations?.needs_water) ? "text-blue-600 bg-blue-50" : "text-gray-700 bg-gray-50",
                    detail: soil?.analysis?.description || overallIrrigationRecommendations?.reason || (soil.value ? `Độ ẩm đất: ${parseFloat(soil.value).toFixed(1)}%` : 'Chưa có dữ liệu')
                  },
                  { label: "Đèn chiếu sáng", 
                    status: light?.analysis?.status === 'warning_low' || (light?.value && parseFloat(light.value) < 500) ? "Nên bật" : "Đủ sáng", 
                    color: light?.analysis?.status === 'warning_low' || (light?.value && parseFloat(light.value) < 500) ? "text-yellow-700 bg-yellow-50" : "text-gray-700 bg-gray-50",
                    detail: light?.analysis?.description || (light.value ? `Cường độ: ${parseFloat(light.value).toFixed(0)} Lux` : 'Chưa có dữ liệu')
                  },
                  { label: "Thông gió/Làm mát", 
                    status: temperature?.analysis?.status === 'warning_high' || (temperature?.value && parseFloat(temperature.value) > 30) ? "Nên bật" : "Nhiệt độ ổn", 
                    color: temperature?.analysis?.status === 'warning_high' || (temperature?.value && parseFloat(temperature.value) > 30) ? "text-orange-600 bg-orange-50" : "text-gray-700 bg-gray-50",
                    detail: temperature?.analysis?.description || (temperature.value ? `Nhiệt độ: ${parseFloat(temperature.value).toFixed(1)}°C` : 'Chưa có dữ liệu')
                  },
                ].map(item => (
                    <div key={item.label} className={`p-3 rounded-lg ${item.color}`}>
                        <div className="flex justify-between items-center">
                            <span className="font-semibold">{item.label}</span>
                            <span className="font-bold text-xs px-2 py-0.5 rounded-full ">{item.status}</span>
                        </div>
                        <p className="text-xs mt-1 opacity-80">{item.detail}</p>
                    </div>
                ))}
              </div>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-lg">
              <h2 className="text-lg font-semibold mb-4 text-gray-700 flex items-center">
                <Lightbulb className="w-5 h-5 mr-2 text-green-500" />
                Khuyến nghị hàng đầu
              </h2>
              <div className="space-y-3">
                {smartRecsForHome.length > 0 ? smartRecsForHome.map((rec, index) => (
                  <div key={index} className={`p-3 rounded-lg border-l-4 shadow-sm ${
                    rec.priority === 'high' ? 'bg-red-50 border-red-500' :
                    rec.priority === 'medium' ? 'bg-yellow-50 border-yellow-500' :
                    'bg-blue-50 border-blue-400'
                  }`}>
                    <div className="flex items-start">
                      <rec.icon className={`w-4 h-4 mr-2.5 mt-0.5 flex-shrink-0 ${
                        rec.priority === 'high' ? 'text-red-500' :
                        rec.priority === 'medium' ? 'text-yellow-500' :
                        'text-blue-500'
                      }`} />
                      <div className="flex-1">
                        <p className="font-medium text-gray-800 text-sm">{rec.title}</p>
                        <p className="text-xs text-gray-600 mt-0.5">{rec.description}</p>
                        <p className="text-xs font-semibold text-gray-700 mt-1">➡️ {rec.action}</p>
                      </div>
                    </div>
                  </div>
                )) : (
                  <div className="text-center py-6 text-gray-500">
                    <CheckCircle className="w-10 h-10 mx-auto mb-2 text-green-400" />
                    <p className="text-sm">Hệ thống hoạt động tối ưu, không có khuyến nghị đặc biệt!</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </main>

        <div className="fixed bottom-6 right-6 z-40 flex flex-col gap-3">
          <BubbleIcon type="phone" onClick={() => window.open("tel:+1234567890")} size="md" />
          <BubbleIcon type="zalo" href="https://zalo.me/your_zalo_id" size="md" />
          {/* <BubbleIcon type="tiktok" href="https://tiktok.com/@your_profile" size="md" /> */}
        </div>
        
        <Footer />
      </div>
    </div>
  );
};

export default Home;