// src/components/NotificationToast.jsx
import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Info, X } from 'lucide-react';

const NotificationToast = ({ message, type = 'info', onClose, duration = 3000 }) => {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        handleClose();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [duration]);

  const handleClose = () => {
    setIsVisible(false);
    if (onClose) {
      setTimeout(onClose, 300); // Wait for fade out animation
    }
  };

  if (!isVisible) return null;

  const styles = {
    success: {
      bgColor: 'bg-green-500',
      icon: CheckCircle,
      borderColor: 'border-green-600'
    },
    error: {
      bgColor: 'bg-red-500', 
      icon: XCircle,
      borderColor: 'border-red-600'
    },
    info: {
      bgColor: 'bg-blue-500',
      icon: Info,
      borderColor: 'border-blue-600'
    }
  };

  const currentStyle = styles[type] || styles.info;
  const Icon = currentStyle.icon;

  return (
    <div
      className={`fixed bottom-4 right-4 p-4 rounded-lg shadow-lg text-white flex items-center z-50 
                  transition-all duration-300 transform
                  ${currentStyle.bgColor} ${currentStyle.borderColor} border
                  ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}`}
      style={{ minWidth: '250px', maxWidth: '400px' }}
    >
      <Icon className="w-5 h-5 mr-3 flex-shrink-0" />
      <span className="flex-1 text-sm">{message}</span>
      <button
        onClick={handleClose}
        className="ml-3 p-1 rounded-full hover:bg-white/20 transition-colors"
        aria-label="Close notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

export default NotificationToast;