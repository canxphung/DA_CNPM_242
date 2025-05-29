// // hooks/useSensorData.js
// import { useState, useEffect, useCallback, useRef } from "react";
// import sensorService from "../utils/sensorService"; // Đã được cập nhật

// // createDefaultSensorData and createDefaultChartData can be simplified
// // as sensorService will now return a more structured error object if fetch fails.
// const createInitialSensorData = () => ({
//   temperature: { value: 0, unit: "°C", status: "unknown", timestamp: new Date().toISOString(), feedId: "N/A", analysis: null },
//   moisture: { value: 0, unit: "%", status: "unknown", timestamp: new Date().toISOString(), feedId: "N/A", analysis: null }, // For air humidity
//   light: { value: 0, unit: "Lux", status: "unknown", timestamp: new Date().toISOString(), feedId: "N/A", analysis: null },
//   soil: { value: 0, unit: "%", status: "unknown", timestamp: new Date().toISOString(), feedId: "N/A", analysis: null } // For soil moisture
// });

// const createInitialChartData = () => ({
//   temperature: { labels: [], values: [] },
//   moisture: { labels: [], values: [] },
//   light: { labels: [], values: [] },
//   soil: { labels: [], values: [] }
// });

// export const useSensorData = (options = {}) => {
//   const {
//     refreshInterval = 60000, 
//     enableAutoRefresh = true,
//     // enableAnalysis option might be less relevant if sensorService always fetches analysis
//     historyHours = 24,
//     // sensorTypes to monitor is still relevant for chart data fetching if using specific types
//     sensorTypes = ['temperature', 'moisture', 'light', 'soil'] 
//   } = options;

//   const [data, setData] = useState(createInitialSensorData());
//   const [chartData, setChartData] = useState(createInitialChartData());
  
//   const [analysis, setAnalysis] = useState(null); // This might be overall analysis from snapshot
//   const [recommendations, setRecommendations] = useState([]); // From snapshot or combined sensor analyses
//   const [overallStatus, setOverallStatus] = useState('unknown'); // From snapshot
  
//   const [loading, setLoading] = useState(true);
//   const [error, setError] = useState(null);
//   const [lastUpdate, setLastUpdate] = useState(null);
//   const [connectionStatus, setConnectionStatus] = useState('connecting'); // 'connecting', 'connected', 'error'
  
//   const [fetchStats, setFetchStats] = useState({ /* ... (keep existing) ... */ });
//   const mountedRef = useRef(true);
//   const retryCountRef = useRef(0);
//   const lastSuccessfulFetchRef = useRef(null);
//   const refreshTimeoutRef = useRef(null);
//   const MAX_RETRY_ATTEMPTS = 3;


//   const getDynamicRefreshInterval = useCallback(() => {
//     if (connectionStatus === 'error' && retryCountRef.current > 0) {
//       return Math.min(refreshInterval * Math.pow(2, retryCountRef.current), 300000);
//     }
//     if (connectionStatus === 'connected') return refreshInterval;
//     return refreshInterval;
//   }, [connectionStatus, refreshInterval]);

//   // No longer need transformSensorData and transformChartData here if sensorService.js provides them correctly
//   // These transformation should happen inside sensorService.js methods
//   // based on the API response structures.

//   const refreshData = useCallback(async (forceRefresh = false) => {
//     if (loading && !forceRefresh) return false;
//     if (!mountedRef.current) return false;

//     setLoading(true);
//     setError(null); // Clear previous error
//     const fetchStartTime = Date.now();

//     try {
//       // sensorService.fetchCurrentSensorData() now returns a structured object:
//       // { sensors: {temp, moisture, light, soil}, overall_status, analysis_summary, irrigation_recommendation, timestamp, source, error? }
//       const currentDataResult = await sensorService.fetchCurrentSensorData(forceRefresh);
      
//       // sensorService.fetchHistoricalData() returns:
//       // { chartData: {temp, moisture, light, soil}, timestamp, source, error? }
//       const historicalDataResult = await sensorService.fetchHistoricalData({
//         hours: historyHours,
//         sensorTypes, // Ensure these types match keys in chartData (temp, moisture, light, soil)
//         forceRefresh
//       });

//       if (!mountedRef.current) return false;

//       // Handle Current Data
//       if (currentDataResult.sensors) {
//         setData(prevData => ({ ...prevData, ...currentDataResult.sensors })); // Merge new sensor values
//       }
//       if (currentDataResult.overall_status) {
//         setOverallStatus(currentDataResult.overall_status);
//       }
//       if (currentDataResult.analysis_summary) { // This is an object keyed by sensor type
//         setAnalysis(currentDataResult.analysis_summary); 
//       }
//       if (currentDataResult.irrigation_recommendation) {
//         setRecommendations(currentDataResult.irrigation_recommendation.action_items || [currentDataResult.irrigation_recommendation]); // Snapshot might return a single object or array
//       }
//       if (currentDataResult.error) {
//          // Partial success or fallback data, may set error specific to current data
//          setError(prevError => prevError ? `${prevError}; Lỗi dữ liệu hiện tại: ${currentDataResult.error}` : `Lỗi dữ liệu hiện tại: ${currentDataResult.error}`);
//          setConnectionStatus('error'); // If error exists, mark connection as error
//       } else {
//           setConnectionStatus('connected'); // If no error explicitly, assume connected
//       }

//       // Handle Historical Data
//       if (historicalDataResult.chartData) {
//         setChartData(prevChartData => ({ ...prevChartData, ...historicalDataResult.chartData }));
//       }
//       if (historicalDataResult.error) {
//         setError(prevError => prevError ? `${prevError}; Lỗi dữ liệu lịch sử: ${historicalDataResult.error}` : `Lỗi dữ liệu lịch sử: ${historicalDataResult.error}`);
//          // No specific connection status change here, error is per-data-type
//       }
      
//       // Overall status check
//       if(!currentDataResult.error && !historicalDataResult.error) {
//         setError(null); // Clear error if both fetches were successful (or returned no explicit error)
//         setConnectionStatus('connected');
//         lastSuccessfulFetchRef.current = Date.now();
//         retryCountRef.current = 0;
//       } else {
//         retryCountRef.current += 1;
//       }
//       setLastUpdate(new Date(currentDataResult.timestamp || Date.now()));


//       setFetchStats(prev => ({
//         totalFetches: prev.totalFetches + 1,
//         successfulFetches: prev.successfulFetches + (!currentDataResult.error && !historicalDataResult.error ? 1 : 0),
//         failedFetches: prev.failedFetches + ((currentDataResult.error || historicalDataResult.error) ? 1 : 0),
//         averageResponseTime: (prev.averageResponseTime * (prev.successfulFetches) + (Date.now() - fetchStartTime)) / (prev.successfulFetches + (!currentDataResult.error && !historicalDataResult.error ? 1 : 0) || 1),
//       }));
      
//       // Schedule next if any part had an error and retries are allowed
//       if ((currentDataResult.error || historicalDataResult.error) && retryCountRef.current <= MAX_RETRY_ATTEMPTS) {
//         // Retry logic will be handled by scheduleNextRefresh if enableAutoRefresh is on
//       }

//       return true;

//     } catch (err) { // Catch unexpected errors during the hook's execution
//       if (!mountedRef.current) return false;
//       console.error("Unexpected error in refreshData (useSensorData):", err);
//       setError(err.message || "Lỗi không xác định khi làm mới dữ liệu.");
//       setConnectionStatus('error');
//       retryCountRef.current += 1;
//       setFetchStats(prev => ({ ...prev, totalFetches: prev.totalFetches + 1, failedFetches: prev.failedFetches + 1 }));
//       return false;
//     } finally {
//       if (mountedRef.current) {
//         setLoading(false);
//         // IMPORTANT: Schedule next refresh AFTER loading is set to false
//         // And AFTER all state updates from this refresh have likely settled
//         if(enableAutoRefresh) scheduleNextRefresh(); 
//       }
//     }
//   }, [historyHours, sensorTypes, loading, enableAutoRefresh]); // Removed transform functions from deps, Added enableAutoRefresh

//   // Analyze specific sensor
//   const analyzeSensor = useCallback(async (sensorType) => {
//     try {
//       // sensorService.analyzeSensor returns { sensor_type, reading, analysis, timestamp, recommendations (if any generated by service), error? }
//       const result = await sensorService.analyzeSensor(sensorType, true); // Force collect fresh for specific analysis
//       if (result.error) {
//         console.error(`Analysis failed for ${sensorType}:`, result.error);
//         // You might want to update a specific error state for this sensor's analysis
//         return { success: false, error: result.error, analysis: null };
//       }
//       // Update parts of the UI, e.g., a modal showing detailed analysis for 'sensorType'
//       // This hook might not be the place to store individual sensor analysis details,
//       // but it could trigger an update or return data for the component to handle.
//       console.log(`Analysis for ${sensorType}:`, result);
//       return { success: true, analysis: result.analysis, reading: result.reading, recommendations: result.recommendations };
//     } catch (error) {
//       console.error(`Error analyzing ${sensorType} via hook:`, error);
//       return { success: false, error: error.message, analysis: null };
//     }
//   }, []);


//   const scheduleNextRefresh = useCallback(() => {
//     if (!enableAutoRefresh || !mountedRef.current) return;
//     if (refreshTimeoutRef.current) clearTimeout(refreshTimeoutRef.current);

//     const nextInterval = getDynamicRefreshInterval();
    
//     console.log(`Next sensor data refresh scheduled in ${nextInterval / 1000}s`);
//     refreshTimeoutRef.current = setTimeout(() => {
//       if (mountedRef.current && enableAutoRefresh) {
//         console.log("Auto-refreshing sensor data...");
//         refreshData(); // This will then call scheduleNextRefresh again in its finally block
//       }
//     }, nextInterval);
//   }, [enableAutoRefresh, getDynamicRefreshInterval, refreshData]);

//   useEffect(() => {
//     mountedRef.current = true;
//     console.log("useSensorData mounted. Initial fetch starting...");
//     refreshData(true); // Initial fetch, force to bypass cache

//     return () => {
//       mountedRef.current = false;
//       if (refreshTimeoutRef.current) {
//         clearTimeout(refreshTimeoutRef.current);
//         console.log("useSensorData unmounted, refresh timer cleared.");
//       }
//     };
//   // eslint-disable-next-line react-hooks/exhaustive-deps
//   }, []); // Run only on mount and unmount. refreshData dependency removed to prevent re-triggering initial fetch by itself. Auto-refresh loop is now self-contained.

//   // useEffect for refreshInterval changes - was causing issues by being in main useEffect.
//   // The scheduleNextRefresh in refreshData's finally block will pick up new interval.

//   const getPerformanceMetrics = useCallback(() => { /* ... (keep existing, but use sensorService.getCacheStats() if that's desired) ... */ 
//       const timeSinceLastSuccess = lastSuccessfulFetchRef.current 
//       ? Date.now() - lastSuccessfulFetchRef.current 
//       : null;

//     return {
//       ...fetchStats,
//       connectionStatus,
//       timeSinceLastSuccessMs: timeSinceLastSuccess,
//       retryCount: retryCountRef.current,
//       cacheStats: sensorService.getCacheStats() // Assuming this function exists
//     };
//   }, [fetchStats, connectionStatus]);

//   const clearCacheAndRefresh = useCallback(() => {
//     sensorService.clearCache();
//     console.log('Sensor data cache cleared, forcing refresh...');
//     refreshData(true);
//   }, [refreshData]);


//   return {
//     data,
//     chartData,
//     loading,
//     error,
//     analysis, // Overall analysis_summary from snapshot
//     recommendations, // Irrigation recommendations from snapshot
//     overallStatus, // Overall status from snapshot
//     refreshData: clearCacheAndRefresh, // Expose clearCacheAndRefresh as primary refresh
//     analyzeSensor, // Function to get detailed analysis for one sensor
//     lastUpdate,
//     connectionStatus,
//     getPerformanceMetrics,
//     clearCache: sensorService.clearCache, // Direct expose
//     isAutoRefreshEnabled: enableAutoRefresh,
//     currentRefreshInterval: getDynamicRefreshInterval()
//   };
// };
// src/hooks/useSensorData.js
import { useState, useEffect, useCallback, useRef } from 'react';
import sensorService from '../utils/sensorService';
// import { SensorStatus } from '../utils/sensorCollectors';
import { SensorStatus } from '../utils/sensorTypes';

/**
 * Hook để quản lý dữ liệu sensor
 */
export const useSensorData = (options = {}) => {
  const {
    autoRefresh = true,
    refreshInterval = 30000, // 30 giây
    sensorTypes = ['temperature', 'moisture', 'light', 'soil']
  } = options;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  
  const refreshIntervalRef = useRef(null);
  const unsubscribeRef = useRef(null);

  /**
   * Fetch dữ liệu sensor
   */
  const fetchData = useCallback(async (forceRefresh = false) => {
    try {
      setLoading(true);
      setError(null);
      
      const sensorData = await sensorService.fetchCurrentSensorData(forceRefresh);
      
      setData(sensorData);
      setLastUpdated(new Date());
      
      return sensorData;
    } catch (err) {
      const errorMessage = err.message || 'Lỗi không xác định khi tải dữ liệu sensor';
      setError(errorMessage);
      console.error('Error fetching sensor data:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Refresh dữ liệu
   */
  const refresh = useCallback(() => {
    return fetchData(true);
  }, [fetchData]);

  /**
   * Lấy thông tin của một sensor cụ thể
   */
  const getSensorInfo = useCallback((sensorType) => {
    if (!data?.sensors?.[sensorType]) {
      return {
        value: null,
        unit: '',
        status: SensorStatus.UNKNOWN,
        timestamp: null,
        analysis: null
      };
    }

    const sensor = data.sensors[sensorType];
    return {
      value: sensor.value,
      unit: sensor.unit,
      status: sensor.status,
      timestamp: sensor.timestamp,
      analysis: sensor.analysis,
      isOnline: sensor.status !== SensorStatus.ERROR,
      isNormal: sensor.status === SensorStatus.NORMAL,
      isWarning: sensor.status === SensorStatus.WARNING,
      isCritical: sensor.status === SensorStatus.CRITICAL
    };
  }, [data]);

  /**
   * Lấy recommendation cho sensor
   */
  const getRecommendation = useCallback((sensorType) => {
    return sensorService.getRecommendation(sensorType);
  }, []);

  /**
   * Kiểm tra xem có sensor nào đang trong trạng thái cảnh báo không
   */
  const hasWarnings = useCallback(() => {
    if (!data?.sensors) return false;
    
    return Object.values(data.sensors).some(sensor => 
      sensor.status === SensorStatus.WARNING || sensor.status === SensorStatus.CRITICAL
    );
  }, [data]);

  /**
   * Lấy danh sách các sensor có vấn đề
   */
  const getProblematicSensors = useCallback(() => {
    if (!data?.sensors) return [];
    
    return Object.entries(data.sensors)
      .filter(([_, sensor]) => 
        sensor.status === SensorStatus.WARNING || 
        sensor.status === SensorStatus.CRITICAL ||
        sensor.status === SensorStatus.ERROR
      )
      .map(([type, sensor]) => ({
        type,
        ...sensor,
        recommendation: getRecommendation(type)
      }));
  }, [data, getRecommendation]);

  /**
   * Get overall system status
   */
  const getOverallStatus = useCallback(() => {
    if (!data) return SensorStatus.UNKNOWN;
    
    if (data.overall_status) {
      return data.overall_status;
    }
    
    // Fallback: determine from individual sensors
    if (!data.sensors) return SensorStatus.UNKNOWN;
    
    const sensors = Object.values(data.sensors);
    
    if (sensors.some(s => s.status === SensorStatus.CRITICAL)) {
      return SensorStatus.CRITICAL;
    }
    
    if (sensors.some(s => s.status === SensorStatus.WARNING)) {
      return SensorStatus.WARNING;
    }
    
    if (sensors.some(s => s.status === SensorStatus.ERROR)) {
      return SensorStatus.ERROR;
    }
    
    if (sensors.every(s => s.status === SensorStatus.NORMAL)) {
      return SensorStatus.NORMAL;
    }
    
    return SensorStatus.UNKNOWN;
  }, [data]);

  // Setup auto refresh
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      refreshIntervalRef.current = setInterval(() => {
        fetchData(false); // Không force refresh trong auto refresh
      }, refreshInterval);
    }

    // Cleanup
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [autoRefresh, refreshInterval, fetchData]);

  // Subscribe to sensor service updates
  useEffect(() => {
    unsubscribeRef.current = sensorService.subscribe((newData) => {
      setData(newData);
      setLastUpdated(new Date());
      setError(null);
    });

    // Cleanup
    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
      }
    };
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchData(false);
  }, [fetchData]);

  return {
    // Data
    data,
    sensors: data?.sensors || {},
    loading,
    error,
    lastUpdated,
    
    // Actions
    refresh,
    fetchData,
    
    // Utilities
    getSensorInfo,
    getRecommendation,
    hasWarnings,
    getProblematicSensors,
    getOverallStatus,
    
    // Status checks
    isLoading: loading,
    hasError: !!error,
    isOnline: !error && data && data.source !== 'default_fallback_error'
  };
};

/**
 * Hook để lấy dữ liệu lịch sử
 */
export const useSensorHistory = (options = {}) => {
  const {
    hours = 24,
    sensorTypes = ['temperature', 'moisture', 'light', 'soil'],
    autoRefresh = false,
    refreshInterval = 300000 // 5 phút
  } = options;

  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  
  const refreshIntervalRef = useRef(null);

  const fetchHistoryData = useCallback(async (forceRefresh = false) => {
    try {
      setLoading(true);
      setError(null);
      
      const historyData = await sensorService.fetchHistoricalData({
        hours,
        sensorTypes,
        forceRefresh
      });
      
      setChartData(historyData);
      setLastUpdated(new Date());
      
      return historyData;
    } catch (err) {
      const errorMessage = err.message || 'Lỗi không xác định khi tải dữ liệu lịch sử';
      setError(errorMessage);
      console.error('Error fetching sensor history:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [hours, sensorTypes]);

  const refresh = useCallback(() => {
    return fetchHistoryData(true);
  }, [fetchHistoryData]);

  // Setup auto refresh
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      refreshIntervalRef.current = setInterval(() => {
        fetchHistoryData(false);
      }, refreshInterval);
    }

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [autoRefresh, refreshInterval, fetchHistoryData]);

  // Initial fetch
  useEffect(() => {
    fetchHistoryData(false);
  }, [fetchHistoryData]);

  return {
    chartData: chartData?.chartData || {},
    metadata: {
      timestamp: chartData?.timestamp,
      source: chartData?.source,
      period_hours: chartData?.period_hours
    },
    loading,
    error,
    lastUpdated,
    refresh,
    fetchData: fetchHistoryData,
    isLoading: loading,
    hasError: !!error
  };
};

/**
 * Hook để phân tích sensor
 */
export const useSensorAnalysis = (sensorType) => {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyzeData = useCallback(async (collectFresh = false) => {
    if (!sensorType) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const analysisData = await sensorService.analyzeSensor(sensorType, collectFresh);
      setAnalysis(analysisData);
      
      return analysisData;
    } catch (err) {
      const errorMessage = err.message || `Lỗi phân tích dữ liệu ${sensorType}`;
      setError(errorMessage);
      console.error(`Error analyzing ${sensorType}:`, err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [sensorType]);

  useEffect(() => {
    if (sensorType) {
      analyzeData(false);
    }
  }, [sensorType, analyzeData]);

  return {
    analysis,
    loading,
    error,
    analyzeData,
    refresh: () => analyzeData(true),
    isLoading: loading,
    hasError: !!error
  };
};