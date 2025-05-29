// src/components/SensorDashboard.jsx
import React from 'react';
import { useSensorData, useSensorHistory } from '../hooks/useSensorData';
import { getSensorConfig } from '../utils/sensorTypes';
import { SensorStatus } from '../utils/sensorCollectors';

const SensorCard = ({ sensorType, sensorInfo, recommendation }) => {
  const config = getSensorConfig(sensorType);
  
  const getStatusColor = (status) => {
    switch (status) {
      case SensorStatus.NORMAL: return 'text-green-600 bg-green-50';
      case SensorStatus.WARNING: return 'text-yellow-600 bg-yellow-50';
      case SensorStatus.CRITICAL: return 'text-red-600 bg-red-50';
      case SensorStatus.ERROR: return 'text-gray-600 bg-gray-50';
      default: return 'text-gray-400 bg-gray-50';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case SensorStatus.NORMAL: return 'Bình thường';
      case SensorStatus.WARNING: return 'Cảnh báo';
      case SensorStatus.CRITICAL: return 'Nghiêm trọng';
      case SensorStatus.ERROR: return 'Lỗi';
      default: return 'Không xác định';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <span className="text-2xl">{config?.icon}</span>
          <h3 className="text-lg font-semibold text-gray-800">
            {config?.name}
          </h3>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(sensorInfo.status)}`}>
          {getStatusText(sensorInfo.status)}
        </span>
      </div>
      
      <div className="mb-4">
        <div className="flex items-baseline space-x-2">
          <span className="text-3xl font-bold text-gray-900">
            {sensorInfo.value !== null ? sensorInfo.value.toFixed(1) : '--'}
          </span>
          <span className="text-lg text-gray-500">{sensorInfo.unit}</span>
        </div>
        
        {sensorInfo.timestamp && (
          <p className="text-sm text-gray-500 mt-1">
            Cập nhật: {new Date(sensorInfo.timestamp).toLocaleString('vi-VN')}
          </p>
        )}
      </div>

      {recommendation && (
        <div className={`mt-4 p-3 rounded-lg ${
          recommendation.type === 'critical' ? 'bg-red-50 border border-red-200' :
          recommendation.type === 'warning' ? 'bg-yellow-50 border border-yellow-200' :
          'bg-green-50 border border-green-200'
        }`}>
          <p className={`text-sm font-medium ${
            recommendation.type === 'critical' ? 'text-red-800' :
            recommendation.type === 'warning' ? 'text-yellow-800' :
            'text-green-800'
          }`}>
            {recommendation.message}
          </p>
        </div>
      )}
    </div>
  );
};

const getStatusText = (status) => {
  switch (status) {
    case SensorStatus.NORMAL: return 'Bình thường';
    case SensorStatus.WARNING: return 'Cảnh báo';
    case SensorStatus.CRITICAL: return 'Nghiêm trọng';
    case SensorStatus.ERROR: return 'Lỗi';
    default: return 'Không xác định';
  }
};

const OverallStatusCard = ({ status, hasWarnings, problematicSensors }) => {
  const getStatusInfo = (status) => {
    switch (status) {
      case SensorStatus.NORMAL:
        return {
          text: 'Hệ thống hoạt động bình thường',
          color: 'text-green-600 bg-green-50 border-green-200',
          icon: '✅'
        };
      case SensorStatus.WARNING:
        return {
          text: 'Hệ thống có cảnh báo',
          color: 'text-yellow-600 bg-yellow-50 border-yellow-200',
          icon: '⚠️'
        };
      case SensorStatus.CRITICAL:
        return {
          text: 'Hệ thống cần chú ý ngay',
          color: 'text-red-600 bg-red-50 border-red-200',
          icon: '🚨'
        };
      case SensorStatus.ERROR:
        return {
          text: 'Hệ thống gặp lỗi',
          color: 'text-gray-600 bg-gray-50 border-gray-200',
          icon: '❌'
        };
      default:
        return {
          text: 'Trạng thái không xác định',
          color: 'text-gray-400 bg-gray-50 border-gray-200',
          icon: '❓'
        };
    }
  };

  const statusInfo = getStatusInfo(status);

  return (
    <div className={`rounded-lg border p-6 ${statusInfo.color}`}>
      <div className="flex items-center space-x-3 mb-4">
        <span className="text-2xl">{statusInfo.icon}</span>
        <h2 className="text-xl font-semibold">Trạng thái tổng quan</h2>
      </div>
      
      <p className="text-lg font-medium mb-2">{statusInfo.text}</p>
      
      {hasWarnings && problematicSensors.length > 0 && (
        <div className="mt-4">
          <p className="font-medium mb-2">Cảm biến cần chú ý:</p>
          <ul className="space-y-1">
            {problematicSensors.map((sensor) => (
              <li key={sensor.type} className="text-sm">
                • {getSensorConfig(sensor.type)?.name}: {getStatusText(sensor.status)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

const SensorDashboard = () => {
  const {
    sensors,
    loading,
    error,
    lastUpdated,
    refresh,
    getSensorInfo,
    getRecommendation,
    hasWarnings,
    getProblematicSensors,
    getOverallStatus,
    isOnline
  } = useSensorData({
    autoRefresh: true,
    refreshInterval: 30000 // 30 giây
  });

  const {
    chartData,
    loading: historyLoading,
    error: historyError,
    refresh: refreshHistory
  } = useSensorHistory({
    hours: 24,
    autoRefresh: true,
    refreshInterval: 300000 // 5 phút
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Đang tải dữ liệu sensor...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-red-500 text-xl mb-4">❌</div>
          <p className="text-red-600 mb-4">Lỗi tải dữ liệu: {error}</p>
          <button
            onClick={() => refresh()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Thử lại
          </button>
        </div>
      </div>
    );
  }

  const sensorTypes = ['temperature', 'moisture', 'light', 'soil'];
  const overallStatus = getOverallStatus();
  const problematicSensors = getProblematicSensors();

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard Cảm Biến</h1>
          <p className="text-gray-600 mt-2">
            Giám sát hệ thống greenhouse của bạn
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="text-right">
            <p className="text-sm text-gray-500">Cập nhật lần cuối</p>
            <p className="text-sm font-medium">
              {lastUpdated ? lastUpdated.toLocaleString('vi-VN') : 'Chưa có'}
            </p>
          </div>
          
          <div className="flex items-center space-x-2">
            <div className={`h-3 w-3 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm font-medium">
              {isOnline ? 'Trực tuyến' : 'Ngoại tuyến'}
            </span>
          </div>
          
          <button
            onClick={() => refresh()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            🔄 Làm mới
          </button>
        </div>
      </div>

      {/* Overall Status */}
      <OverallStatusCard
        status={overallStatus}
        hasWarnings={hasWarnings()}
        problematicSensors={problematicSensors}
      />

      {/* Sensor Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {sensorTypes.map((sensorType) => {
          const sensorInfo = getSensorInfo(sensorType);
          const recommendation = getRecommendation(sensorType);
          
          return (
            <SensorCard
              key={sensorType}
              sensorType={sensorType}
              sensorInfo={sensorInfo}
              recommendation={recommendation}
            />
          );
        })}
      </div>

      {/* Chart Section (Basic) */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-800">Dữ liệu 24h qua</h2>
          <button
            onClick={() => refreshHistory()}
            className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
            disabled={historyLoading}
          >
            {historyLoading ? 'Đang tải...' : '🔄 Làm mới'}
          </button>
        </div>
        
        {historyError ? (
          <p className="text-red-600">Lỗi tải dữ liệu lịch sử: {historyError}</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sensorTypes.map((sensorType) => (
              <div key={sensorType} className="border rounded p-4">
                <h3 className="font-medium mb-2">
                  {getSensorConfig(sensorType)?.name}
                </h3>
                <p className="text-sm text-gray-600">
                  Điểm dữ liệu: {chartData[sensorType]?.values?.length || 0}
                </p>
                {chartData[sensorType]?.values?.length > 0 && (
                  <p className="text-sm text-gray-600">
                    Giá trị mới nhất: {chartData[sensorType].values[chartData[sensorType].values.length - 1]}
                    {getSensorConfig(sensorType)?.unit}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Debug Info (có thể ẩn trong production) */}
      {process.env.NODE_ENV === 'development' && (
        <details className="bg-gray-100 p-4 rounded">
          <summary className="cursor-pointer font-medium">Debug Info</summary>
          <pre className="mt-2 text-xs overflow-auto">
            {JSON.stringify({ sensors, chartData }, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
};

export default SensorDashboard;