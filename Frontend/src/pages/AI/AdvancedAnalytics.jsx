// src/pages/AI/AdvancedAnalytics.jsx
import React, { useState, useEffect } from 'react';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import Sidebar from '../../components/Sidebar';
import aiAnalyticsService from '../../utils/aiAnalyticsService'; // Import updated service
import NotificationToast from '../../components/NotificationToast';
import { TrendingUp, BarChart3, Filter, AlertCircle, Info } from 'lucide-react'; // Changed BarChart to BarChart3 for variety
import SensorChart from '../../components/SensorChart'; // This is your Chart.js based chart
import Loading from '../../components/Loading'; // Import Loading component

const AdvancedAnalytics = () => {
  const [selectedAnalysisType, setSelectedAnalysisType] = useState('prediction'); // 'prediction', 'correlation'
  const [chartDisplayData, setChartDisplayData] = useState({ labels: [], values: [] }); // For SensorChart
  const [analysisTextResult, setAnalysisTextResult] = useState('');
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(true);
  const [filterStartDate, setFilterStartDate] = useState(''); // YYYY-MM-DD
  const [filterEndDate, setFilterEndDate] = useState('');   // YYYY-MM-DD
  const [currentErrorMessage, setCurrentErrorMessage] = useState('');
  const [notification, setNotification] = useState({ show: false, message: "", type: "success" });

  const showToast = (message, type = "success") => {
    setNotification({ show: true, message, type, onClose: () => setNotification(p=>({...p, show: false})) });
  };

  // Main data fetching function for selected analysis type
  const fetchTypedAnalyticsData = async (type, start, end) => {
    setIsLoadingAnalytics(true);
    setCurrentErrorMessage(''); // Clear previous error
    setChartDisplayData({ labels: [], values: [] }); // Clear chart before new fetch
    setAnalysisTextResult('');

    try {
      // This will call the (currently placeholder) getAnalyticsChartData in the service
      // It expects response: { success, data: { chart: {labels, values}, text }, error? }
      const result = await aiAnalyticsService.getAnalyticsChartData(type, { startDate: start, endDate: end });
      
      if (result.success && result.data) {
        setChartDisplayData(result.data.chart || { labels: [], values: [] });
        setAnalysisTextResult(result.data.text || `Không có phân tích văn bản cho loại ${type}.`);
        showToast(`Tải phân tích "${type}" thành công!`, "success");
      } else {
        setCurrentErrorMessage(result.error || `Không thể tải dữ liệu phân tích cho "${type}".`);
        showToast(result.error || `Lỗi tải phân tích "${type}".`, "error");
      }
    } catch (error) { // Catch unexpected errors
      console.error(`Error fetching typed analytics data (${type}):`, error);
      const msg = `Lỗi hệ thống khi tải phân tích "${type}".`;
      setCurrentErrorMessage(msg);
      showToast(msg, "error");
    } finally {
      setIsLoadingAnalytics(false);
    }
  };

  useEffect(() => {
    // Fetch initial data for the default 'prediction' type
    fetchTypedAnalyticsData(selectedAnalysisType, filterStartDate, filterEndDate);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAnalysisType]); // Re-fetch when selectedAnalysisType changes. Filters are applied via button.

  const handleApplyFilters = () => {
    fetchTypedAnalyticsData(selectedAnalysisType, filterStartDate, filterEndDate);
  };
  
  const getChartTitle = () => {
      if(selectedAnalysisType === 'prediction') return "Biểu đồ Dự đoán Xu hướng";
      if(selectedAnalysisType === 'correlation') return "Biểu đồ Phân tích Tương quan";
      return "Biểu đồ Phân tích";
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-col w-full md:w-5/6 ml-0 md:ml-64"> {/* Adjust margin */}
        <Header />
        {notification.show && notification.onClose && (
          <NotificationToast message={notification.message} type={notification.type} onClose={notification.onClose} />
        )}
        <main className="flex-grow p-4 sm:p-6 bg-gray-100">
          <h1 className="text-2xl sm:text-3xl font-bold text-center mb-6 sm:mb-8 text-gray-700">
             <TrendingUp size={30} className="inline-block mr-3 text-purple-500"/>Phân tích Nâng cao & Dự đoán AI
          </h1>

          <div className="mb-6 bg-white p-4 sm:p-6 rounded-xl shadow-lg border border-gray-200">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                {/* Tabs */}
                <div className="flex border-b border-gray-200">
                    <button
                    className={`px-3 sm:px-4 py-2.5 font-medium text-sm sm:text-base border-b-2 transition-colors flex items-center ${selectedAnalysisType === 'prediction' ? 'text-blue-600 border-blue-600' : 'text-gray-500 hover:text-gray-700 border-transparent hover:border-gray-300'}`}
                    onClick={() => setSelectedAnalysisType('prediction')} >
                    <TrendingUp className="inline-block w-4 h-4 sm:w-5 sm:h-5 mr-2" /> Dự đoán
                    </button>
                    <button
                    className={`px-3 sm:px-4 py-2.5 font-medium text-sm sm:text-base border-b-2 transition-colors flex items-center ${selectedAnalysisType === 'correlation' ? 'text-blue-600 border-blue-600' : 'text-gray-500 hover:text-gray-700 border-transparent hover:border-gray-300'}`}
                    onClick={() => setSelectedAnalysisType('correlation')} >
                    <BarChart3 className="inline-block w-4 h-4 sm:w-5 sm:h-5 mr-2" /> Tương quan
                    </button>
                </div>
                 {/* Filters */}
                <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-3 text-sm">
                    <Filter className="w-5 h-5 text-gray-500 hidden sm:block" />
                    <label htmlFor="startDate" className="sr-only sm:not-sr-only font-medium text-gray-700">Từ:</label>
                    <input type="date" id="startDate" value={filterStartDate} onChange={(e) => setFilterStartDate(e.target.value)} className="border border-gray-300 p-2 rounded-md focus:ring-1 focus:ring-blue-500"/>
                    <label htmlFor="endDate" className="sr-only sm:not-sr-only font-medium text-gray-700">Đến:</label>
                    <input type="date" id="endDate" value={filterEndDate} onChange={(e) => setFilterEndDate(e.target.value)} className="border border-gray-300 p-2 rounded-md focus:ring-1 focus:ring-blue-500"/>
                    <button onClick={handleApplyFilters} disabled={isLoadingAnalytics}
                        className="w-full sm:w-auto px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition text-sm disabled:opacity-70">
                        Áp dụng
                    </button>
                </div>
            </div>
          </div>


          {isLoadingAnalytics ? (
            <Loading />
          ) : currentErrorMessage ? (
             <div className="bg-red-50 p-6 rounded-lg shadow-md text-center border border-red-200">
                <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3"/>
                <h3 className="text-lg font-semibold text-red-700">Lỗi tải dữ liệu phân tích</h3>
                <p className="text-red-600 mt-1">{currentErrorMessage}</p>
             </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              <div className="lg:col-span-3 bg-white p-4 sm:p-6 rounded-xl shadow-xl border border-gray-200">
                {/* <h2 className="text-lg sm:text-xl font-semibold mb-4 text-gray-700">{getChartTitle()}</h2> */}
                {chartDisplayData && chartDisplayData.labels && chartDisplayData.labels.length > 0 ? (
                  <SensorChart
                    title={getChartTitle()} // Passed title to SensorChart
                    chartData={chartDisplayData} // {labels, values}
                    yAxisLabel={selectedAnalysisType === 'prediction' ? 'Giá trị Dự đoán' : (selectedAnalysisType === 'correlation' ? 'Hệ số Tương quan' : 'Giá trị')}
                    lineColor={selectedAnalysisType === 'prediction' ? "#8A2BE2" : "#4682B4"} // Example different colors
                  />
                ) : (
                  <div className="h-72 md:h-80 flex flex-col items-center justify-center text-gray-500">
                    <Info size={32} className="mb-2 text-gray-400"/>
                    <p>Không có dữ liệu biểu đồ cho loại phân tích này.</p>
                  </div>
                )}
              </div>

              <div className="lg:col-span-2 bg-white p-6 rounded-xl shadow-xl border border-gray-200">
                <h2 className="text-lg sm:text-xl font-semibold mb-4 text-gray-700">Diễn giải Kết quả Phân tích</h2>
                <div className="text-gray-700 text-sm leading-relaxed whitespace-pre-wrap prose prose-sm max-w-none">
                  {analysisTextResult || "Chọn loại phân tích và áp dụng bộ lọc để xem kết quả chi tiết."}
                </div>
              </div>
            </div>
          )}
        </main>
        <Footer />
      </div>
    </div>
  );
};

export default AdvancedAnalytics;