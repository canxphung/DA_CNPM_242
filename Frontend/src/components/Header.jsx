import React from "react";
import { FaSignOutAlt } from "react-icons/fa"; // Import biểu tượng đăng xuất từ react-icons
import logo from "../assets/picture/water.png"; // Import logo
import { useAuth } from "../contexts/AuthContext";
const Header = () => {
  const { logout } = useAuth();

  const handleLogout = () => {
    logout(); // Hàm logout trong AuthContext sẽ xử lý việc chuyển hướng
  };

  return (
    <header className="bg-gray-800 text-white py-4">
      <div className="container mx-auto flex justify-between items-center">
        {/* Logo và tên */}
        <div className="flex items-center justify-center flex-grow cursor-pointer">
          <a href="/about">
          <img src={logo} alt="HCMUT Logo" className="h-10 mr-3" />
          </a>
          <div className="text-lg font-bold">
            <a href="/" className="">
              Smart water
            </a>
          </div>
        </div>

        {/* Biểu tượng đăng xuất nằm ở bên phải và cách mép phải */}
        <div className=" mx-3 border-t border-gray-700">
          <button
            onClick={handleLogout}
            className="flex items-center w-full hover:bg-red-500 bg-red-600 px-3 py-2 rounded transition-colors"
          >
            <FaSignOutAlt className="mr-2" />
            <span>Đăng xuất</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
