// src/pages/Home/Home.jsx
import React, { useState, useEffect, useCallback, useMemo } from "react"; // Added useMemo
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Sidebar from "../../components/Sidebar";
import BubbleIcon from "../../components/BubbleIcon";
import { useSensorData } from "../../hooks/useSensorData";
import Loading from "../../components/Loading";
import DevicesCard from "../Devices/DevicesCard";
import NotificationButton from "../../components/NotificationButton";
import { AlertTriangle, CheckCircle, Activity, Lightbulb, Droplet, Info, Wifi, WifiOff, RefreshCw } from "lucide-react";

// Helper function to compare arrays of alert objects
const areAlertsEqual = (alertsA, alertsB) => {
  if (!alertsA && !alertsB) return true; // both null or undefined
  if (!alertsA || !alertsB) return false; // one is null/undefined, other is not
  if (alertsA.length !== alertsB.length) return false;
  // Using JSON.stringify for simplicity. For better performance, a deep comparison specific to alert structure is recommended.
  return JSON.stringify(alertsA) === JSON.stringify(alertsB);
};

const Home = () => {
  const [showDetailedAlerts, setShowDetailedAlerts] = useState(false);
  const [priorityAlerts, setPriorityAlerts] = useState([]);

  const {
    sensors,
    loading,
    error: rawError,
    lastUpdated: lastUpdate,
    refresh: refreshData,
    getOverallStatus,
    isOnline,
    data: fullSensorDataResponse,
  } = useSensorData({
    autoRefresh: true,
    refreshInterval: 45000,
  });

  const { temperature = {}, moisture = {}, light = {}, soil = {} } = sensors;
  
  const overallStatusFromHook = getOverallStatus(); // This is a string from the hook
  const overallAnalysisSummary = fullSensorDataResponse?.analysis_summary;
  const overallIrrigationRecommendations = fullSensorDataResponse?.irrigation_recommendation;
  const hookError = fullSensorDataResponse?.error || rawError;

  const derivedConnectionStatus = useMemo(() => {
    if (loading && !fullSensorDataResponse) return 'connecting';
    if (hookError) return 'error';
    if (isOnline) return 'connected';
    if (fullSensorDataResponse?.source === 'default_fallback_error' && !hookError) return 'error';
    return 'connecting'; // Default fallback, e.g. initial state before first successful fetch without error
  }, [loading, fullSensorDataResponse, hookError, isOnline]);
  
  // Specific dependencies for the priorityAlerts useEffect
  const tempStatus = temperature?.status;
  const tempValue = temperature?.value;
  const soilStatus = soil?.status;
  const soilValue = soil?.value;
  const moistureStatus = moisture?.status;
  const moistureValue = moisture?.value;
  // const lightStatus = light?.status; // Add if used in alert logic
  // const lightValue = light?.value;   // Add if used in alert logic

  useEffect(() => {
    const calculateAlerts = () => {
      const newAlerts = [];
      // Check if essential sensor data is available
      if (!fullSensorDataResponse?.sensors || Object.keys(sensors).length === 0) {
        return [];
      }

      const formatVal = (val, fixed = 1) => (typeof val !== 'undefined' && val !== null) ? parseFloat(val).toFixed(fixed) : 'N/A';

      if (soilStatus === 'critical' || soilStatus === 'critical_low') {
        newAlerts.push({
          id: 'soil_critical', type: 'critical', icon: Droplet, title: 'Đất rất khô',
          message: `Độ ẩm đất rất thấp: ${formatVal(soilValue)}%`, action: 'Cần tưới khẩn cấp!', priority: 1
        });
      }
      if (tempStatus === 'critical' || tempStatus === 'critical_high' || tempStatus === 'critical_low') {
        const formattedTempVal = formatVal(tempValue);
        const tempNumeric = parseFloat(formattedTempVal);
        newAlerts.push({
          id: 'temp_critical', type: 'critical', icon: AlertTriangle, title: tempNumeric > 38 ? 'Nhiệt độ quá cao' : (tempNumeric < 10 ? 'Nhiệt độ quá thấp' : 'Nhiệt độ nguy hiểm'),
          message: `Nhiệt độ ở mức nguy hiểm: ${formattedTempVal}°C`, action: 'Điều chỉnh nhiệt độ ngay!', priority: 1
        });
      }
      if (soilStatus === 'warning' || soilStatus === 'warning_low') {
        newAlerts.push({
          id: 'soil_warning', type: 'warning', icon: Droplet, title: 'Đất đang khô dần',
          message: `Độ ẩm đất: ${formatVal(soilValue)}%`, action: 'Xem xét tưới sớm.', priority: 2
        });
      }
      if (moistureStatus === 'warning' || moistureStatus === 'warning_low' || moistureStatus === 'warning_high') {
        newAlerts.push({
          id: 'humidity_warning', type: 'warning', icon: Activity, title: 'Độ ẩm không khí bất thường',
          message: `Độ ẩm không khí: ${formatVal(moistureValue)}%`, action: 'Kiểm tra hệ thống thông gió/tạo ẩm.', priority: 2
        });
      }

      if (derivedConnectionStatus === 'error' && hookError) {
        const errorMessageText = typeof hookError === 'string' ? hookError : (hookError.message || "Lỗi kết nối không xác định");
        newAlerts.push({
          id: 'connection_error', type: 'warning', icon: WifiOff, title: 'Mất kết nối cảm biến',
          message: errorMessageText.substring(0, 100) + (errorMessageText.length > 100 ? "..." : ""),
          action: 'Kiểm tra kết nối mạng và refresh.', priority: 2
        });
      }
      newAlerts.sort((a, b) => a.priority - b.priority);
      return newAlerts.slice(0, 3);
    };

    const newCalculatedAlerts = calculateAlerts();
    
    setPriorityAlerts(prevAlerts => {
      if (!areAlertsEqual(prevAlerts, newCalculatedAlerts)) {
        return newCalculatedAlerts;
      }
      return prevAlerts;
    });

  }, [
    // Specific, stable dependencies
    tempStatus, tempValue,
    soilStatus, soilValue,
    moistureStatus, moistureValue,
    // lightStatus, lightValue, // Add if light sensor alerts are implemented
    overallStatusFromHook, // String, stable if value doesn't change
    derivedConnectionStatus, // Memoized string, stable
    hookError, // Object/string, should be stable unless error truly changes
    // fullSensorDataResponse?.sensors is tricky as its reference might change.
    // The check `Object.keys(sensors).length === 0` depends on `sensors` ref.
    // However, the individual status/value deps should cover most cases.
    // If `sensors` object itself is needed for the empty check, we might need `JSON.stringify(sensors)`
    // or rely on `fullSensorDataResponse` directly for that initial check.
    // For now, the current deps are more granular. The initial check for empty sensors now relies on `sensors` directly from hook.
    sensors, // Added `sensors` back because `Object.keys(sensors).length === 0` uses it.
             // The `setPriorityAlerts` functional update should prevent loops if `sensors` changes ref but content for alerts is same.
    fullSensorDataResponse?.sensors // for the `!fullSensorDataResponse?.sensors` check
  ]);
  
  const createEnhancedCardsForHome = useCallback(() => {
    if (!sensors || Object.keys(sensors).length === 0 || !sensors.temperature?.feedId) {
      return [];
    }
    const calculateDisplayPercent = (sensorValue, sensorAnalysis, type) => {
        if (sensorAnalysis && sensorAnalysis.status) {
            switch (sensorAnalysis.status) {
                case "optimal": case "normal": return 85 + Math.random() * 15;
                case "warning": case "warning_low": case "warning_high": return 40 + Math.random() * 30;
                case "critical": case "critical_low": case "critical_high": return Math.random() * 30;
                default: return 50;
            }
        }
        // Fallback if no analysis or status in analysis
        if (typeof sensorValue === 'undefined' || sensorValue === null) return 0;
        const numericValue = parseFloat(sensorValue);
        if (isNaN(numericValue)) return 0;

        if (type === "temperature") return Math.min(Math.max(((numericValue - 0) / (50 - 0)) * 100, 0), 100);
        if (type === "moisture" || type === "soil") return Math.min(Math.max(numericValue, 0), 100);
        if (type === "light") return Math.min(Math.max(((numericValue - 0) / (2000 - 0)) * 100, 0), 100);
        return 50;
    };
    const sensorDetailsMap = {
        temperature: "Nhiệt độ không khí trong nhà kính.",
        moisture: "Độ ẩm không khí hiện tại.",
        light: "Mức độ ánh sáng cho cây quang hợp.",
        soil: "Độ ẩm của đất, chỉ số tưới tiêu."
    };

    return [sensors.temperature, sensors.moisture, sensors.light, sensors.soil].map(sensorData => {
      if (!sensorData || typeof sensorData.value === 'undefined') {
         let type = "unknown_sensor";
            if(sensorData === sensors.temperature) type="temperature";
            if(sensorData === sensors.moisture) type="moisture";
            if(sensorData === sensors.light) type="light";
            if(sensorData === sensors.soil) type="soil";
         return {
             type, title: "Cảm biến", value: "N/A", sub: "", percent: 0, detail: "Thiếu dữ liệu",
             feedId: "N/A", date: "N/A", time: "N/A", status: "error", analysis: null, recommendations: []
         };
      }
      let typeKey = sensorData.sensor_type || 'unknown'; 
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
        analysis: specificAnalysis,
        metadata: sensorData.metadata,
        recommendations: typeKey === 'soil' && overallIrrigationRecommendations ? 
            (Array.isArray(overallIrrigationRecommendations) ? overallIrrigationRecommendations : [overallIrrigationRecommendations]) 
            : (specificAnalysis?.recommendations || [])
      };
    });
  }, [sensors, overallIrrigationRecommendations]);


  const getSystemStatusSummary = useCallback(() => {
    if (overallStatusFromHook === 'error') {
        return { status: 'error', message: (typeof hookError === 'string' ? hookError : hookError?.message) || "Lỗi hệ thống, không thể xác định trạng thái.", color: 'text-red-600', bgColor: 'bg-red-50', borderColor: 'border-red-200', icon: AlertTriangle};
    }
    const criticalCount = priorityAlerts.filter(alert => alert.type === 'critical').length;
    const warningCount = priorityAlerts.filter(alert => alert.type === 'warning').length;
    
    if (overallStatusFromHook === 'critical' || criticalCount > 0) {
      return { status: 'critical', message: `Hệ thống có ${criticalCount || 1} vấn đề nghiêm trọng!`, color: 'text-red-600', bgColor: 'bg-red-50', borderColor: 'border-red-200', icon: AlertTriangle };
    }
    if (overallStatusFromHook === 'warning' || warningCount > 0) {
      return { status: 'warning', message: `Hệ thống có ${warningCount || 1} cảnh báo cần chú ý.`, color: 'text-yellow-600', bgColor: 'bg-yellow-50', borderColor: 'border-yellow-200', icon: AlertTriangle };
    }
    return { status: 'normal', message: 'Tất cả hệ thống hoạt động bình thường.', color: 'text-green-600', bgColor: 'bg-green-50', borderColor: 'border-green-200', icon: CheckCircle };
  }, [overallStatusFromHook, priorityAlerts, hookError]);


  const generateSmartRecommendationsForHome = useCallback(() => {
    if (!sensors || Object.keys(sensors).length === 0) return [];
    let recs = [];

    if (overallIrrigationRecommendations) {
        const recArray = Array.isArray(overallIrrigationRecommendations) ? overallIrrigationRecommendations : [overallIrrigationRecommendations];
        recArray.forEach(rec => {
            if (rec.action_items && Array.isArray(rec.action_items)) {
                recs = recs.concat(rec.action_items.map(item => ({
                    icon: item.action?.includes("water") ? Droplet : Info,
                    title: item.action?.replace(/_/g, ' ') || "Hành động được gợi ý",
                    description: item.details || rec.reason || "Dựa trên phân tích AI.",
                    action: item.priority ? `Ưu tiên: ${item.priority}` : "Nên thực hiện sớm",
                    priority: item.priority || 'medium'
                })));
            } else if (rec.needs_water) {
                 recs.push({
                    icon: Droplet, title: 'Khuyến nghị tưới',
                    description: rec.reason || `Độ ẩm đất cần điều chỉnh.`,
                    action: `Tưới với lượng ${rec.recommended_water_amount || 'phù hợp'}. Ưu tiên ${rec.urgency || 'trung bình'}`,
                    priority: rec.urgency || 'medium'
                });
            }
        });
    }

    const tempAnalysis = overallAnalysisSummary?.temperature;
    if (tempAnalysis && (tempAnalysis.status === 'warning' || tempAnalysis.status === 'critical')) {
        recs.push({
            icon: AlertTriangle, title: 'Nhiệt độ bất thường',
            description: tempAnalysis.description || `Nhiệt độ hiện tại ${temperature?.value ? parseFloat(temperature.value).toFixed(1) : 'N/A'}°C.`,
            action: tempAnalysis.stress_level === 'high' ? 'Cần điều chỉnh nhiệt độ gấp!' : 'Theo dõi và điều chỉnh nhiệt độ.',
            priority: tempAnalysis.stress_level === 'high' ? 'high' : 'medium'
        });
    }
    const lightAnalysis = overallAnalysisSummary?.light;
    if (lightAnalysis && (lightAnalysis.status === 'warning' || lightAnalysis.status === 'critical')) {
        recs.push({
            icon: Lightbulb, title: 'Ánh sáng không tối ưu',
            description: lightAnalysis.description || `Cường độ sáng ${light?.value ? parseFloat(light.value).toFixed(0) : 'N/A'} Lux.`,
            action: lightAnalysis.plant_impact !== 'good_growth' ? 'Điều chỉnh nguồn sáng bổ sung/che chắn.' : 'Theo dõi thêm.',
            priority: lightAnalysis.plant_impact !== 'good_growth' ? 'medium' : 'low'
        });
    }

    if (recs.length === 0 && overallStatusFromHook === 'normal') {
        recs.push({
            icon: CheckCircle, title: "Hệ thống ổn định",
            description: "Các chỉ số môi trường trong ngưỡng tối ưu.",
            action: "Tiếp tục theo dõi định kỳ.",
            priority: 'low'
        });
    }
    const priorityOrder = { 'high': 1, 'medium': 2, 'low': 3 };
    recs.sort((a, b) => (priorityOrder[a.priority] || 4) - (priorityOrder[b.priority] || 4));
    return recs.slice(0, 3);
  }, [sensors, overallIrrigationRecommendations, overallAnalysisSummary, overallStatusFromHook, temperature, light]);


  const homeCards = createEnhancedCardsForHome();
  const systemStatusSummary = getSystemStatusSummary();
  const smartRecsForHome = generateSmartRecommendationsForHome();

  if (loading && !fullSensorDataResponse) {
    return <Loading />;
  }
  if (hookError && !fullSensorDataResponse && !loading) {
    return (
        <div className="flex min-h-screen items-center justify-center p-4">
            <div className="text-center">
                <AlertTriangle size={48} className="mx-auto text-red-500 mb-4" />
                <h2 className="text-xl font-semibold text-red-700 mb-2">Không thể tải dữ liệu</h2>
                <p className="text-gray-600 mb-4">{typeof hookError === 'string' ? hookError : hookError.message}</p>
                <button
                    onClick={() => refreshData()}
                    className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-60"
                    disabled={loading}
                >
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    {loading ? 'Đang thử lại...' : 'Thử lại'}
                </button>
            </div>
        </div>
    );
  }
  
  const connectionStyling = () => {
     switch (derivedConnectionStatus) {
      case 'connected': return { color: 'text-green-600', icon: Wifi };
      case 'connecting': return { color: 'text-yellow-500', icon: Wifi };
      case 'error': return { color: 'text-red-500', icon: WifiOff };
      default: return { color: 'text-gray-500', icon: Wifi };
    }
  };
  const currentConnectionStyling = connectionStyling();

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-col flex-1 ml-64">
        <Header />
        <NotificationButton />
        <main className="flex-grow p-4 sm:p-6 bg-gray-100">
          <div className="mb-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-3">
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-gray-800">Tổng quan Nhà kính</h1>
                <p className="text-sm text-gray-500 mt-1 flex items-center">
                  <currentConnectionStyling.icon size={16} className={`mr-1.5 ${currentConnectionStyling.color}`} />
                  {derivedConnectionStatus === 'connected' ? 'Đã kết nối' : derivedConnectionStatus === 'error' ? `Lỗi kết nối` : 'Đang kết nối...'}
                  {lastUpdate && (<span className="hidden sm:inline">  • Cập nhật: {lastUpdate.toLocaleTimeString('vi-VN')}</span>)}
                </p>
              </div>
              <button
                onClick={() => refreshData()}
                className="mt-2 sm:mt-0 flex items-center px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm disabled:opacity-60"
                disabled={loading}
              >
                <RefreshCw className={`w-4 h-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Đang cập nhật...' : 'Làm mới'}
              </button>
            </div>
            {hookError && !loading && (
                 <div className="mb-4 p-3 bg-red-50 border-l-4 border-red-400 text-red-700 text-sm rounded-md">
                    <div className="flex items-center">
                      <AlertTriangle size={18} className="mr-2"/>
                      <p>{typeof hookError === 'string' ? hookError : hookError.message || "Đã xảy ra lỗi."}</p>
                    </div>
                </div>
            )}
            <div className={`p-4 rounded-lg border ${systemStatusSummary.bgColor} ${systemStatusSummary.borderColor} mb-6 shadow-sm`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <systemStatusSummary.icon className={`w-6 h-6 mr-3 ${systemStatusSummary.color}`} />
                  <div>
                    <p className={`font-semibold ${systemStatusSummary.color}`}>Trạng thái hệ thống</p>
                    <p className={`text-sm ${systemStatusSummary.color.replace('600', '700')}`}>{systemStatusSummary.message}</p>
                  </div>
                </div>
                {priorityAlerts.length > 0 && (
                  <button
                    onClick={() => setShowDetailedAlerts(!showDetailedAlerts)}
                    className={`px-3 py-1 rounded text-sm font-medium hover:bg-opacity-20 transition-colors
                                ${systemStatusSummary.color === 'text-red-600' ? 'text-red-600 hover:bg-red-100' :
                                  systemStatusSummary.color === 'text-yellow-600' ? 'text-yellow-600 hover:bg-yellow-100' :
                                  'text-green-600 hover:bg-green-100'}`}
                  >{showDetailedAlerts ? 'Ẩn' : 'Chi tiết'} ({priorityAlerts.length})</button>
                )}
              </div>
            </div>
          </div>
          {showDetailedAlerts && priorityAlerts.length > 0 && (
            <div className="mb-6 space-y-3 animate-fadeIn">
              <h3 className="text-md font-semibold text-gray-700 mb-1">Cảnh báo ưu tiên:</h3>
              {priorityAlerts.map((alert) => (
                <div key={alert.id} className={`p-3 rounded-lg border-l-4 shadow-sm ${alert.type === 'critical' ? 'bg-red-50 border-red-500' : 'bg-yellow-50 border-yellow-500'}`}>
                  <div className="flex items-start">
                    <alert.icon className={`w-5 h-5 mr-2.5 mt-0.5 flex-shrink-0 ${alert.type === 'critical' ? 'text-red-500' : 'text-yellow-500'}`} />
                    <div className="flex-1">
                      <p className={`font-medium text-sm ${alert.type === 'critical' ? 'text-red-800' : 'text-yellow-800'}`}>{alert.title}</p>
                      <p className={`text-xs mt-0.5 ${alert.type === 'critical' ? 'text-red-700' : 'text-yellow-700'}`}>{alert.message}</p>
                      <p className={`text-xs font-semibold mt-1 ${alert.type === 'critical' ? 'text-red-600' : 'text-yellow-600'}`}>➡️ {alert.action}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6 mb-8">
            {homeCards.map((cardProps, index) => (<div key={cardProps.type || index} className="h-64"><DevicesCard {...cardProps} /></div>))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-xl shadow-lg">
              <h2 className="text-lg font-semibold mb-4 text-gray-700 flex items-center"><Activity className="w-5 h-5 mr-2 text-blue-500" />Trạng thái Hoạt động Dự kiến</h2>
              <div className="space-y-3 text-sm text-gray-600">
                {[
                  { label: "Bơm tưới", status: (soil?.analysis?.needs_water || overallIrrigationRecommendations?.needs_water) ? "Sắp tưới" : "Không cần tưới", color: (soil?.analysis?.needs_water || overallIrrigationRecommendations?.needs_water) ? "text-blue-600 bg-blue-50" : "text-gray-700 bg-gray-50", detail: soil?.analysis?.description || overallIrrigationRecommendations?.reason || (soil?.value ? `Độ ẩm đất: ${parseFloat(soil.value).toFixed(1)}%` : 'Chưa có dữ liệu')},
                  { label: "Đèn chiếu sáng", status: light?.analysis?.status === 'warning_low' || (light?.value && parseFloat(light.value) < 500) ? "Nên bật" : "Đủ sáng", color: light?.analysis?.status === 'warning_low' || (light?.value && parseFloat(light.value) < 500) ? "text-yellow-700 bg-yellow-50" : "text-gray-700 bg-gray-50", detail: light?.analysis?.description || (light?.value ? `Cường độ: ${parseFloat(light.value).toFixed(0)} Lux` : 'Chưa có dữ liệu')},
                  { label: "Thông gió/Làm mát", status: temperature?.analysis?.status === 'warning_high' || (temperature?.value && parseFloat(temperature.value) > 30) ? "Nên bật" : "Nhiệt độ ổn", color: temperature?.analysis?.status === 'warning_high' || (temperature?.value && parseFloat(temperature.value) > 30) ? "text-orange-600 bg-orange-50" : "text-gray-700 bg-gray-50", detail: temperature?.analysis?.description || (temperature?.value ? `Nhiệt độ: ${parseFloat(temperature.value).toFixed(1)}°C` : 'Chưa có dữ liệu')},
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
              <h2 className="text-lg font-semibold mb-4 text-gray-700 flex items-center"><Lightbulb className="w-5 h-5 mr-2 text-green-500" />Khuyến nghị hàng đầu</h2>
              <div className="space-y-3">
                {smartRecsForHome.length > 0 ? smartRecsForHome.map((rec, index) => (
                  <div key={index} className={`p-3 rounded-lg border-l-4 shadow-sm ${rec.priority === 'high' ? 'bg-red-50 border-red-500' : rec.priority === 'medium' ? 'bg-yellow-50 border-yellow-500' : 'bg-blue-50 border-blue-400'}`}>
                    <div className="flex items-start">
                      <rec.icon className={`w-4 h-4 mr-2.5 mt-0.5 flex-shrink-0 ${rec.priority === 'high' ? 'text-red-500' : rec.priority === 'medium' ? 'text-yellow-500' : 'text-blue-500'}`} />
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
        </div>
        <Footer />
      </div>
    </div>
  );
};

export default Home;