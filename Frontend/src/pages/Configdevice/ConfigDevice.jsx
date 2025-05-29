// src/pages/Configdevice/ConfigDevice.jsx
import React, { useState, useEffect, useCallback } from "react";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Sidebar from "../../components/Sidebar";
import deviceControlService from "../../utils/deviceControlService"; // Updated service
import { Clock, Sun, Settings, Droplet, Power, Zap, AlertTriangle, CheckCircle, RefreshCw, Info } from "lucide-react";
import Modal from "../../components/Modal";
import { useAuth, PermissionGate, PERMISSIONS } from "../../contexts/AuthContext";
import NotificationToast from "../../components/NotificationToast";

const ConfigDevice = () => {
  const { hasPermission } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [notification, setNotification] = useState({ show: false, message: "", type: "success" });

  // --- Pump State ---
  const [pumpRunning, setPumpRunning] = useState(false);
  const [pumpSpeed, setPumpSpeed] = useState(50); // UI state, sent on demand
  const [pumpMode, setPumpMode] = useState("manual"); // 'manual' or 'auto' from irrigation.auto.enabled
  const [pumpSystemData, setPumpSystemData] = useState(null); // Store full pump data from /control/status

  // --- Light State (NEEDS API CONFIRMATION) ---
  const [lightOn, setLightOn] = useState(false);
  const [lightIntensity, setLightIntensity] = useState(50); // UI state
  const [lightMode, setLightMode] = useState("manual"); // Needs backend state if light has auto mode
  // const [lightSystemData, setLightSystemData] = useState(null); // For full light device data

  // --- Thresholds (for auto modes, fetched from /system/config or /control/auto) ---
  // Pump (moisture based)
  const [moistureThresholds, setMoistureThresholds] = useState({ critical: 20, low: 30, optimal: 50 });
  const [originalMoistureThresholds, setOriginalMoistureThresholds] = useState({ critical: 20, low: 30, optimal: 50 }); // For modal reset

  // Light (lux based)
  const [lightSensorThresholds, setLightSensorThresholds] = useState({ min: 200, max: 10000, optimal_min: 1000, optimal_max: 7000 });
  const [originalLightSensorThresholds, setOriginalLightSensorThresholds] = useState({ min: 200, max: 10000, optimal_min: 1000, optimal_max: 7000 });

  // Modals
  const [showMoistureModal, setShowMoistureModal] = useState(false);
  const [showLightModal, setShowLightModal] = useState(false);
  
  // Debounce timers (still useful for sliders if not sending every change immediately)
  const [pumpDebounceTimer, setPumpDebounceTimer] = useState(null);
  const [lightDebounceTimer, setLightDebounceTimer] = useState(null);


  const showToast = (message, type = "success") => {
    setNotification({ show: true, message, type, onClose: () => setNotification(prev => ({ ...prev, show: false })) });
  };

  const fetchAllStatusAndConfig = useCallback(async () => {
    setIsLoading(true);
    let failCount = 0;
    try {
      // 1. Get full irrigation status (includes pump status and auto_irrigation.enabled for pumpMode)
      const statusRes = await deviceControlService.getIrrigationStatus();
      if (statusRes.success && statusRes.data) {
        const { pump, autoIrrigation } = statusRes.data;
        if (pump) {
          setPumpSystemData(pump);
          setPumpRunning(pump.is_on);
          // pump.speed_percent or similar would be ideal from backend if pump has variable speed GET.
          // For now, pumpSpeed is a local UI state.
        }
        if (autoIrrigation) {
          setPumpMode(autoIrrigation.enabled ? "auto" : "manual");
        }
      } else {
        failCount++;
        showToast(statusRes.error || "Không thể tải trạng thái hệ thống tưới.", "error");
      }

      // 2. Get Light Status (NEEDS API CONFIRMATION for light-specific status)
      // const lightStatusRes = await deviceControlService.getLightStatus();
      // if (lightStatusRes.success && lightStatusRes.data) {
      //   setLightSystemData(lightStatusRes.data);
      //   setLightOn(lightStatusRes.data.is_on);
      //   // setLightIntensity(lightStatusRes.data.intensity_percent);
      //   // setLightMode(lightStatusRes.data.auto_mode_enabled ? "auto" : "manual");
      // } else {
      //   // If no specific light status API, can rely on sensor data if it implies light is on/off
      //   // Or, if light state is only controlled via frontend, local state is fine.
      //   console.warn("Could not fetch specific light status:", lightStatusRes.error);
      // }
      
      // 3. Get Auto-Irrigation Config (for moisture thresholds for pump's auto mode)
      const autoConfigRes = await deviceControlService.getAutoIrrigationConfig(); // Calls GET /control/auto
      if (autoConfigRes.success && autoConfigRes.data?.moisture_thresholds) {
        setMoistureThresholds(autoConfigRes.data.moisture_thresholds);
        setOriginalMoistureThresholds(autoConfigRes.data.moisture_thresholds);
      } else {
         failCount++;
         showToast(autoConfigRes.error || "Không thể tải cấu hình tưới tự động.", "error");
      }

      // 4. Get System Config (for light sensor thresholds for light's auto mode)
      const lightConfigRes = await deviceControlService.getSystemConfiguration("sensors.light.thresholds");
      if (lightConfigRes.success && lightConfigRes.data?.value) { // path specific response {path, value}
        setLightSensorThresholds(lightConfigRes.data.value);
        setOriginalLightSensorThresholds(lightConfigRes.data.value);
      } else {
         failCount++;
         // Don't show error if path simply not found vs. actual API error
         if(lightConfigRes.error && !lightConfigRes.error.includes("not found")) {
            showToast(lightConfigRes.error || "Không thể tải cấu hình ngưỡng sáng.", "error");
         } else if (!lightConfigRes.data?.value) {
            console.warn("Light sensor thresholds not found in config or API error:", lightConfigRes.error);
         }
      }

      if (failCount === 0) showToast("Tải cấu hình thành công!", "success")

    } catch (error) { // Catch errors from the service calls themselves if not handled inside
      console.error("Critical error fetching initial device configs:", error);
      showToast("Lỗi nghiêm trọng khi tải dữ liệu cấu hình.", "error");
    } finally {
      setIsLoading(false);
    }
  }, []); // useCallback dependencies are empty as it's a "load on mount" type function

  useEffect(() => {
    fetchAllStatusAndConfig();
  }, [fetchAllStatusAndConfig]);

  // --- PUMP ACTIONS ---
  const handleTogglePump = async () => {
    if (pumpMode === "auto") {
      showToast("Bơm đang ở chế độ tự động. Chuyển sang thủ công để điều khiển.", "info");
      return;
    }
    if (!hasPermission(PERMISSIONS.CONTROL_IRRIGATION)) { // Using CONTROL_IRRIGATION
      showToast("Bạn không có quyền điều khiển bơm.", "error");
      return;
    }
    
    const action = pumpRunning ? 'off' : 'on';
    // For 'on', if we want to use the current pumpSpeed slider value:
    // We need to confirm if `POST /control/pump/on` API can take speed or if there's a separate API for setting speed
    // Currently, API doc `POST /control/pump/on?duration=X` doesn't mention speed.
    // Let's assume for now pump runs at a default speed, or its speed is managed by another mechanism not in API.
    // If you pass `duration=0` or very small for a speed change, it might just run for that short time.
    // Backend needs to support setting speed for manual "ON" or have an "ADJUST_SPEED" endpoint.
    // For now, toggle only changes on/off. Speed slider could set a *target* speed for the *next* ON operation.
    
    showToast(`Đang ${action === 'on' ? 'bật' : 'tắt'} bơm...`, "info");
    setIsLoading(true);
    const result = await deviceControlService.controlPump(action, { duration: action === 'on' ? 300 : null }); // Default 5 min if turning on
    setIsLoading(false);

    if (result.success) {
      showToast(`Bơm đã ${action === 'on' ? 'BẬT' : 'TẮT'} thành công. (${result.data.message || ''})`, "success");
      // State (pumpRunning) will be updated by fetchAllStatusAndConfig or specific getPumpStatus in service
    } else {
      showToast(`Lỗi khi ${action === 'on' ? 'bật' : 'tắt'} bơm: ${result.error}. ${result.details?.reason || ''} ${result.details?.time_remaining ? `(Chờ ${Math.ceil(result.details.time_remaining/60)} phút)`: '' }`, "error");
    }
  };
  
  const sendPumpSpeedToServer = async (speedValue) => {
    // THIS FUNCTION NEEDS A CONFIRMED API ENDPOINT
    // Example: API `POST /control/pump/set-speed` with body `{ speed_percent: X }`
    // OR, if `POST /control/pump/on` accepts speed.
    // For now, this function won't make an API call if pump is ON and in manual mode.
    // It would be part of the 'ON' command.
    console.log(`(Simulated) Pump speed set to: ${speedValue}% via API if pump is running & manual.`);
    // try {
    //   await api.post(API_ENDPOINTS.CORE_OPERATIONS.SET_PUMP_SPEED_ENDPOINT, { value: speedValue / 100 });
    //   showToast(`Tốc độ bơm đã được yêu cầu: ${speedValue}%`, "info");
    // } catch (error) { /* ... */ }
  };
  const handlePumpSpeedChange = (newSpeed) => {
    if (!hasPermission(PERMISSIONS.CONFIGURE_DEVICES)) { /* or CONTROL_IRRIGATION if speed is part of control */
      showToast("Bạn không có quyền thay đổi tốc độ bơm.", "error");
      return;
    }
    setPumpSpeed(newSpeed); // Update UI state
    if (pumpMode === "manual" && pumpRunning) { // Only send if pump is ON and in MANUAL mode
      if (pumpDebounceTimer) clearTimeout(pumpDebounceTimer);
      setPumpDebounceTimer(setTimeout(() => sendPumpSpeedToServer(newSpeed), 700));
    }
  };


  // --- LIGHT ACTIONS (NEEDS API CONFIRMATION) ---
  const handleToggleLight = async () => {
    if (lightMode === "auto") {
      showToast("Đèn đang ở chế độ tự động. Chuyển thủ công để điều khiển.", "info");
      return;
    }
    if (!hasPermission(PERMISSIONS.CONTROL_IRRIGATION)) { // Assuming same perm, or create PERMISSIONS.CONTROL_LIGHTING
      showToast("Bạn không có quyền điều khiển đèn.", "error");
      return;
    }
    const newLightState = !lightOn;
    showToast(`Đang ${newLightState ? 'bật' : 'tắt'} đèn...`, "info");
    setIsLoading(true);
    // Pass current intensity if turning on
    const result = await deviceControlService.controlLight(newLightState ? 'on' : 'off', { intensity: newLightState ? lightIntensity : 0 });
    setIsLoading(false);
    if (result.success) {
      setLightOn(newLightState); // Optimistic update, or re-fetch status
      showToast(`Đèn đã ${newLightState ? "BẬT" : "TẮT"}.`, "success");
    } else {
      showToast(`Lỗi ${newLightState ? "bật" : "tắt"} đèn: ${result.error}`, "error");
    }
  };

  const sendLightIntensityToServer = async (intensityValue) => {
    // Assumes deviceControlService.controlLight('on', { intensity }) handles this
    // or there's a specific "set_intensity" API.
    console.log(`(Simulated) Light intensity set to: ${intensityValue}% via API if light is running & manual.`);
    // Example:
    // const result = await deviceControlService.controlLight('set_intensity', { intensity: intensityValue });
    // if (result.success) showToast(...) else showToast(..., "error");
  };
  const handleLightIntensityChange = (newIntensity) => {
     if (!hasPermission(PERMISSIONS.CONFIGURE_DEVICES)) {
      showToast("Bạn không có quyền thay đổi cường độ sáng.", "error");
      return;
    }
    setLightIntensity(newIntensity);
    if (lightMode === "manual" && lightOn) {
        if (lightDebounceTimer) clearTimeout(lightDebounceTimer);
        setLightDebounceTimer(setTimeout(() => sendLightIntensityToServer(newIntensity), 700));
    }
  };

  // --- MODE TOGGLES ---
  const handleToggleDeviceMode = async (deviceType, currentMode) => {
    if (!hasPermission(PERMISSIONS.CONFIGURE_DEVICES)) {
      showToast(`Bạn không có quyền thay đổi chế độ ${deviceType === 'pump' ? 'bơm' : 'đèn'}.`, "error");
      return;
    }
    const newMode = currentMode === "manual" ? "auto" : "manual";
    showToast(`Đang chuyển chế độ ${deviceType === 'pump' ? 'bơm' : 'đèn'} sang ${newMode}...`, "info");
    setIsLoading(true);
    const result = await deviceControlService.setDeviceMode(deviceType, newMode);
    setIsLoading(false);
    
    if (result.success) {
      showToast(`Chế độ ${deviceType === 'pump' ? 'bơm' : 'đèn'} đã chuyển sang ${newMode === "auto" ? "Tự động" : "Thủ công"}.`, "success");
      if (deviceType === 'pump') setPumpMode(newMode);
      if (deviceType === 'light') setLightMode(newMode);
      // fetchAllStatusAndConfig(); // Re-fetch to confirm state from backend
    } else {
      showToast(`Lỗi cập nhật chế độ ${deviceType === 'pump' ? 'bơm' : 'đèn'}: ${result.error}.`, "error");
    }
  };

  // --- SAVE THRESHOLDS ---
  const handleSaveMoistureThreshold = async () => {
    if (!hasPermission(PERMISSIONS.CONFIGURE_DEVICES)) {
      showToast("Bạn không có quyền cấu hình ngưỡng.", "error"); return;
    }
    if (parseFloat(moistureThresholds.low) <= parseFloat(moistureThresholds.critical) || 
        parseFloat(moistureThresholds.optimal) <= parseFloat(moistureThresholds.low)) {
        showToast("Thứ tự ngưỡng độ ẩm không hợp lệ (Critical < Low < Optimal).", "error"); return;
    }
    setIsLoading(true);
    // PUT to /control/auto for the entire auto-irrigation config block
    const currentAutoConfig = await deviceControlService.getAutoIrrigationConfig();
    let payload = { moisture_thresholds: moistureThresholds };
    if (currentAutoConfig.success && currentAutoConfig.data) {
        payload = { ...currentAutoConfig.data, moisture_thresholds: moistureThresholds };
    } else {
        showToast("Không lấy được cấu hình tưới tự động hiện tại, chỉ cập nhật ngưỡng.", "warning");
    }

    const result = await deviceControlService.updateAutoIrrigationConfig(payload);
    setIsLoading(false);
    if (result.success) {
      setOriginalMoistureThresholds(moistureThresholds);
      showToast("Lưu ngưỡng độ ẩm đất thành công!", "success");
      setShowMoistureModal(false);
    } else {
      showToast(`Lỗi lưu ngưỡng độ ẩm: ${result.error}. ${result.details?.message || ''}`, "error");
    }
  };
  
  const handleSaveLightThreshold = async () => {
    if (!hasPermission(PERMISSIONS.CONFIGURE_DEVICES)) {
      showToast("Bạn không có quyền cấu hình ngưỡng.", "error"); return;
    }
     if (parseFloat(lightSensorThresholds.optimal_min) <= parseFloat(lightSensorThresholds.min) || 
        parseFloat(lightSensorThresholds.max) <= parseFloat(lightSensorThresholds.optimal_max) ||
        parseFloat(lightSensorThresholds.optimal_max) <= parseFloat(lightSensorThresholds.optimal_min) ) {
        showToast("Thứ tự ngưỡng ánh sáng không hợp lệ.", "error"); return;
    }
    setIsLoading(true);
    // PUT to /system/config for path "sensors.light.thresholds"
    const result = await deviceControlService.updateSystemConfiguration("sensors.light.thresholds", lightSensorThresholds);
    setIsLoading(false);
    if (result.success) {
      setOriginalLightSensorThresholds(lightSensorThresholds);
      showToast("Lưu ngưỡng ánh sáng thành công!", "success");
      setShowLightModal(false);
    } else {
      showToast(`Lỗi lưu ngưỡng ánh sáng: ${result.error}. ${result.details?.message || ''}`, "error");
    }
  };
  
  // Logic auto control đã được loại bỏ vì giả định backend xử lý dựa trên config enabled/disabled.

  if (isLoading && !pumpSystemData) { // More specific initial loading
    return (
      <div className="flex min-h-screen"> <Sidebar />
        <div className="flex flex-col w-5/6 items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-blue-500"></div>
          <p className="mt-4 text-lg">Đang tải cấu hình & trạng thái thiết bị...</p>
        </div>
      </div>
    );
  }
  
  // Render helper for sliders
  const renderSlider = (id, label, value, onChange, min, max, unit, disabled) => (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
        {label}: {value}{unit}
      </label>
      <input type="range" id={id} min={min} max={max} value={value || 0}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className={`w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500
                    ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        disabled={disabled || isLoading} // Disable also if another action is loading
      />
    </div>
  );
  
  // Render helper for mode toggle switch
  const renderModeSwitch = (id, label, currentMode, onToggle) => (
    <div className="flex items-center justify-between mt-4 pt-4 border-t">
      <label htmlFor={id} className="text-sm font-medium text-gray-700">{label} (Tự động)</label>
      <button id={id} onClick={onToggle} disabled={isLoading}
        className={`relative inline-flex items-center h-6 rounded-full w-11 transition-colors duration-200 ease-in-out 
                    focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-70
                    ${currentMode === 'auto' ? 'bg-blue-600' : 'bg-gray-300'}`}
      >
        <span className={`inline-block w-4 h-4 transform bg-white rounded-full transition-transform duration-200 ease-in-out 
                        ${currentMode === 'auto' ? 'translate-x-6' : 'translate-x-1'}`} />
      </button>
    </div>
  );

  return (
    <div className="flex min-h-screen"><Sidebar />
      <div className="flex flex-col w-5/6 min-h-screen bg-gray-50">
        <Header />
        {notification.show && (
          <NotificationToast
            message={notification.message} type={notification.type} onClose={notification.onClose}
          />
        )}
        <main className="flex-grow p-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-3xl font-bold text-gray-800">
                Quản lý & Cấu hình Thiết bị
            </h1>
            <button onClick={fetchAllStatusAndConfig} disabled={isLoading}
                className="flex items-center px-3 py-1.5 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50 text-sm">
                <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                {isLoading ? 'Đang tải...' : 'Tải lại tất cả'}
            </button>
          </div>
          

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {/* Pump Control Card */}
            <div className="bg-white p-6 rounded-xl shadow-lg">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center"><div className="bg-blue-100 rounded-full p-3 mr-3"><Droplet className="text-blue-500 w-6 h-6" /></div><h2 className="text-xl font-semibold text-gray-700">Bơm Nước</h2></div>
                <PermissionGate permission={PERMISSIONS.CONFIGURE_DEVICES}>
                    <button className="p-2 rounded-full hover:bg-gray-200 transition-colors" onClick={() => setShowMoistureModal(true)} aria-label="Cấu hình ngưỡng độ ẩm" disabled={isLoading}> <Settings className="w-5 h-5 text-gray-500" /></button>
                </PermissionGate>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
                <div className={`bg-gray-50 rounded-lg p-3 border-l-4 ${pumpRunning ? 'border-green-400' : 'border-red-400'}`}><p className="text-xs text-gray-500 uppercase">Trạng thái</p><p className={`font-semibold ${pumpRunning ? "text-green-600" : "text-red-600"}`}>{pumpRunning ? "Đang chạy" : "Đã tắt"}</p></div>
                <div className="bg-gray-50 rounded-lg p-3 border-l-4 border-blue-400"><p className="text-xs text-gray-500 uppercase">Chế độ</p><p className="font-semibold text-blue-600">{pumpMode === "manual" ? "Thủ công" : "Tự động"}</p></div>
              </div>
              <PermissionGate permission={PERMISSIONS.CONTROL_IRRIGATION}>
                <div className="mb-4"><button onClick={handleTogglePump} disabled={isLoading || (pumpMode === 'auto')} className={`w-full py-2.5 px-4 rounded-lg font-semibold transition-all flex items-center justify-center ${pumpMode === 'auto' ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : (pumpRunning ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-green-500 hover:bg-green-600 text-white')}`}><Power className="w-5 h-5 mr-2" />{pumpRunning ? "TẮT BƠM" : "BẬT BƠM"}</button></div>
              </PermissionGate>
              <PermissionGate permission={PERMISSIONS.CONFIGURE_DEVICES}> {/* Or CONTROL_IRRIGATION */}
                 {renderSlider("pumpSpeed", "Tốc độ bơm (mục tiêu)", pumpSpeed, handlePumpSpeedChange, 0, 100, "%", pumpMode === 'auto')}
              </PermissionGate>
              <PermissionGate permission={PERMISSIONS.CONFIGURE_DEVICES}>
                {renderModeSwitch("pumpModeToggle", "Chế độ bơm", pumpMode, () => handleToggleDeviceMode('pump', pumpMode))}
              </PermissionGate>
            </div>

            {/* Light System Control Card - NEEDS API CONFIRMATION FOR FULL FUNCTIONALITY */}
            <div className="bg-white p-6 rounded-xl shadow-lg">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center"><div className="bg-yellow-100 rounded-full p-3 mr-3"><Sun className="text-yellow-500 w-6 h-6" /></div><h2 className="text-xl font-semibold text-gray-700">Hệ thống Đèn</h2></div>
                <PermissionGate permission={PERMISSIONS.CONFIGURE_DEVICES}>
                    <button className="p-2 rounded-full hover:bg-gray-200 transition-colors" onClick={() => setShowLightModal(true)} aria-label="Cấu hình ngưỡng sáng" disabled={isLoading}><Settings className="w-5 h-5 text-gray-500" /></button>
                </PermissionGate>
              </div>
               <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
                <div className={`bg-gray-50 rounded-lg p-3 border-l-4 ${lightOn ? 'border-green-400' : 'border-red-400'}`}><p className="text-xs text-gray-500 uppercase">Trạng thái</p><p className={`font-semibold ${lightOn ? "text-green-600" : "text-red-600"}`}>{lightOn ? "Đang bật" : "Đã tắt"}</p></div>
                <div className="bg-gray-50 rounded-lg p-3 border-l-4 border-yellow-400"><p className="text-xs text-gray-500 uppercase">Chế độ</p><p className="font-semibold text-yellow-600">{lightMode === "manual" ? "Thủ công" : "Tự động"}</p></div>
              </div>
              <PermissionGate permission={PERMISSIONS.MANAGE_DEVICES}> {/* Assuming new permission or reuse */}
                <div className="mb-4"><button onClick={handleToggleLight} disabled={isLoading || lightMode === 'auto'} className={`w-full py-2.5 px-4 rounded-lg font-semibold transition-all flex items-center justify-center ${lightMode === 'auto' ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : (lightOn ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-yellow-500 hover:bg-yellow-600 text-white')}`}><Zap className="w-5 h-5 mr-2" />{lightOn ? "TẮT ĐÈN" : "BẬT ĐÈN"}</button></div>
              </PermissionGate>
               <PermissionGate permission={PERMISSIONS.CONFIGURE_DEVICES}>
                {renderSlider("lightIntensity", "Cường độ sáng", lightIntensity, handleLightIntensityChange, 0, 100, "%", lightMode === 'auto')}
              </PermissionGate>
              <PermissionGate permission={PERMISSIONS.CONFIGURE_DEVICES}>
                {renderModeSwitch("lightModeToggle", "Chế độ đèn", lightMode, () => handleToggleDeviceMode('light', lightMode))}
              </PermissionGate>
            </div>
          </div>
          
          <PermissionGate permission={PERMISSIONS.CONFIGURE_DEVICES}>
            <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-xl font-semibold mb-6 text-center text-gray-700">Cấu hình Ngưỡng Tự động</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"><div className="flex items-center mb-2"><Droplet className="w-5 h-5 text-blue-500 mr-2"/><h3 className="text-lg font-medium text-gray-700">Ngưỡng Độ ẩm Đất (cho Bơm)</h3></div><p className="text-sm text-gray-500 mb-3">Bơm sẽ tự động dựa trên các ngưỡng này khi ở chế độ tự động.</p><p className="text-sm mb-1">Nguy cấp: {moistureThresholds.critical}%, Thấp: {moistureThresholds.low}%, Tối ưu: {moistureThresholds.optimal}%</p><button onClick={() => setShowMoistureModal(true)} disabled={isLoading} className="w-full mt-2 px-4 py-2 bg-blue-500 text-white text-sm rounded-md hover:bg-blue-600 transition disabled:opacity-60">Thay đổi</button></div>
                    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"><div className="flex items-center mb-2"><Sun className="w-5 h-5 text-yellow-500 mr-2"/><h3 className="text-lg font-medium text-gray-700">Ngưỡng Ánh sáng (cho Đèn)</h3></div><p className="text-sm text-gray-500 mb-3">Đèn sẽ tự động dựa trên các ngưỡng này khi ở chế độ tự động (nếu được hỗ trợ).</p><p className="text-sm mb-1">Min Lux: {lightSensorThresholds.min}, Max Lux: {lightSensorThresholds.max}</p><button onClick={() => setShowLightModal(true)} disabled={isLoading} className="w-full mt-2 px-4 py-2 bg-yellow-500 text-white text-sm rounded-md hover:bg-yellow-600 transition disabled:opacity-60">Thay đổi</button></div>
                </div>
            </div>
          </PermissionGate>
        </main>

        {['critical', 'low', 'optimal'].map(key => (
          <div key={key}>
            <label htmlFor={`moisture_${key}`} className="block text-sm font-medium text-gray-700 mb-1">Ngưỡng {key === 'critical' ? 'Nguy cấp' : key === 'low' ? 'Thấp' : 'Tối ưu'} (%):</label>
            <input id={`moisture_${key}`} type="number" value={moistureThresholds[key]} onChange={(e) => setMoistureThresholds(prev => ({...prev, [key]: parseFloat(e.target.value)}))} className="w-full border border-gray-300 rounded-md shadow-sm p-2 focus:ring-blue-500 focus:border-blue-500" />
          </div>
        ))}
        <div className="flex justify-end gap-3 pt-3">
          <button type="button" onClick={() => {setShowMoistureModal(false); setMoistureThresholds(originalMoistureThresholds);}} className="px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300">Hủy</button>
          <button onClick={handleSaveMoistureThreshold} disabled={isLoading} className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50">{isLoading ? "Đang lưu..." : "Lưu ngưỡng"}</button>
        </div>

        <Modal isOpen={showLightModal} onClose={() => setShowLightModal(false)} title="Thiết lập ngưỡng cảm biến ánh sáng (Đèn tự động)">
          <div className="space-y-4">
            {(['min', 'max', 'optimal_min', 'optimal_max']).map(key => (
                <div key={key}>
                    <label htmlFor={`light_${key}`} className="block text-sm font-medium text-gray-700 mb-1">Ngưỡng {key.replace('_', ' ')} (Lux):</label>
                    <input id={`light_${key}`} type="number" value={lightSensorThresholds[key]} onChange={(e) => setLightSensorThresholds(prev => ({...prev, [key]: parseFloat(e.target.value)}))} className="w-full border border-gray-300 rounded-md shadow-sm p-2 focus:ring-yellow-500 focus:border-yellow-500" />
                </div>
            ))}
             <div className="flex justify-end gap-3 pt-3">
                <button type="button" onClick={() => {setShowLightModal(false); setLightSensorThresholds(originalLightSensorThresholds);}} className="px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300">Hủy</button>
                <button onClick={handleSaveLightThreshold} disabled={isLoading} className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50">{isLoading ? "Đang lưu..." : "Lưu ngưỡng"}</button>
            </div>
          </div>
        </Modal>
        <Footer />
      </div>
    </div>
  );
};

export default ConfigDevice;