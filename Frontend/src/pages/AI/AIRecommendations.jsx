// src/pages/AI/AIRecommendations.jsx
import React, { useState, useEffect, useMemo } from 'react';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import Sidebar from '../../components/Sidebar';
import aiRecommendationsService from '../../utils/aiRecommendationsService'; // Updated service
import NotificationToast from '../../components/NotificationToast';
import { Lightbulb, Droplet, Thermometer, CalendarCheck, History, Send, AlertTriangle, CheckCircle, ListChecks, Clock4 } from 'lucide-react';
import Loading from '../../components/Loading'; // Import Loading component

// Helper to get icons and colors based on recommendation content/type if not directly provided by API
const getRecommendationVisuals = (recommendation) => {
  // Try to infer from reason or specific fields in recommendation object
  const reasonText = recommendation?.reason?.toLowerCase() || "";
  const zones = recommendation?.zones || [];
  let icon = Lightbulb;
  let color = 'bg-blue-100 text-blue-800 border-blue-300'; // Default
  let typeText = "Chung";

  if (zones.some(z => z.plant_types?.includes("tomato"))) {
      typeText = "Cà Chua";
  } else if (zones.some(z => z.plant_types?.includes("cucumber"))) {
      typeText = "Dưa chuột";
  } else if (zones.some(z => z.plant_types?.includes("lettuce"))) {
       typeText = "Xà lách";
  }
  
  if (reasonText.includes("soil") || recommendation?.should_irrigate) {
    icon = Droplet;
    color = 'bg-sky-100 text-sky-800 border-sky-300';
    typeText = `Tưới (${typeText})`;
  } else if (reasonText.includes("temperature") || reasonText.includes("nhiệt độ")) {
    icon = Thermometer;
    color = 'bg-red-100 text-red-800 border-red-300';
    typeText = `Nhiệt độ (${typeText})`;
  } else if (reasonText.includes("light") || reasonText.includes("ánh sáng")) {
    icon = Lightbulb; // already default
    color = 'bg-yellow-100 text-yellow-800 border-yellow-300';
    typeText = `Ánh sáng (${typeText})`;
  }
  return { IconComponent: icon, typeColorClass: color, typeText };
};


const RecommendationHistoryCard = ({ item, onResend }) => {
  // item is from GET /api/recommendation/history response
  // { id, timestamp, recommendation: {should_irrigate, zones, reason,...}, status, result: {...}, displayTimestamp, isActionable }
  const { recommendation, status, result, displayTimestamp, isActionable } = item;
  const { IconComponent, typeColorClass, typeText } = getRecommendationVisuals(recommendation);

  let statusText = "Không rõ";
  let statusColor = "bg-gray-100 text-gray-700";
  let StatusIcon = ListChecks;

  switch(status) {
      case 'created': statusText = "Mới tạo"; statusColor = "bg-blue-100 text-blue-700"; StatusIcon=Clock4; break;
      case 'sent_to_core': statusText = "Đã gửi đi"; statusColor = "bg-indigo-100 text-indigo-700"; StatusIcon=Send; break;
      case 'applied':
      case 'completed': statusText = "Đã áp dụng"; statusColor = "bg-green-100 text-green-700"; StatusIcon=CheckCircle; break;
      case 'rejected_by_core':
      case 'failed': statusText = "Thất bại/Từ chối"; statusColor = "bg-red-100 text-red-700"; StatusIcon=AlertTriangle; break;
      default: statusText = status || "Không rõ";
  }
  
  const wasIrrigationRecommended = recommendation?.should_irrigate;

  return (
    <div className="bg-white p-5 rounded-lg shadow-md border hover:shadow-lg transition-shadow duration-300">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center">
            <div className={`p-2 rounded-full mr-3 ${typeColorClass.split(' ')[0]}`}>
                 <IconComponent size={20} className={`${typeColorClass.split(' ')[1]}`} />
            </div>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${typeColorClass}`}>
                {typeText}
            </span>
        </div>
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full flex items-center ${statusColor}`}>
            <StatusIcon size={14} className="mr-1"/> {statusText}
        </span>
      </div>

      <p className="text-sm text-gray-500 mb-1">ID: <span className="font-mono text-gray-700">{item.id}</span></p>
      <p className="text-sm text-gray-500 mb-3">Thời gian: <span className="text-gray-700 font-medium">{displayTimestamp}</span></p>
      
      <div className="bg-gray-50 p-3 rounded-md mb-3">
        <p className="text-sm text-gray-700 font-medium mb-1">Khuyến nghị chính:</p>
        <p className="text-sm text-gray-600">{recommendation?.reason || "Không có lý do cụ thể."}</p>
        {wasIrrigationRecommended && recommendation?.zones?.map((zone, idx) => (
            <div key={idx} className="mt-1 pl-2 border-l-2 border-gray-300 text-xs">
                <p><strong>Vùng:</strong> {zone.zone_id} ({zone.plant_types?.join(', ')})</p>
                <p><strong>Tưới:</strong> {zone.should_irrigate ? `Có, ${zone.duration_minutes} phút` : 'Không'}</p>
                {zone.irrigation_time && <p><strong>Giờ tưới dự kiến:</strong> {zone.irrigation_time}</p>}
            </div>
        ))}
      </div>

      {result && (
        <div className="bg-green-50 p-3 rounded-md mb-3 border border-green-200">
          <p className="text-sm text-green-700 font-medium mb-1">Kết quả thực tế:</p>
          <p className="text-xs text-green-600">
            Hoàn thành: {result.irrigation_completed ? 'Có' : 'Không'}. Thời lượng thực tế: {result.actual_duration?.toFixed(1) || 'N/A'} phút.
          </p>
          {typeof result.soil_moisture_before === 'number' && 
            <p className="text-xs text-green-600">Độ ẩm đất: {result.soil_moisture_before}% → {result.soil_moisture_after}%</p>}
        </div>
      )}
      
      {isActionable && onResend && (
          <button 
            onClick={() => onResend(item.id)}
            className="w-full mt-2 text-xs py-1.5 px-3 bg-blue-500 hover:bg-blue-600 text-white rounded-md transition-colors flex items-center justify-center"
          >
              <Send size={14} className="mr-1.5"/> Gửi lại lệnh tưới
          </button>
      )}
    </div>
  );
};

const OptimizedScheduleDisplay = ({ scheduleData }) => {
  // scheduleData from GET /api/recommendation/optimize/schedule
  // { schedule: [{ day, schedule: [{ time, duration_minutes, effectiveness }] }], analysis_period_days, recommendation (text) }
  if (!scheduleData || !scheduleData.schedule || scheduleData.schedule.length === 0) {
    return <p className="text-gray-500 text-center py-8">Không có lịch tưới tối ưu nào được tạo.</p>;
  }

  const dayOrder = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

  return (
    <div className="bg-white p-6 rounded-xl shadow-xl space-y-6">
        <div>
            <h3 className="text-xl font-semibold text-gray-700 mb-1">Lịch Tưới Tối ưu bởi AI</h3>
            <p className="text-sm text-gray-500">Dựa trên phân tích {scheduleData.analysis_period_days || 'N/A'} ngày. {scheduleData.recommendation}</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {scheduleData.schedule.sort((a,b) => dayOrder.indexOf(a.day) - dayOrder.indexOf(b.day)).map(dayEntry => (
                <div key={dayEntry.day} className="p-4 border rounded-lg bg-gray-50">
                    <h4 className="font-semibold text-gray-800 capitalize mb-2 border-b pb-1.5">{daysOfWeekMap.find(d => d.value === dayEntry.day)?.label || dayEntry.day}</h4>
                    {dayEntry.schedule && dayEntry.schedule.length > 0 ? (
                        <ul className="space-y-1.5 text-sm">
                        {dayEntry.schedule.map((slot, idx) => (
                            <li key={idx} className="flex justify-between items-center text-gray-600">
                                <span><Clock4 size={14} className="inline mr-1 opacity-70"/>{slot.time} - {slot.duration_minutes} phút</span>
                                <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded-full" title={`Điểm hiệu quả: ${slot.effectiveness?.toFixed(2) || 'N/A'}`}>
                                    Eff: {(slot.effectiveness * 100 || 0).toFixed(0)}%
                                </span>
                            </li>
                        ))}
                        </ul>
                    ) : (
                        <p className="text-xs text-gray-400 italic">Không có lịch tưới.</p>
                    )}
                </div>
            ))}
        </div>
        <div className="mt-4 text-center">
            <button 
                // onClick={() => aiRecommendationsService.applyOptimizedScheduleToCore(scheduleData)} // Placeholder for future
                onClick={() => alert("Chức năng 'Áp dụng lịch' đang được phát triển!")}
                className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors text-sm disabled:opacity-50"
                // disabled={true} // Enable when implemented
            >
                Áp dụng lịch tối ưu này (Tính năng đang phát triển)
            </button>
        </div>
    </div>
  );
};


const AIRecommendationsPage = () => {
  const [activeTab, setActiveTab] = useState('history'); // 'history' or 'optimizedSchedule'
  const [history, setHistory] = useState([]);
  const [optimizedSchedule, setOptimizedSchedule] = useState(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [isLoadingOptimized, setIsLoadingOptimized] = useState(true);
  const [notification, setNotification] = useState({ show: false, message: "", type: "success" });

  const showToast = (message, type = "success") => {
    setNotification({ show: true, message, type, onClose: () => setNotification(p => ({...p, show: false})) });
  };

  const fetchHistory = async () => {
    setIsLoadingHistory(true);
    const result = await aiRecommendationsService.getRecommendationHistory({ days: 14 }); // Fetch last 14 days
    if (result.success) {
      setHistory(result.data);
    } else {
      showToast(result.error || "Lỗi tải lịch sử khuyến nghị.", "error");
      setHistory([]);
    }
    setIsLoadingHistory(false);
  };

  const fetchOptimizedSchedule = async () => {
    setIsLoadingOptimized(true);
    const result = await aiRecommendationsService.getOptimizedSchedule({ analysis_period_days: 7 }); // Analyze last 7 days for optimization
    if (result.success) {
      setOptimizedSchedule(result.data);
    } else {
      showToast(result.error || "Lỗi tải lịch tưới tối ưu.", "error");
      setOptimizedSchedule(null);
    }
    setIsLoadingOptimized(false);
  };

  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
    } else if (activeTab === 'optimizedSchedule') {
      fetchOptimizedSchedule();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]); 

  const handleResendRecommendation = async (recId) => {
      if(!recId) return;
      showToast("Đang gửi lại khuyến nghị...", "info");
      const result = await aiRecommendationsService.sendRecommendationToCore(recId, {priority: "high"});
      if(result.success){
          showToast(result.data?.message || "Khuyến nghị đã được gửi lại thành công!", "success");
          fetchHistory(); // Refresh history
      } else {
          showToast(result.error || "Gửi lại khuyến nghị thất bại.", "error");
      }
  };

  const tabButtonClass = (tabName) => 
    `px-4 py-2.5 font-medium text-sm sm:text-base border-b-2 transition-colors hover:bg-gray-50 ${
    activeTab === tabName ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
  }`;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-col w-full md:w-5/6 ml-0 md:ml-64">
        <Header />
        {notification.show && notification.onClose && (
          <NotificationToast message={notification.message} type={notification.type} onClose={notification.onClose} />
        )}
        <main className="flex-grow p-4 sm:p-6 bg-gray-100">
          <h1 className="text-2xl sm:text-3xl font-bold text-center mb-6 sm:mb-8 text-gray-700">
            <Lightbulb size={30} className="inline-block mr-3 text-yellow-400"/>Khuyến nghị Thông minh từ AI
          </h1>

          <div className="mb-6 border-b border-gray-200 flex justify-center">
            <button className={tabButtonClass('history')} onClick={() => setActiveTab('history')}>
                <History size={18} className="inline mr-1.5"/> Lịch sử Khuyến nghị
            </button>
            <button className={tabButtonClass('optimizedSchedule')} onClick={() => setActiveTab('optimizedSchedule')}>
                <CalendarCheck size={18} className="inline mr-1.5"/> Lịch Tưới Tối ưu
            </button>
          </div>

          {activeTab === 'history' && (
            isLoadingHistory ? <Loading /> : history.length === 0 ? (
              <p className="text-gray-500 text-center py-10">Không có lịch sử khuyến nghị nào.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                {history.map((item) => (
                  <RecommendationHistoryCard key={item.id} item={item} onResend={handleResendRecommendation}/>
                ))}
              </div>
            )
          )}

          {activeTab === 'optimizedSchedule' && (
            isLoadingOptimized ? <Loading /> : (
              <OptimizedScheduleDisplay scheduleData={optimizedSchedule} />
            )
          )}
        </main>
        <Footer />
      </div>
    </div>
  );
};

export default AIRecommendationsPage;