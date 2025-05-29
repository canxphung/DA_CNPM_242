// components/DeviceStatusMonitor.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { 
  Activity, Droplets, Clock, AlertTriangle, CheckCircle, Power,
  Settings, TrendingUp, Zap
} from 'lucide-react';
import deviceControlService from '../utils/deviceControlService'; // Service đã được giả định là có các hàm gọi API mới
import { API_ENDPOINTS } from '../utils/constants'; // Để biết rõ endpoint nào đang được gọi

const DeviceStatusMonitor = ({ refreshInterval = 30000 }) => {
  const [systemStatus, setSystemStatus] = useState(null); // From /control/status
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchSystemStatus = useCallback(async () => {
    try {
      setLoading(true);
      console.log('Fetching comprehensive system status (DeviceStatusMonitor)...');
      
      // deviceControlService.getIrrigationStatus() sẽ gọi API_ENDPOINTS.CORE_OPERATIONS.CONTROL.STATUS
      // và trả về { success: true, data: enhancedStatus } hoặc { success: false, error, cachedData }
      const result = await deviceControlService.getIrrigationStatus();
      
      if (result.success) {
        setSystemStatus(result.data); // result.data là enhancedStatus từ service
        setError(null);
        setLastUpdate(new Date());
        console.log('System status (DeviceStatusMonitor) updated successfully');
      } else {
        setError(result.error);
        if (result.cachedData) { // Use cached data if API fails but cache exists
          setSystemStatus(result.cachedData);
          console.log('Using cached system status (DeviceStatusMonitor) due to API error');
        } else if(!systemStatus) { // Clear systemStatus if no cache and it's currently null
            setSystemStatus(null);
        }
      }
    } catch (err) { // Should not happen if service handles errors, but good to have
      console.error('Failed to fetch system status (DeviceStatusMonitor):', err);
      setError(err.message || 'Failed to fetch system status');
      if(!systemStatus) setSystemStatus(null);
    } finally {
      setLoading(false);
    }
  }, [systemStatus]); // Added systemStatus to dependency to potentially avoid clearing if it already has data.

  useEffect(() => {
    fetchSystemStatus();
    let intervalId;
    if (autoRefresh) {
      intervalId = setInterval(fetchSystemStatus, refreshInterval);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [fetchSystemStatus, refreshInterval, autoRefresh]);

  const handlePumpControl = async (action, duration = null) => {
    try {
      console.log(`Attempting to ${action} pump (DeviceStatusMonitor)...`);
      setLoading(true); // Indicate loading for pump control action

      // deviceControlService.controlPump sẽ gọi API_ENDPOINTS.CORE_OPERATIONS.CONTROL.PUMP_ACTION(action)
      const result = await deviceControlService.controlPump(action, {
        duration,
        reason: 'manual_control_from_monitor_v2' // Updated reason
      });

      if (result.success) {
        alert(`Bơm đã ${action === 'on' ? 'BẬT' : 'TẮT'} thành công! ${result.data.message || result.data.operation?.predicted_outcome || ''}`);
        // Refresh status after a short delay to allow backend to update
        setTimeout(fetchSystemStatus, 1500); // Shorter delay
      } else {
        const errorMsg = result.error || 'Lỗi không xác định khi điều khiển bơm.';
        const suggestions = result.suggestions ? '\nGợi ý:\n' + result.suggestions.join('\n') : '';
        alert(`Điều khiển bơm thất bại: ${errorMsg}${suggestions}`);
      }
    } catch (err) { // Should not happen if service handles errors
      console.error(`Error controlling pump (${action}) (DeviceStatusMonitor):`, err);
      alert(`Lỗi điều khiển bơm: ${err.message}`);
    } finally {
        setLoading(false); // Stop loading for pump control action
    }
  };

  const getStatusStyling = (status, type = 'pump_status') => { // Renamed from 'pump' type for clarity
    if (type === 'pump_status') { // 'status' here is pump is_on (boolean)
      return status ? 
        { color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200' } :
        { color: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200' };
    }
    
    // For system health string 'healthy', 'warning', 'critical'
    if (type === 'system_health') {
        switch (status) {
            case 'healthy': return { color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200', icon: CheckCircle };
            case 'warning': return { color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200', icon: AlertTriangle };
            case 'critical': return { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', icon: AlertTriangle };
            default: return { color: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200', icon: Activity };
        }
    }
    return { color: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200' };
  };

  const formatTimeRemaining = (seconds) => {
    if (typeof seconds !== 'number' || seconds < 0) return 'N/A'; // Handles null/undefined better
    if (seconds === 0 && systemStatus?.pump?.is_on) return '0s'; // Show 0s if pump on but 0 remaining
    if (seconds === 0 && !systemStatus?.pump?.is_on) return 'N/A';

    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  // UI Logic based on new systemStatus structure
  // systemStatus.pump from GET /control/status contains:
  // { is_on, start_time, scheduled_stop_time, ..., total_runtime_seconds, total_water_used, 
  //   current_runtime_seconds, current_water_used, remaining_seconds, ..., efficiency, nextAllowedStart }

  const pumpIsOn = systemStatus?.pump?.is_on || false;
  const pumpStyling = getStatusStyling(pumpIsOn, 'pump_status');
  const systemHealthStatus = systemStatus?.systemHealth?.status || 'unknown';
  const healthStyling = getStatusStyling(systemHealthStatus, 'system_health');
  const HealthIcon = healthStyling.icon || Activity;

  if (loading && !systemStatus) { // Only show initial loading spinner if no data at all
    return (
      <div className="bg-white rounded-lg shadow-md p-6 animate-pulse">
        <div className="flex items-center justify-center">
          <Activity className="w-6 h-6 animate-spin text-blue-500 mr-2" />
          <span className="text-gray-600">Đang tải trạng thái hệ thống...</span>
        </div>
      </div>
    );
  }

  if (error && !systemStatus) { // Show error if no data could be fetched (even cached)
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center mb-4">
          <AlertTriangle className="w-6 h-6 text-red-500 mr-2" />
          <h3 className="text-lg font-semibold text-red-800">Lỗi Trạng Thái Hệ Thống</h3>
        </div>
        <p className="text-red-700 mb-4">{error}</p>
        <button 
          onClick={fetchSystemStatus}
          className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
        >
          Thử lại
        </button>
      </div>
    );
  }
  
  if (!systemStatus) { // If still no systemStatus after loading & error checks (e.g. API returns success:false with no cache)
     return (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
            <Info className="w-8 h-8 text-yellow-500 mx-auto mb-2"/>
            <p className="text-yellow-700">Không thể tải dữ liệu trạng thái hệ thống. Vui lòng thử lại.</p>
             <button 
                onClick={fetchSystemStatus}
                className="mt-3 px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600 transition-colors"
            > Thử lại </button>
        </div>
     )   
  }

  return (
    <div className="space-y-6">
      {/* System Status Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-800 flex items-center">
            <Activity className="w-6 h-6 mr-2 text-blue-500" />
            Trạng thái Hệ thống Tưới Thông minh
          </h2>
          <div className="flex items-center space-x-3">
            <button onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-1 rounded text-xs font-medium ${ autoRefresh ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
              Tự động làm mới: {autoRefresh ? 'BẬT' : 'TẮT'}
            </button>
            <button onClick={fetchSystemStatus} disabled={loading}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 transition-colors text-sm">
              {loading ? 'Đang cập nhật...' : 'Làm mới'}
            </button>
          </div>
        </div>

        {lastUpdate && (<p className="text-xs text-gray-500 mb-4">Cập nhật lần cuối: {lastUpdate.toLocaleString('vi-VN')}</p>)}

        {error && !loading && ( // Display non-critical error (e.g. using cached data)
             <div className="my-2 p-3 bg-yellow-50 border-l-4 border-yellow-400 text-yellow-700 text-sm rounded">
                <div className="flex items-center"><AlertTriangle size={16} className="mr-2"/> <p>{error}</p></div>
            </div>
        )}

        {systemStatus.systemHealth && (
          <div className={`p-4 rounded-lg border ${healthStyling.bg} ${healthStyling.border}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <HealthIcon className={`w-5 h-5 mr-2 ${healthStyling.color}`} />
                <span className={`font-medium ${healthStyling.color}`}>
                  Sức khỏe hệ thống: {systemStatus.systemHealth.status.toUpperCase()}
                </span>
              </div>
              <span className={`text-sm font-medium ${healthStyling.color}`}>
                Điểm: {systemStatus.systemHealth.score || "N/A"}/100
              </span>
            </div>
             {systemStatus.systemHealth.factors && systemStatus.systemHealth.factors.length > 0 && (
                <ul className="mt-2 text-xs space-y-0.5 pl-7">
                    {systemStatus.systemHealth.factors.map(f => (
                        <li key={f.component} className={f.status === 'healthy' ? 'text-green-700' : 'text-yellow-700'}>
                           <strong>{f.component}:</strong> {f.message}
                        </li>
                    ))}
                </ul>
            )}
          </div>
        )}
      </div>

      {/* Pump Status Panel */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <Droplets className="w-5 h-5 mr-2 text-blue-500" />
          Trạng thái Bơm Nước
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className={`p-4 rounded-lg border ${pumpStyling.bg} ${pumpStyling.border}`}>
            <div className="flex items-center justify-between mb-3">
              <span className="font-medium text-gray-700">Trạng thái hiện tại</span>
              <Power className={`w-5 h-5 ${pumpStyling.color} ${pumpIsOn && !loading ? 'animate-pulse text-green-500' : ''}`} />
            </div>
            <div className={`text-2xl font-bold ${pumpStyling.color} mb-2`}>
              {pumpIsOn ? 'ĐANG CHẠY' : 'ĐÃ DỪNG'}
            </div>
            {systemStatus.pump && ( // Ensure pump object exists
              <div className="space-y-1 text-sm text-gray-600">
                 {pumpIsOn && (
                    <>
                    <div className="flex justify-between"><span>Thời gian chạy:</span><span className="font-medium">{formatTimeRemaining(systemStatus.pump.current_runtime_seconds)}</span></div>
                    <div className="flex justify-between"><span>Còn lại:</span><span className="font-medium">{formatTimeRemaining(systemStatus.pump.remaining_seconds)}</span></div>
                    <div className="flex justify-between"><span>Nước đã dùng (lần này):</span><span className="font-medium">{(systemStatus.pump.current_water_used || 0).toFixed(2)} L</span></div>
                    </>
                 )}
                 {!pumpIsOn && systemStatus.pump.last_off_time && (
                     <div className="flex justify-between"><span>Lần tắt cuối:</span><span className="font-medium">{new Date(systemStatus.pump.last_off_time).toLocaleTimeString('vi-VN')}</span></div>
                 )}
                 {systemStatus.pump.nextAllowedStart?.minutesRemaining > 0 && !pumpIsOn &&(
                    <div className="mt-2 text-xs text-orange-600">Cần đợi {systemStatus.pump.nextAllowedStart.minutesRemaining} phút trước khi chạy lại.</div>
                 )}
              </div>
            )}
          </div>

          <div className="space-y-3">
            <h4 className="font-medium text-gray-700">Điều khiển thủ công</h4>
            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => handlePumpControl('on', 300)} disabled={pumpIsOn || loading}
                className="px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm">
                Bật (5 phút)
              </button>
              <button onClick={() => handlePumpControl('on', 600)} disabled={pumpIsOn || loading}
                className="px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm">
                Bật (10 phút)
              </button>
              <button onClick={() => handlePumpControl('off')} disabled={!pumpIsOn || loading}
                className="px-3 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm col-span-2">
                Tắt Bơm
              </button>
            </div>
             {systemStatus.pump?.recommendedAction && systemStatus.pump.recommendedAction.action !== 'ready' && (
                <div className={`mt-3 text-xs p-2 rounded border-l-2
                    ${systemStatus.pump.recommendedAction.priority === 'high' ? 'bg-red-50 border-red-300 text-red-700' :
                     systemStatus.pump.recommendedAction.priority === 'medium' ? 'bg-yellow-50 border-yellow-300 text-yellow-700' :
                     'bg-blue-50 border-blue-300 text-blue-700'}`}>
                    💡 {systemStatus.pump.recommendedAction.message}
                </div>
            )}
          </div>
        </div>

        {systemStatus.pump?.efficiency && ( // From enhancedStatus in deviceControlService
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="font-medium text-gray-700 mb-3 flex items-center">
              <TrendingUp className="w-4 h-4 mr-2 text-indigo-500" />
              Thống kê Hiệu suất Bơm
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              <div className="text-center p-2 bg-white rounded shadow-sm">
                <div className="font-semibold text-gray-800">{systemStatus.pump.efficiency.efficiency || 0} {systemStatus.pump.efficiency.unit}</div>
                <div className="text-gray-500">Hiệu suất</div>
              </div>
              <div className="text-center p-2 bg-white rounded shadow-sm">
                <div className="font-semibold text-gray-800">{(systemStatus.pump.total_water_used || 0).toFixed(1)} L</div>
                <div className="text-gray-500">Tổng nước (hôm nay)</div>
              </div>
              <div className="text-center p-2 bg-white rounded shadow-sm">
                <div className="font-semibold text-gray-800">{Math.round((systemStatus.pump.total_runtime_seconds || 0) / 60)} phút</div>
                <div className="text-gray-500">Tổng chạy (hôm nay)</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Schedule Status */}
      {systemStatus.scheduler && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <Clock className="w-5 h-5 mr-2 text-purple-500" />
            Trạng thái Lịch Trình
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Bộ lập lịch:</span>
                <span className={`font-medium px-2 py-0.5 rounded text-xs ${ systemStatus.scheduler.active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'}`}>
                  {systemStatus.scheduler.active ? 'ĐANG HOẠT ĐỘNG' : 'KHÔNG HOẠT ĐỘNG'}
                </span>
              </div>
              <div className="flex justify-between items-center mt-2">
                <span className="text-gray-600">Số lịch đang hoạt động:</span>
                <span className="font-medium text-purple-700">{systemStatus.scheduler.schedules_count || 0}</span>
              </div>
               {systemStatus.scheduler.conflictingSchedules && systemStatus.scheduler.conflictingSchedules.length > 0 && (
                    <div className="mt-2 text-xs text-red-600 p-2 bg-red-50 rounded border-l-2 border-red-300">
                       Có {systemStatus.scheduler.conflictingSchedules.length} lịch trình xung đột cần xem xét!
                    </div>
                )}
            </div>
            {systemStatus.scheduler.nextScheduledEvent ? (
              <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
                <h4 className="font-medium text-gray-700 mb-1.5">Lịch tưới tiếp theo:</h4>
                <div className="space-y-1">
                  <div className="flex justify-between"><span className="text-gray-600">Tên:</span><span className="font-medium">{systemStatus.scheduler.nextScheduledEvent.schedule?.name || 'N/A'}</span></div>
                  <div className="flex justify-between"><span className="text-gray-600">Thời gian:</span><span className="font-medium">{new Date(systemStatus.scheduler.nextScheduledEvent.execution?.timestamp).toLocaleTimeString('vi-VN')}</span></div>
                   <div className="flex justify-between"><span className="text-gray-600">Còn:</span><span className="font-medium">{systemStatus.scheduler.nextScheduledEvent.execution?.hoursUntil} giờ</span></div>
                </div>
              </div>
            ) : (
                <div className="p-3 bg-gray-50 rounded-lg text-center text-gray-500">Không có lịch tưới nào sắp tới.</div>
            )}
          </div>
        </div>
      )}

      {/* System Alerts */}
      {systemStatus.alerts && systemStatus.alerts.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <AlertTriangle className="w-5 h-5 mr-2 text-orange-500" />
            Cảnh báo Hệ thống
          </h3>
          <div className="space-y-3">
            {systemStatus.alerts.map((alert, index) => (
              <div key={index}
                className={`p-3 rounded-lg border-l-4 ${ alert.type === 'warning' ? 'bg-yellow-50 border-yellow-400' : (alert.type === 'critical' ? 'bg-red-50 border-red-400' : 'bg-blue-50 border-blue-400')}`}>
                <div className="flex items-start">
                  <AlertTriangle className={`w-4 h-4 mr-2 mt-0.5 flex-shrink-0 ${ alert.type === 'warning' ? 'text-yellow-500' : (alert.type === 'critical' ? 'text-red-500' : 'text-blue-500')}`} />
                  <div className="flex-1 text-sm">
                    <p className="font-medium text-gray-800">[{alert.component?.toUpperCase() || 'SYSTEM'}] {alert.message}</p>
                    {alert.action && <p className="text-gray-600 mt-1">➡️ {alert.action}</p>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DeviceStatusMonitor;