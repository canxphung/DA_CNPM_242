// src/components/NotificationButton.jsx
import { useState, useRef, useEffect } from "react";
import { Bell, BellDot, X } from "lucide-react"; // Added X for close button

const NotificationButton = () => {
  const [hasUnread, setHasUnread] = useState(true);
  const [isOpen, setIsOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const popupRef = useRef(null);
  const buttonRef = useRef(null); // Ref for the button itself

  useEffect(() => {
    const handleClickOutside = (event) => {
      // Check if click is outside popup AND outside the button
      if (
        popupRef.current && !popupRef.current.contains(event.target) &&
        buttonRef.current && !buttonRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const notifications = [
    {
      id: 1,
      title: "Hệ thống cập nhật",
      message: "Phiên bản mới 2.0 đã sẵn sàng",
      time: "10 phút trước",
      read: false,
    },
    {
      id: 2,
      title: "Cảnh báo nhiệt độ",
      message: "Nhiệt độ vượt ngưỡng tại khu vực A",
      time: "1 giờ trước",
      read: true,
    },
    {
      id: 3,
      title: "Bảo trì hệ thống",
      message: "Hệ thống sẽ bảo trì vào 02:00 - 04:00",
      time: "1 ngày trước",
      read: true,
    },
  ];

  const togglePopup = () => {
    setIsOpen(!isOpen);
    if (!isOpen && hasUnread) {
      // Simulate marking as read - in a real app, this would involve an API call or state update
      // For now, let's just visually remove the dot
      // setHasUnread(false); // This would remove the dot immediately upon opening
    }
  };

  const markAllAsRead = () => {
    // Placeholder: In a real app, update notification states and call API
    notifications.forEach(n => n.read = true); // This is a local mutation, not ideal for React state
    setHasUnread(false); // Update the visual indicator
    // You'd typically refetch notifications or update them in a global state
  };

  const unreadCount = notifications.filter(n => !n.read).length;
  useEffect(() => {
    setHasUnread(unreadCount > 0);
  }, [unreadCount]);


  return (
    <div
      className="fixed z-50 
        top-4 right-10  
        md:top-6 md:right-12 /* Adjusted medium screen positioning */
        lg:top-8 lg:right-16 /* Adjusted large screen positioning */
        xl:top-10 xl:right-[6.25rem] /* 100px, equivalent to 25 units if 1 unit = 0.25rem */
        transition-all duration-300"
    //   ref={popupRef} // Ref should be on the popup itself for outside click to work correctly with button
    >
      <button
        ref={buttonRef} // Assign ref to the button
        onClick={togglePopup}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={`relative w-12 h-12 rounded-full flex items-center justify-center shadow-lg transition-all duration-300
          ${
            isOpen
              ? "bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-700"
              : "bg-white hover:bg-gray-100 dark:bg-gray-700 dark:hover:bg-gray-600"
          }
          ${isHovered ? "scale-110 shadow-xl" : "scale-100"}`}
        aria-label="Notifications"
      >
        {hasUnread ? (
          <BellDot className="w-6 h-6 text-amber-500 dark:text-amber-400" />
        ) : (
          <Bell className="w-6 h-6 text-gray-700 dark:text-gray-300" />
        )}
         {hasUnread && unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">
            {unreadCount}
          </span>
        )}
      </button>

      <div
        className={`absolute right-full mr-2 top-1/2 -translate-y-1/2 
          bg-gray-800 dark:bg-gray-700 text-white text-xs px-2 py-1 rounded-md 
          transition-opacity duration-300 pointer-events-none 
          ${isHovered && !isOpen ? "opacity-100" : "opacity-0"}
          hidden md:block 
        `}
      >
        Thông báo
      </div>

      {isOpen && (
        <div 
          ref={popupRef} // Assign ref to the popup
          className="absolute right-0 mt-2 w-72 sm:w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl overflow-hidden border border-gray-200 dark:border-gray-700 origin-top-right animate-fadeIn"
          // Adjusted positioning: top-full for below button, or right-0 for side
        >
          <div className="p-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 flex justify-between items-center">
            <h3 className="font-semibold text-gray-800 dark:text-white">
              Thông báo
            </h3>
            <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <X size={20} />
            </button>
          </div>
          <div className="max-h-80 overflow-y-auto"> {/* Reduced max-h for better fit */}
            {notifications.length > 0 ? (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`p-3 border-b border-gray-100 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer
                    ${
                      !notification.read
                        ? "bg-amber-50 dark:bg-amber-900/20"
                        : ""
                    }`}
                  // onClick={() => handleNotificationClick(notification.id)} // Optional: handle click on individual notification
                >
                  <div className="flex justify-between items-start">
                    <h4 className="font-medium text-sm text-gray-800 dark:text-white">
                      {notification.title}
                    </h4>
                    <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                      {notification.time}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                    {notification.message}
                  </p>
                </div>
              ))
            ) : (
              <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                Không có thông báo mới
              </div>
            )}
          </div>
          <div className="p-2 text-center border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
            <button 
                onClick={markAllAsRead}
                className="text-sm text-blue-500 hover:text-blue-700 dark:hover:text-blue-400 disabled:opacity-50"
                disabled={!hasUnread}
            >
              Đánh dấu đã đọc
            </button>
            <button className="text-sm text-blue-500 hover:text-blue-700 dark:hover:text-blue-400">
              Xem tất cả
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationButton;