// src/pages/Reports/Reports.jsx
import React, { useState, useEffect, useCallback } from "react";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Sidebar from "../../components/Sidebar";
import Graph from "../../components/Graph"; // Uses Recharts
import sensorService from "../../utils/sensorService"; // Service đã cập nhật để gọi AI service history
import { Search, PlusCircle, CheckCircle, AlertTriangle, Clock, FileText, Info } from 'lucide-react';
import NotificationToast from "../../components/NotificationToast";
import Modal from "../../components/Modal";
import Loading from "../../components/Loading"; // Import Loading component

const Reports = () => {
  // State for placeholder report list data (sẽ được thay bằng API call sau)
  const [reportListData, setReportListData] = useState([]);
  const [isLoadingReportList, setIsLoadingReportList] = useState(true);
  const [reportListError, setReportListError] = useState(null);

  // State for the combined sensor graph
  const [graphDisplayData, setGraphDisplayData] = useState([]);
  const [isLoadingGraph, setIsLoadingGraph] = useState(true);
  const [graphError, setGraphError] = useState(null);

  // State for modal and filters for report list
  const [selectedReportDetail, setSelectedReportDetail] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] = useState("id");
  const [sortDirection, setSortDirection] = useState("asc");
  
  const [notification, setNotification] = useState({ show: false, message: "", type: "success" });

  const showToast = (message, type = "info") => {
    setNotification({ show: true, message, type, onClose: () => setNotification(prev => ({...prev, show: false}))});
  };

  // Simulate fetching report list (thay thế bằng API thật sau)
  useEffect(() => {
    const fetchReportList = async () => {
      setIsLoadingReportList(true);
      setReportListError(null);
      // TODO: Replace with actual API call using reportService.js or direct api call
      // For now, using placeholder with a delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      const placeholderReports = [
          { _id: "REP001", id: "REP001", name: "Báo cáo Nhiệt độ Tháng 4", status: "Hoàn thành", value: "28°C", date: "2025-05-01", type: "temperature", description: "Nhiệt độ trung bình và biến động trong tháng 4.", author: "AI System" },
          { _id: "REP002", id: "REP002", name: "Phân tích Độ ẩm Đất Tuần 18", status: "Đang tiến hành", value: "45%", date: "2025-05-03", type: "soil", description: "Đánh giá độ ẩm đất và nhu cầu tưới.", author: "John Doe" },
          { _id: "REP003", id: "REP003", name: "Báo cáo Ánh sáng Tổng hợp", status: "Chưa bắt đầu", value: "750 Lux", date: "2025-05-05", type: "light", description: "Phân tích cường độ ánh sáng và ảnh hưởng.", author: "Jane Smith" },
      ];
      setReportListData(placeholderReports);
      // setReportListError("API lấy danh sách báo cáo chưa được định nghĩa."); // Uncomment if API not ready
      setIsLoadingReportList(false);
    };
    fetchReportList();
  }, []);

  // Fetch and format data for the combined sensor graph using sensorService
  const fetchAndFormatGraphData = useCallback(async () => {
    setIsLoadingGraph(true);
    setGraphError(null);
    try {
      const lastHours = 6; // Show last 6 hours for the combined graph
      // sensorService.fetchHistoricalData calls AI service: GET /api/sensors/history?hours=X
      // It returns { chartData: {temperature:{labels,values}, moisture:{...}, light:{...}, soil:{...} }, ... }
      // 'moisture' key is for air humidity, 'soil' for soil moisture
      
      const historicalResult = await sensorService.fetchHistoricalData({ 
          hours: lastHours,
          // Ensure these types align with keys returned by sensorService.processAIHistoricalData
          sensorTypes: ['temperature', 'soil', 'moisture'] // temp, soil_moisture, humidity(air)
      });

      if (historicalResult.error || !historicalResult.chartData) {
        throw new Error(historicalResult.error || "Không thể tải dữ liệu biểu đồ từ service.");
      }
      
      const { temperature, soil, moisture: humidity } = historicalResult.chartData; // Destructure with alias

      // Graph.jsx expects data: [{ time, soil, temp, humidity }, ...]
      // We need to merge data from different sensors by timestamp (label)
      // This requires that all sensor histories have aligned timestamps, or we interpolate/align them.
      // `sensorService.processAIHistoricalData` should ideally return data that can be easily merged or already merged if API allows.
      // Current `processAIHistoricalData` in `sensorService.js` creates separate arrays for each sensor.
      // We will merge them here. This is a common and sometimes complex task.

      const mergedData = [];
      const timestamps = new Set();

      // Collect all unique timestamps
      [temperature, soil, humidity].forEach(sensor => {
        if (sensor?.labels) sensor.labels.forEach(label => timestamps.add(label));
      });

      const sortedTimestamps = Array.from(timestamps).sort((a, b) => {
          // Simple time string sort HH:MM - may need improvement for跨วัน
          return a.localeCompare(b, undefined, {numeric: true});
      });
      
      sortedTimestamps.forEach(time => {
        const dataPoint = { time };
        if (temperature?.labels && temperature?.values) {
          const index = temperature.labels.indexOf(time);
          if (index !== -1) dataPoint.temp = temperature.values[index];
        }
        if (soil?.labels && soil?.values) {
          const index = soil.labels.indexOf(time);
          if (index !== -1) dataPoint.soil = soil.values[index];
        }
        if (humidity?.labels && humidity?.values) {
          const index = humidity.labels.indexOf(time);
          if (index !== -1) dataPoint.humidity = humidity.values[index];
        }
        mergedData.push(dataPoint);
      });

      setGraphDisplayData(mergedData);

    } catch (err) {
      console.error("Failed to fetch or format data for combined graph:", err);
      setGraphError(err.message || "Lỗi tải dữ liệu biểu đồ tổng hợp.");
      showToast(err.message || "Lỗi tải dữ liệu biểu đồ tổng hợp.", "error");
      setGraphDisplayData([]);
    } finally {
      setIsLoadingGraph(false);
    }
  }, []); // No dependencies that would cause re-run unless explicitly called

  useEffect(() => {
    fetchAndFormatGraphData();
  }, [fetchAndFormatGraphData]);


  // Filter and Sort Logic for Report List (Placeholder)
  const getFilteredAndSortedReports = () => {
    return reportListData
    .filter((report) => {
      if (filterStatus !== "all" && report.status !== filterStatus) return false;
      if (searchTerm && !report.name.toLowerCase().includes(searchTerm.toLowerCase()) && !report.id.toLowerCase().includes(searchTerm.toLowerCase()) && !(report.author && report.author.toLowerCase().includes(searchTerm.toLowerCase()))) return false;
      return true;
    })
    .sort((a, b) => {
      let valA = a[sortField]; let valB = b[sortField];
      if (sortField === 'date') { valA = new Date(valA); valB = new Date(valB); }
      else if (typeof valA === 'string') { valA = valA.toLowerCase(); valB = valB.toLowerCase(); }
      if (valA < valB) return sortDirection === "asc" ? -1 : 1;
      if (valA > valB) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });
  };

  const handleSort = (field) => { /* ... (keep existing) ... */ };
  const handleRowClick = (report) => { setSelectedReportDetail(report); setIsDetailModalOpen(true); };
  const closeModal = () => { setIsDetailModalOpen(false); setSelectedReportDetail(null); };
  const getStatusVisual = (status) => { /* ... (keep existing) ... */ };
  
  const filteredReportDisplayList = getFilteredAndSortedReports();

  if (isLoadingReportList && isLoadingGraph) { // Combined initial loading
    return <Loading />;
  }

  return (
  <div className="flex min-h-screen bg-gray-100"> {/* Changed bg */}
  <Sidebar />
  <div className="flex flex-col w-full md:w-5/6 ml-0 md:ml-64">
    <Header />
    {notification.show && notification.onClose && (
      <NotificationToast message={notification.message} type={notification.type} onClose={notification.onClose}/>
    )}
    <main className="flex-grow container mx-auto py-6 px-4 sm:px-6 lg:px-8">
      <div className="flex flex-col sm:flex-row justify-between items-center mb-6 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-700 flex items-center">
            <FileText size={28} className="mr-3 text-indigo-500"/> Báo cáo & Phân tích
        </h1>
        {/* Add refresh button for reports page maybe? */}
      </div>
      

      {/* Combined Sensor Graph Section */}
      <div className="mb-8 bg-white rounded-xl shadow-xl p-4 sm:p-6 border border-gray-200">
        <h2 className="text-xl font-semibold text-gray-700 mb-4">Biểu đồ Cảm biến Tổng hợp (6 giờ qua)</h2>
        {isLoadingGraph ? (
            <div className="h-[360px] flex justify-center items-center"><div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-blue-500"></div></div>
        ) : graphError ? (
            <div className="h-[360px] flex flex-col justify-center items-center text-red-500">
                <AlertTriangle size={32} className="mb-2"/> <p>{graphError}</p>
                <button onClick={fetchAndFormatGraphData} className="mt-2 px-3 py-1 bg-red-100 text-red-600 border border-red-300 rounded hover:bg-red-200 text-sm">Thử lại</button>
            </div>
        ) : graphDisplayData.length > 0 ? (
          <Graph data={graphDisplayData} title="" /> 
        ) : (
          <div className="h-[360px] flex flex-col justify-center items-center text-gray-500">
            <Info size={32} className="mb-2"/> <p>Không có dữ liệu để hiển thị biểu đồ tổng hợp.</p>
          </div>
        )}
      </div>


      {/* Report List Section */}
      <div className="bg-white rounded-xl shadow-xl p-4 sm:p-6 border border-gray-200">
        <div className="flex flex-col sm:flex-row justify-between items-center mb-5 gap-3">
          <h2 className="text-xl font-semibold text-gray-700">
            Danh sách Báo cáo Hệ thống
          </h2>
          <div className="flex flex-col sm:flex-row items-center space-y-2 sm:space-y-0 sm:space-x-2 w-full sm:w-auto">
            {/* Search and Filter UI - keep existing */}
             <div className="relative w-full sm:w-auto">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input type="text" placeholder="Tìm báo cáo..."
                className="pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm w-full"
                value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
            </div>
            <select className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm w-full sm:w-auto bg-white"
              value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="all">Tất cả trạng thái</option>
              <option value="Hoàn thành">Hoàn thành</option>
              <option value="Đang tiến hành">Đang tiến hành</option>
              <option value="Chưa bắt đầu">Chưa bắt đầu</option>
            </select>
            {/* <button className="bg-blue-600 text-white px-3 py-2 rounded-lg hover:bg-blue-700 transition flex items-center text-sm w-full sm:w-auto justify-center">
              <PlusCircle className="w-4 h-4 mr-2" />Tạo mới
            </button> */}
          </div>
        </div>
        
        {isLoadingReportList ? (
            <div className="text-center py-8"><div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gray-300 mx-auto"></div><p className="mt-2 text-gray-500 text-sm">Đang tải danh sách báo cáo...</p></div>
        ) : reportListError ? (
            <div className="py-8 text-center text-red-500 bg-red-50 p-4 rounded-md border border-red-200">
                <AlertTriangle size={24} className="mx-auto mb-2"/> {reportListError}
            </div>
        ) : filteredReportDisplayList.length === 0 ? (
            <div className="py-8 text-center text-gray-500"><Info size={24} className="mx-auto mb-2 text-gray-400"/>Không tìm thấy báo cáo nào khớp.</div>
        ) : (
            <div className="overflow-x-auto">
                <table className="min-w-full table-auto text-sm">
                {/* ... Table Head from your existing code ... */}
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    {[{key:'id',label:'Mã'}, {key:'name',label:'Tên Báo Cáo'}, {key:'status',label:'Trạng Thái'}, {key:'date',label:'Ngày'}, {key:'author',label:'Tác Giả'}].map(field => (
                        <th key={field.key} className="px-4 py-3 text-left font-medium tracking-wider cursor-pointer hover:bg-gray-100" onClick={() => handleSort(field.key)}>
                        {field.label}
                        {sortField === field.key && (sortDirection === 'asc' ? ' ▲' : ' ▼')}
                        </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                {filteredReportDisplayList.map((report) => (
                    <tr key={report._id || report.id} className="hover:bg-gray-50/70 transition-colors duration-150 cursor-pointer" onClick={() => handleRowClick(report)}>
                    <td className="px-4 py-3 whitespace-nowrap text-gray-600 font-mono text-xs">{report.id}</td>
                    <td className="px-4 py-3 whitespace-normal font-medium text-gray-800">{report.name}</td>
                    <td className="px-4 py-3 whitespace-nowrap"><div className="flex items-center text-gray-600">{getStatusVisual(report.status)} {report.status}</div></td>
                    <td className="px-4 py-3 whitespace-nowrap text-gray-500">{new Date(report.date).toLocaleDateString('vi-VN')}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-gray-600">{report.author}</td>
                    </tr>
                ))}
                </tbody>
                </table>
            </div>
        )}
      </div>

      {selectedReportDetail && isDetailModalOpen && (
        <Modal isOpen={isDetailModalOpen} onClose={closeModal} title={`Chi tiết Báo cáo: ${selectedReportDetail.name}`}>
            {/* Modal Content - keep existing */}
             <div className="text-sm space-y-2.5">
                <p><strong>Mã Báo Cáo:</strong> <span className="font-mono">{selectedReportDetail.id}</span></p>
                <p><strong>Mô tả:</strong> {selectedReportDetail.description || <span className="italic text-gray-400">Không có mô tả.</span>}</p>
                <p><strong>Trạng thái:</strong> {selectedReportDetail.status}</p>
                {selectedReportDetail.value && <p><strong>Giá trị chính:</strong> {selectedReportDetail.value}</p>}
                <p><strong>Tác giả:</strong> {selectedReportDetail.author}</p>
                <p><strong>Ngày tạo:</strong> {new Date(selectedReportDetail.date).toLocaleDateString('vi-VN')}</p>
                {selectedReportDetail.type && <p><strong>Loại báo cáo:</strong> <span className="capitalize">{selectedReportDetail.type.replace('_', ' ')}</span></p>}
            </div>
            <div className="mt-6 flex justify-end">
              <button className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition text-sm" onClick={closeModal}>Đóng</button>
            </div>
        </Modal>
      )}
    </main>
    <Footer />
  </div>
  </div>
  );
  };
  export default Reports;