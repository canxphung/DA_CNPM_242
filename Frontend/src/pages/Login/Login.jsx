// Login.jsx
import React, { useState, useEffect } from "react";
import { useNavigate, useParams, Link, useLocation } from "react-router-dom";
import { AiFillEye, AiFillEyeInvisible } from "react-icons/ai";
import avatar from "../../assets/picture/water.png"; // Make sure path is correct
import { useAuth } from "../../contexts/AuthContext";
import NotificationToast from "../../components/NotificationToast";

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState({ show: false, message: "", type: "success" });

  const { login, authError, setAuthError } = useAuth();

  const { userType } = useParams(); // 'customer' hoặc 'admin'
  const location = useLocation();
  // logType from state is fine if navigating internally with state.
  // userType from params is fallback or direct URL access.
  const logType = location.state?.logType || userType || "customer"; // Default to customer if no type
  
  const navigate = useNavigate();

  useEffect(() => {
    setAuthError(""); 
  }, [setAuthError]);

  useEffect(() => {
    if (authError) {
      // Notification is now managed locally within the component for display
      setNotification({ 
          show: true, 
          message: authError, 
          type: "error", 
          onClose: () => setNotification(prev => ({...prev, show: false})) 
      });
    }
  }, [authError]);

  useEffect(() => {
    if (!userType && !location.state?.logType) { 
      navigate("/login-as"); 
    }
  }, [userType, location.state?.logType, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setAuthError(""); 

    // login function in AuthContext now returns {success, message}
    const result = await login(email, password, logType); 
    
    setIsLoading(false); // Set loading false regardless of outcome AFTER await
    
    if (!result.success) {
      // Error already set in AuthContext's authError, which triggers the useEffect above
      // No need to call setNotification here if useEffect [authError] handles it.
      // If you want immediate feedback before authError state update trickles down:
      // setNotification({ show: true, message: result.message || "Đăng nhập thất bại.", type: "error", onClose: () => setNotification(prev => ({...prev, show: false})) });
    }
    // Navigation is handled by AuthContext after successful login
  };

  return (
    <div className="flex min-h-screen w-full overflow-hidden">
      <div className="hidden md:flex w-2/5 bg-white flex-col justify-center  px-16 items-center">
        <div className="flex flex-col gap-2 justify-center items-center">
          <img src={avatar} alt="logo" className="w-20 " />
          <div className="text-3xl font-bold flex items-center gap-1">
            <span className="text-[#2AF598]">Smart</span>
            <span className="text-[#08AEEA]">Water</span>
          </div>
        </div>
        <div className="mt-20 flex flex-col items-center justify-between">
          <h1 className="text-5xl font-bold text-[#2AF598] leading-tight ">
            Chào Mừng!
          </h1>
          <p className="mt-6 text-lg text-gray-600 max-w-md">
            Đăng nhập để truy cập tài khoản của bạn và khám phá các tính năng
            mới nhất của chúng tôi.
          </p>
        </div>
      </div>

      <div className="flex-1 bg-gradient-to-br from-[#2AF598] to-[#08AEEA] flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-2xl px-8 md:px-16 py-10 w-[90%] max-w-md border border-black"> {/* Consider removing border-black or making it softer gray */}
          <div className="mb-6 text-center">
            <h2 className="text-4xl font-bold text-[#52ACFF]">Đăng nhập</h2>
            <p className="text-lg text-gray-600 mt-2">
              {logType === "admin" ? "Quản trị viên" : "Khách hàng"}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="text-sm text-gray-600">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Nhập email của bạn"
                className="w-full mt-1 px-4 py-3 rounded-md bg-gray-100 border-b-2 border-green-700 focus:outline-none focus:ring-2 focus:ring-green-400 transition"
                required
                autoComplete="email"
              />
            </div>

            <div className="relative">
              <label htmlFor="password" className="text-sm text-gray-600">Mật khẩu</label>
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Nhập mật khẩu của bạn"
                className="w-full mt-1 px-4 py-3 rounded-md bg-gray-100 border-b-2 border-green-700 focus:outline-none focus:ring-2 focus:ring-green-400 transition"
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                tabIndex={-1} // Make it not focusable with Tab
                className="absolute right-4 top-1/2 transform -translate-y-1/4 cursor-pointer text-gray-500 hover:text-gray-700" // Adjusted top positioning
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
              >
                {showPassword ? (
                  <AiFillEye size={22} />
                ) : (
                  <AiFillEyeInvisible size={22} />
                )}
              </button>
            </div>

            <button
              type="submit"
              className={`w-full py-3 bg-[#0D986A] hover:bg-[#0B8459] text-white rounded-full font-semibold text-lg shadow-lg 
                         transition-all duration-300 flex items-center justify-center
                         ${isLoading ? "opacity-70 cursor-not-allowed" : ""}`}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-r-2 border-white mr-2"></div>
                  Đang đăng nhập...
                </>
              ) : (
                "Đăng nhập"
              )}
            </button>
          </form>

          <div className="mt-8 text-center text-sm text-gray-600">
            <span className="mr-1">Chưa có tài khoản?</span>
            <Link
              to="/register"
              className="text-green-700 hover:underline font-medium"
            >
              Yêu cầu đăng ký tài khoản!
            </Link>
          </div>

          <div className="mt-4 text-center">
            <Link
              to="/login-as"
              className="text-blue-500 hover:underline text-sm"
            >
              Quay lại trang chọn vai trò
            </Link>
          </div>
        </div>
      </div>
      {notification.show && notification.onClose && ( // Ensure onClose is passed to toast
        <NotificationToast
          message={notification.message}
          type={notification.type}
          onClose={notification.onClose} 
        />
      )}
    </div>
  );
};

export default Login;