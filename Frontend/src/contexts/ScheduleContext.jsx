// contexts/ScheduleContext.jsx
import React, { createContext, useState, useEffect, useContext } from "react";
// import api from "../utils/api"; // No longer directly using api here, use schedulingService
import schedulingService from "../utils/schedulingService"; // Import the service

export const ScheduleContext = createContext();

export const ScheduleProvider = ({ children }) => {
  const [events, setEvents] = useState([]); // Upcoming/pending schedules from Core Ops
  const [history, setHistory] = useState([]); // Past COMPLETED irrigation events (NEEDS API)
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSchedulesAndExecutionHistory = async () => {
    setLoading(true);
    setError(null);
    let schedulesFetched = false;
    let historyFetched = false;

    try {
      // Fetch active/pending schedules
      const schedulesRes = await schedulingService.getSchedules();
      if (schedulesRes.success) {
        // Core Ops schedules: {id, name, days, start_time, duration, active, description, created_at, updated_at}
        // Map to the format 'events' state expects, primarily for display on Schedule page.
        // 'Schedule.jsx' expects { _id (use id), title (use name), name (use name), date (needs constructing) }
        const parsedEvents = (schedulesRes.data || []).map(item => {
            // For displaying upcoming events, we need to calculate the next actual date/time
            // This is complex if 'days' is like ["monday", "friday"].
            // For simplicity, if we only show them as defined (not specific next run time) then:
            // A simpler mapping for now, actual "next run" logic would be more involved for recurring.
            // Let's make 'date' store start_time for display simplicity or just raw schedule info.
            // The `DeviceStatusMonitor` / `getIrrigationStatus` gives `nextScheduledEvent`.
            // This context provides data for `/schedule` page.
            return {
              _id: item.id, // Map 'id' to '_id' for compatibility if DeleteEvent uses _id
              id: item.id,
              title: item.name,
              name: item.name, // name prop used in Schedule.jsx
              // How 'date' (full datetime) was previously used needs re-evaluation.
              // API gives 'days' array and 'start_time' (HH:MM).
              // We store them raw and let the component format as needed.
              days: item.days || [], 
              start_time: item.start_time, // "HH:MM"
              duration_seconds: item.duration, // seconds
              active: item.active,
              description: item.description,
              created_at: item.created_at,
              updated_at: item.updated_at
            };
        }).sort((a,b) => { // Sort by start_time for display order
            if (a.start_time && b.start_time) return a.start_time.localeCompare(b.start_time);
            return 0;
        });
        setEvents(parsedEvents);
        schedulesFetched = true;
      } else {
        setError(prev => `${prev || ''} Lỗi tải lịch: ${schedulesRes.error}. `);
      }

      // Fetch irrigation execution history (placeholder, depends on actual API)
      const historyRes = await schedulingService.getIrrigationHistory({ days: 30 }); // Fetch last 30 days
      if (historyRes.success) {
        // `historyRes.data` is now array like:
        // { id, title, date (dd/mm/yyyy), time (hh:mm), moisture, temperature, duration_minutes, status }
        // OR an empty array if placeholder
        setHistory(historyRes.data);
        historyFetched = true;
        if(historyRes.message) console.info(historyRes.message); // Log message from service (e.g. placeholder warning)
      } else {
        setError(prev => `${prev || ''} Lỗi tải lịch sử tưới: ${historyRes.error}. `);
      }

      if (!schedulesFetched && !historyFetched) {
        // Both failed or no data for both and errored out.
      }

    } catch (err) { // Catch unexpected errors from service calls
      console.error("Error in fetchSchedulesAndExecutionHistory (context):", err);
      setError("Lỗi hệ thống khi tải dữ liệu lịch trình.");
      setEvents([]); 
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchSchedulesAndExecutionHistory();
    // const interval = setInterval(fetchSchedulesAndExecutionHistory, 60000 * 5); // Refresh every 5 minutes
    // return () => clearInterval(interval);
    // Disabling interval for now, refresh can be manual or on specific actions.
  }, []);


  // addSchedule expects data from the form in Schedule.jsx
  // Form needs to provide: name, days (array), start_time (HH:MM), duration (seconds), active (boolean), description
  const addSchedule = async (scheduleDataFromForm) => {
    // scheduleDataFromForm: { title (for name), datetime (YYYY-MM-DDTHH:mm), duration_minutes, days_of_week (array) }
    // This needs conversion to API payload: { name, days, start_time, duration, active, description }

    const payload = {
        name: scheduleDataFromForm.title,
        days: scheduleDataFromForm.days_of_week || [], // Ensure it's an array
        start_time: scheduleDataFromForm.start_time, // Expects "HH:MM"
        duration: parseInt(scheduleDataFromForm.duration_seconds || 0),
        active: typeof scheduleDataFromForm.active === 'boolean' ? scheduleDataFromForm.active : true, // Default to active
        description: scheduleDataFromForm.description || ""
    };
    
    const result = await schedulingService.createSchedule(payload);
    if (result.success) {
      fetchSchedulesAndExecutionHistory(); // Refetch all
      return { success: true, message: result.message || "Lịch trình đã được thêm.", schedule: result.data };
    } else {
      return { success: false, message: result.error || "Không thể thêm lịch trình." };
    }
  };

  const deleteSchedule = async (scheduleId) => {
    const result = await schedulingService.deleteSchedule(scheduleId);
    if (result.success) {
      fetchSchedulesAndExecutionHistory(); // Refetch
      return { success: true, message: result.message || "Lịch trình đã được xóa." };
    } else {
      return { success: false, message: result.error || "Không thể xóa lịch trình." };
    }
  };

  // updateSchedule expects similar payload structure as addSchedule, plus the ID
  const updateSchedule = async (scheduleId, scheduleDataFromForm) => {
     const payload = {
        name: scheduleDataFromForm.title,
        days: scheduleDataFromForm.days_of_week || [],
        start_time: scheduleDataFromForm.start_time,
        duration: parseInt(scheduleDataFromForm.duration_seconds || 0),
        active: typeof scheduleDataFromForm.active === 'boolean' ? scheduleDataFromForm.active : true,
        description: scheduleDataFromForm.description || ""
    };
    const result = await schedulingService.updateSchedule(scheduleId, payload);
    if (result.success) {
      fetchSchedulesAndExecutionHistory(); // Refetch
      return { success: true, message: result.message || "Lịch trình đã cập nhật.", schedule: result.data };
    } else {
      return { success: false, message: result.error || "Không thể cập nhật lịch trình." };
    }
  };

  const value = {
    events, // List of defined schedules
    history, // List of past irrigation executions (NEEDS API)
    loading,
    error,
    fetchSchedules: fetchSchedulesAndExecutionHistory, // Expose explicit refresh
    addSchedule,
    deleteSchedule,
    updateSchedule,
  };

  return (
    <ScheduleContext.Provider value={value}>
      {children}
    </ScheduleContext.Provider>
  );
};

export const useSchedule = () => {
  const context = useContext(ScheduleContext);
  if (context === undefined) {
    throw new Error("useSchedule must be used within a ScheduleProvider");
  }
  return context;
};