import React from "react";
import { FaTiktok, FaPhoneAlt } from "react-icons/fa";
import { SiZalo } from "react-icons/si";

// Props for the component
const BubbleIcon = ({ type, href, onClick, size = "md", className = "" }) => {
  // Map icons to types
  const iconMap = {
    tiktok: FaTiktok,
    zalo: SiZalo,
    phone: FaPhoneAlt,
  };

  // Map colors to icon types
  const colorMap = {
    tiktok: "bg-black text-white",
    zalo: "bg-blue-500 text-white",
    phone: "bg-green-500 text-white",
  };

  // Map sizes to classes
  const sizeMap = {
    sm: "w-8 h-8 text-sm",
    md: "w-10 h-10 text-base",
    lg: "w-12 h-12 text-lg",
  };

  const Icon = iconMap[type];
  const colorClass = colorMap[type];
  const sizeClass = sizeMap[size];

  const handleClick = (e) => {
    if (!href && onClick) {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <a
      href={href || "#"}
      target="_blank"
      rel="noopener noreferrer"
      onClick={handleClick}
      className={`rounded-full flex items-center justify-center shadow-md hover:shadow-lg transition-all duration-300 hover:scale-110 ${colorClass} ${sizeClass} ${className}`}
      aria-label={type}
    >
      <Icon className="text-current" />
    </a>
  );
};

export default BubbleIcon;
