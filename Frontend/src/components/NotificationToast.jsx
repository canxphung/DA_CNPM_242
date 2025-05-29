// src/components/NotificationToast.jsx
import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, XCircle, Info } from 'lucide-react'; // Cần cài đặt lucide-react (npm install lucide-react)

const NotificationToast = ({ message, type = 'success', onClose, duration = 3000 }) => {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      if (onClose) onClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const bgColor = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    info: 'bg-blue-500',
  }[type];

  const Icon = {
    success: CheckCircle,
    error: XCircle,
    info: Info,
  }[type];

  if (!isVisible) return null;

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.3 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.5 }}
          className={`fixed bottom-4 right-4 p-4 rounded-md shadow-lg text-white flex items-center z-50 ${bgColor}`}
        >
          {Icon && <Icon className="w-5 h-5 mr-2" />}
          <span>{message}</span>
          <button onClick={() => setIsVisible(false)} className="ml-4 p-1 rounded-full hover:bg-white/20">
            <XCircle className="w-4 h-4" />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default NotificationToast;