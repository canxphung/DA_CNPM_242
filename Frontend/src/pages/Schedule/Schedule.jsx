// pages/Schedule/Schedule.jsx
import React, { useState, useEffect } from "react";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Sidebar from "../../components/Sidebar";
import { ScheduleProvider, useSchedule } from "../../contexts/ScheduleContext";
import { FcEditImage, FcFullTrash } from "react-icons/fc";
import { CalendarDays, Clock, Timer, Repeat, Info, CheckSquare, Square, RefreshCw } from 'lucide-react'; // Added RefreshCw
import NotificationToast from "../../components/NotificationToast";

const daysOfWeekMap = [
  { value: "monday", label: "T2" }, { value: "tuesday", label: "T3" },
  { value: "wednesday", label: "T4" }, { value: "thursday", label: "T5" },
  { value: "friday", label: "T6" }, { value: "saturday", label: "T7" },
  { value: "sunday", label: "CN" },
];

const ScheduleContent = () => {
  const {
    events, history, loading, error, addSchedule, deleteSchedule, updateSchedule, fetchSchedules
  } = useSchedule();
  
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const initialFormData = {
    title: "",
    days_of_week: [],
    start_time: "",
    duration_minutes: "5",
    active: true,
    description: ""
  };
  const [formData, setFormData] = useState(initialFormData);
  const [formErrors, setFormErrors] = useState({});
  const [notification, setNotification] = useState({ show: false, message: "", type: "info" });

  const showToast = (message, type = "info") => {
    setNotification({ show: true, message, type, onClose: () => setNotification(p => ({...p, show: false})) });
  };

  useEffect(() => {
    if (error) {
      showToast(`Lỗi: ${error}`, "error");
    }
  }, [error]);

  const validateForm = () => {
    const errors = {};
    if (!formData.title.trim()) errors.title = "Tên sự kiện không được để trống.";
    if (formData.days_of_week.length === 0) errors.days_of_week = "Vui lòng chọn ít nhất một ngày.";
    if (!formData.start_time) errors.start_time = "Thời gian bắt đầu không được để trống.";
    const durationNum = parseInt(formData.duration_minutes);
    if (isNaN(durationNum) || durationNum <= 0) errors.duration_minutes = "Thời lượng phải là số dương.";
    else if (durationNum > 120) errors.duration_minutes = "Thời lượng không nên quá 2 tiếng (120 phút).";
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleFormInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (type === 'checkbox' && name === 'day_toggle') {
        setFormData(prev => ({
            ...prev,
            days_of_week: checked 
                ? [...prev.days_of_week, value]
                : prev.days_of_week.filter(day => day !== value)
        }));
    } else if (type === 'checkbox' && name === 'active'){
         setFormData(prev => ({ ...prev, active: checked }));
    } else {
        setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleSubmitEvent = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    const payload = {
      ...formData,
      duration_seconds: parseInt(formData.duration_minutes) * 60,
    };

    setNotification({show: false, message: ""});
    const result = isEditing
      ? await updateSchedule(editingId, payload)
      : await addSchedule(payload);

    if (result.success) {
      showToast(result.message || (isEditing ? "Lịch trình đã được cập nhật!" : "Lịch trình đã được thêm!"), "success");
      setFormData(initialFormData);
      setIsEditing(false);
      setEditingId(null);
      setFormErrors({});
    } else {
      showToast(result.message || (isEditing ? "Lỗi cập nhật lịch trình." : "Lỗi thêm lịch trình."), "error");
    }
  };

  const handleEditEvent = (eventToEdit) => {
    setIsEditing(true);
    setEditingId(eventToEdit.id);
    setFormData({
      title: eventToEdit.name,
      days_of_week: eventToEdit.days || [],
      start_time: eventToEdit.start_time || "",
      duration_minutes: eventToEdit.duration_seconds ? (eventToEdit.duration_seconds / 60).toString() : "5",
      active: typeof eventToEdit.active === 'boolean' ? eventToEdit.active : true,
      description: eventToEdit.description || ""
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDeleteEvent = async (id) => {
    if (window.confirm("Bạn có chắc chắn muốn xoá lịch trình này không?")) {
      setNotification({show: false, message: ""});
      const result = await deleteSchedule(id);
      showToast(result.message || (result.success ? "Đã xoá lịch trình!" : "Lỗi khi xoá."), result.success ? "success" : "error");
    }
  };
  
  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditingId(null);
    setFormData(initialFormData);
    setFormErrors({});
  };

  if (loading && events.length === 0 && history.length === 0) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex flex-col flex-1 ml-64">
          <Header />
          <div className="flex justify-center items-center flex-grow">
            <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-blue-500"></div>
            <span className="ml-4 text-xl font-medium text-gray-600">Đang tải dữ liệu lịch trình...</span>
          </div>
          <Footer />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-emerald-50">
      <Sidebar />
      <div className="flex flex-col flex-1 ml-64">
        <Header />
         {notification.show && notification.onClose && (
          <NotificationToast
            message={notification.message}
            type={notification.type}
            onClose={notification.onClose}
          />
        )}
        <main className="flex-grow px-4 sm:px-8 py-6">
          <div className="text-center mb-8">
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-2">Lịch tưới cây</h1>
            <p className="text-gray-500 text-sm sm:text-base">Quản lý và theo dõi lịch trình tưới cây của bạn.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mt-8">
            {/* Form Section - Col 1 */}
            <div className="md:col-span-1 bg-white shadow-xl rounded-2xl p-6 self-start">
              <h2 className="text-xl font-semibold mb-5 text-gray-700 border-b pb-3">
                {isEditing ? "✏️ Chỉnh sửa Lịch Trình" : "➕ Thêm Lịch Trình Mới"}
              </h2>
              <form onSubmit={handleSubmitEvent} className="space-y-4 text-sm">
                <div>
                  <label htmlFor="title" className="block font-medium text-gray-700 mb-1">Tên lịch trình <span className="text-red-500">*</span></label>
                  <input type="text" name="title" id="title" value={formData.title} onChange={handleFormInputChange}
                    className="w-full p-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500" placeholder="VD: Tưới rau buổi sáng" />
                  {formErrors.title && <p className="text-red-500 text-xs mt-1">{formErrors.title}</p>}
                </div>
                
                <div>
                  <label className="block font-medium text-gray-700 mb-1.5">Ngày trong tuần <span className="text-red-500">*</span></label>
                  <div className="grid grid-cols-4 sm:grid-cols-4 gap-2">
                    {daysOfWeekMap.map(day => (
                      <label key={day.value} htmlFor={`day_${day.value}`} className={`flex items-center space-x-1.5 p-1.5 border rounded-md cursor-pointer text-xs sm:text-sm hover:bg-blue-50 ${formData.days_of_week.includes(day.value) ? 'bg-blue-100 border-blue-400 ring-1 ring-blue-400' : 'border-gray-300'}`}>
                        <input type="checkbox" id={`day_${day.value}`} name="day_toggle" value={day.value}
                               checked={formData.days_of_week.includes(day.value)} onChange={handleFormInputChange}
                               className="h-3.5 w-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500" />
                        <span>{day.label}</span>
                      </label>
                    ))}
                  </div>
                   {formErrors.days_of_week && <p className="text-red-500 text-xs mt-1">{formErrors.days_of_week}</p>}
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label htmlFor="start_time" className="block font-medium text-gray-700 mb-1">Giờ bắt đầu <span className="text-red-500">*</span></label>
                        <input type="time" name="start_time" id="start_time" value={formData.start_time} onChange={handleFormInputChange}
                                className="w-full p-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"/>
                        {formErrors.start_time && <p className="text-red-500 text-xs mt-1">{formErrors.start_time}</p>}
                    </div>
                    <div>
                        <label htmlFor="duration_minutes" className="block font-medium text-gray-700 mb-1">Thời lượng (phút) <span className="text-red-500">*</span></label>
                        <input type="number" name="duration_minutes" id="duration_minutes" min="1" max="120" value={formData.duration_minutes} onChange={handleFormInputChange}
                            className="w-full p-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500" placeholder="VD: 10" />
                        {formErrors.duration_minutes && <p className="text-red-500 text-xs mt-1">{formErrors.duration_minutes}</p>}
                    </div>
                </div>

                <div>
                  <label htmlFor="description" className="block font-medium text-gray-700 mb-1">Mô tả</label>
                  <textarea name="description" id="description" value={formData.description} onChange={handleFormInputChange} rows="2"
                    className="w-full p-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500" placeholder="Ghi chú thêm (nếu có)"></textarea>
                </div>

                 <div className="flex items-center pt-1">
                    <input type="checkbox" name="active" id="active" checked={formData.active} onChange={handleFormInputChange} className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mr-2"/>
                    <label htmlFor="active" className="font-medium text-gray-700">Kích hoạt lịch trình này</label>
                 </div>

                <div className="flex gap-3 pt-2">
                    <button type="submit"
                        className="flex-1 bg-blue-600 hover:bg-blue-700 transition text-white font-medium py-2.5 rounded-lg disabled:opacity-70"
                        disabled={loading}
                    >
                        {isEditing ? "Cập nhật" : "Thêm mới"}
                    </button>
                    {isEditing && (
                        <button type="button" onClick={handleCancelEdit}
                            className="flex-1 bg-gray-200 hover:bg-gray-300 transition text-gray-700 font-medium py-2.5 rounded-lg">
                            Hủy
                        </button>
                    )}
                </div>
              </form>
            </div>

            {/* Event List & History - Col 2 & 3 */}
            <div className="md:col-span-2 space-y-6">
                 {/* Upcoming Events */}
                <div className="bg-white shadow-xl rounded-2xl p-6 overflow-x-auto">
                <h2 className="text-xl sm:text-2xl font-semibold text-gray-700 mb-4 flex items-center">
                    <CalendarDays size={22} className="mr-2.5 text-blue-500"/> Danh sách Lịch trình
                     <button onClick={()=> fetchSchedules()} title="Làm mới danh sách lịch" className="ml-auto p-1.5 rounded-full hover:bg-gray-100 transition-colors disabled:opacity-50" disabled={loading}>
                        <RefreshCw size={16} className={`text-gray-500 ${loading ? 'animate-spin': ''}`}/>
                    </button>
                </h2>
                 {loading && events.length === 0 && <p className="text-gray-500 text-sm">Đang tải danh sách...</p>}
                 {!loading && events.length === 0 && <p className="text-gray-500 text-sm italic">Chưa có lịch trình nào được tạo.</p>}
                {events.length > 0 && (
                    <div className="max-h-[400px] overflow-y-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-gray-50 sticky top-0">
                        <tr>
                            <th className="p-3 font-semibold text-gray-600">Tên Lịch</th>
                            <th className="p-3 font-semibold text-gray-600">Ngày tưới</th>
                            <th className="p-3 font-semibold text-gray-600">Giờ</th>
                            <th className="p-3 font-semibold text-gray-600">Thời lượng</th>
                            <th className="p-3 font-semibold text-gray-600">Trạng thái</th>
                            <th className="p-3 font-semibold text-gray-600 text-center">Thao tác</th>
                        </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                        {events.map((event) => (
                            <tr key={event.id} className="hover:bg-blue-50/50 transition-colors">
                            <td className="p-3 font-medium text-gray-800">{event.name}</td>
                            <td className="p-3 text-gray-600">
                                {event.days.map(d => daysOfWeekMap.find(m => m.value === d)?.label || d).join(', ')}
                            </td>
                            <td className="p-3 text-gray-600">{event.start_time}</td>
                            <td className="p-3 text-gray-600">{event.duration_seconds / 60} phút</td>
                            <td className="p-3">
                                <span className={`px-2 py-0.5 text-xs rounded-full font-semibold ${event.active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'}`}>
                                {event.active ? 'Hoạt động' : 'Tạm dừng'}
                                </span>
                            </td>
                            <td className="p-3 text-center">
                                <button onClick={() => handleEditEvent(event)} title="Chỉnh sửa" className="p-1.5 hover:bg-yellow-100 rounded-full text-yellow-600 transition-colors"><FcEditImage className="w-4 h-4" /></button>
                                <button onClick={() => handleDeleteEvent(event.id)} title="Xóa" className="p-1.5 hover:bg-red-100 rounded-full text-red-600 transition-colors ml-1"><FcFullTrash className="w-4 h-4" /></button>
                            </td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    </div>
                )}
                </div>
                
                {/* History */}
                <div className="bg-white shadow-xl rounded-2xl p-6 overflow-x-auto">
                <h2 className="text-xl sm:text-2xl font-semibold text-gray-700 mb-4 flex items-center">
                    <Clock size={22} className="mr-2.5 text-green-500"/> Lịch sử Tưới
                </h2>
                 {loading && history.length === 0 && <p className="text-gray-500 text-sm">Đang tải lịch sử...</p>}
                 {!loading && history.length === 0 && <p className="text-gray-500 text-sm italic">Chưa có dữ liệu lịch sử tưới.</p>}
                 {history.length > 0 && (
                    <div className="max-h-[300px] overflow-y-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-gray-50 sticky top-0">
                        <tr>
                            <th className="p-3 font-semibold text-gray-600">Sự kiện</th>
                            <th className="p-3 font-semibold text-gray-600">Ngày</th>
                            <th className="p-3 font-semibold text-gray-600">Thời gian</th>
                            <th className="p-3 font-semibold text-gray-600">Thời lượng</th>
                            <th className="p-3 font-semibold text-gray-600">Độ ẩm đất</th>
                            <th className="p-3 font-semibold text-gray-600">Trạng thái</th>
                        </tr>
                        </thead>
                         <tbody className="divide-y divide-gray-100">
                        {history.map((h, index) => (
                            <tr key={h.id || index} className="hover:bg-green-50/50 transition-colors">
                                <td className="p-3 font-medium text-gray-800">{h.title || `ID: ${h.id?.slice(-5)}`}</td>
                                <td className="p-3 text-gray-600">{h.date}</td>
                                <td className="p-3 text-gray-600">{h.time}</td>
                                <td className="p-3 text-gray-600">{h.duration_minutes ? `${h.duration_minutes} phút` : 'N/A'}</td>
                                <td className="p-3 text-gray-600">{h.moisture !== "N/A" ? `${h.moisture}%` : 'N/A'}</td>
                                <td className="p-3">
                                    <span className={`px-2 py-0.5 text-xs rounded-full font-semibold capitalize ${
                                        h.status === 'completed' || h.status === 'applied' ? 'bg-green-100 text-green-700' :
                                        h.status === 'failed' ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-700'}`}>
                                    {h.status || 'Không rõ'}
                                    </span>
                                </td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    </div>
                 )}
                </div>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    </div>
  );
};

const Schedule = () => (
  <ScheduleProvider>
    <ScheduleContent />
  </ScheduleProvider>
);

export default Schedule;