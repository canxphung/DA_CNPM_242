// src/pages/SignUp/SignUp.jsx
import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import avatar from "../../assets/picture/water.png"; // Make sure path is correct
import { useAuth } from "../../contexts/AuthContext";
import NotificationToast from "../../components/NotificationToast";
import { Eye, EyeOff, CheckCircle, Zap as ZapIcon } from 'lucide-react'; // Using ZapIcon to avoid conflict with local Zap

const SignUp = () => {
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    birth: "", // Will NOT be sent to /auth/register by default in AuthContext
    address: "", // Will NOT be sent
    email: "",
    phone: "", // Will NOT be sent
    username: "", // Will NOT be sent by default, can be derived from email if API /users allows username.
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState({ show: false, message: "", type: "success" });

  const { register, authError, setAuthError, updateUserProfile, currentUser } = useAuth(); // Added updateUserProfile and currentUser
  const navigate = useNavigate();

  useEffect(() => {
    setAuthError("");
  }, [setAuthError]);

  const showToast = (message, type = "info") => {
    setNotification({ show: true, message, type, onClose: () => setNotification(prev => ({...prev, show: false}))});
  };
  
  // Show toast when authError changes
  useEffect(() => {
    if (authError) {
        showToast(authError, "error");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authError]);


  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const validateForm = () => {
    const { firstName, lastName, email, password, phone, birth, address, username } = formData;
    if (!firstName || !lastName || !email || !password || !username ) { // Username is required in form but may not be in initial register API call
      showToast("Vui lòng điền các trường Họ, Tên, Email, Tên đăng nhập và Mật khẩu.", "error");
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showToast("Địa chỉ email không hợp lệ.", "error");
      return false;
    }
    // Password check: ít nhất 6 ký tự, bao gồm chữ và số.
    if (password.length < 6 || !/\d/.test(password) || !/[a-zA-Z]/.test(password)) {
      showToast("Mật khẩu phải có ít nhất 6 ký tự, bao gồm cả chữ cái và số.", "error");
      return false;
    }
    if (phone && !/^[0-9]{10,11}$/.test(phone)) { // Phone is optional on form submit but validated if provided
        showToast("Số điện thoại không hợp lệ (10-11 chữ số).", "error");
        return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAuthError(""); 

    if (!validateForm()) return;

    setIsLoading(true);
    try {
      // AuthContext's register function expects { firstName, lastName, email, password, ...otherFields }
      // It will internally pick only the required fields for the /auth/register API call.
      const registrationPayload = {
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email,
        password: formData.password,
        // username: formData.username, // User Service API POST /auth/register does not list username
      };
      const result = await register(registrationPayload); 

      if (result.success) {
        showToast(result.message || "Đăng ký thành công! Vui lòng kiểm tra email (nếu có) và đăng nhập.", "success");
        
        // Backend might auto-login. If not, or if we need to update additional info:
        // To update other info (phone, address, birth, username if not sent) AFTER registration
        // we would need the user to be logged in, or the `register` function in AuthContext to handle it.
        // For now, just redirecting to login page after success message.
        
        setTimeout(() => {
          navigate("/login/customer"); // Or /login-as if you want them to choose again
        }, 3000);

      } else {
        // showToast is handled by useEffect [authError]
      }
    } catch (error) {
      console.error("Lỗi đăng ký không mong muốn:", error);
      showToast("Đăng ký thất bại do lỗi hệ thống. Vui lòng thử lại sau.", "error");
    } finally {
      setIsLoading(false);
    }
  };


  const inputFields = [
    { name: "firstName", label: "Họ (*)", placeholder: "Nguyễn", type: "text", halfWidth: true },
    { name: "lastName", label: "Tên (*)", placeholder: "Văn A", type: "text", halfWidth: true },
    { name: "username", label: "Tên đăng nhập (*)", placeholder: "nguyenvana123", type: "text", halfWidth: true},
    { name: "birth", label: "Ngày sinh", type: "date", halfWidth: true }, // Optional for initial registration
    { name: "email", label: "Email (*)", placeholder: "example@email.com", type: "email" }, // No longer halfWidth
    { name: "phone", label: "Số điện thoại", placeholder: "0912345678", type: "tel" }, // Optional
    { name: "address", label: "Địa chỉ", placeholder: "Số nhà, đường, phường/xã...", type: "text", className:"sm:col-span-2" }, // Optional
    { 
      name: "password", 
      label: "Mật khẩu (*)", 
      placeholder: "Ít nhất 6 ký tự, có chữ và số", 
      type: showPassword ? "text" : "password", 
      icon: showPassword ? <EyeOff size={18}/> : <Eye size={18}/>, 
      onIconClick: () => setShowPassword(!showPassword),
      className:"sm:col-span-2" // Make password full width for better layout
    },
  ];

  return (
    <div className="flex flex-col md:flex-row min-h-screen w-screen overflow-x-hidden">
      <div className="hidden md:flex md:w-2/5 bg-gradient-to-br from-[#2AF598] to-[#08AEEA] relative p-12 flex-col justify-center">
        <div>
            <div className="flex items-center mb-4">
                <img src={avatar} alt="SmartWater Logo" className="w-10 h-10 mr-2"/>
                <span className="text-3xl font-bold">
                    <span className="text-yellow-300">Smart</span>
                    <span className="text-white">Water</span>
                </span>
            </div>
            <h1 className="text-4xl lg:text-5xl font-bold text-white mb-6 leading-tight">
                Tham gia cùng Chúng tôi
            </h1>
            <p className="text-white/90 text-lg lg:text-xl max-w-md">
                Đăng ký để quản lý hệ thống tưới tiêu thông minh, theo dõi và tối ưu hóa việc sử dụng nước cho nông trại của bạn.
            </p>
        </div>
        <div className="mt-10 space-y-4">
            <div className="flex items-start p-4 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20">
                <CheckCircle className="w-10 h-10 text-yellow-300 mr-3 mt-1 flex-shrink-0" />
                <div>
                    <h3 className="text-white font-semibold">Quản lý Hiệu quả</h3>
                    <p className="text-white/80 text-sm">Dễ dàng theo dõi và điều khiển thiết bị từ xa.</p>
                </div>
            </div>
             <div className="flex items-start p-4 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20">
                <ZapIcon className="w-10 h-10 text-yellow-300 mr-3 mt-1 flex-shrink-0" />
                <div>
                    <h3 className="text-white font-semibold">Công nghệ AI</h3>
                    <p className="text-white/80 text-sm">Nhận khuyến nghị thông minh để tối ưu hóa năng suất.</p>
                </div>
            </div>
        </div>
      </div>

      <div className="w-full md:w-3/5 bg-white flex items-center justify-center py-8 px-4 sm:px-8 lg:px-12">
        <div className="w-full max-w-xl"> {/* Increased max-width for better form layout */}
          <div className="md:hidden flex flex-col items-center mb-8">
            <img src={avatar} className="w-16 h-16 mb-2" alt="logo" />
            <div className="flex font-sans font-bold text-2xl">
              <p className="text-[#2AF598]">Smart</p><p className="text-[#08AEEA]">Water</p>
            </div>
          </div>

          <h2 className="text-3xl md:text-4xl font-bold text-gray-800 mb-2 text-center md:text-left">
            Đăng ký Tài khoản
          </h2>
          <p className="text-gray-500 mb-8 text-center md:text-left">Vui lòng điền thông tin để tạo tài khoản mới. Các trường (*) là bắt buộc.</p>

          <form onSubmit={handleSubmit} className="space-y-3"> {/* Reduced general space-y for tighter form */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3"> {/* Reduced gap-y */}
                {inputFields.map(field => (
                    <div key={field.name} className={`${field.halfWidth ? "" : "sm:col-span-2"} ${field.className || ''}`}>
                        <label htmlFor={field.name} className="block text-sm font-medium text-gray-700 mb-1">
                        {field.label}
                        </label>
                        <div className="relative">
                        <input
                            type={field.type}
                            name={field.name}
                            id={field.name}
                            value={formData[field.name]}
                            onChange={handleChange}
                            placeholder={field.placeholder}
                            className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-sm
                                        focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
                            required={field.label.includes("(*)")} // Mark required based on label
                            autoComplete={field.name === "email" ? "email" : field.name === "password" ? "new-password" : "off"}
                        />
                        {field.icon && (
                            <button type="button" tabIndex={-1} onClick={field.onIconClick} className="absolute inset-y-0 right-0 px-3 flex items-center text-gray-500 hover:text-blue-600">
                                {field.icon}
                            </button>
                        )}
                        </div>
                    </div>
                ))}
            </div>
            
            {/* Notification moved out of form structure to be more globally visible or handled by global toast system */}

            <div className="pt-3 space-y-3"> {/* Increased pt */}
              <button
                type="submit"
                className={`w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold text-base 
                           shadow-md hover:shadow-lg transition-all duration-300 flex items-center justify-center
                           disabled:opacity-70 disabled:cursor-not-allowed`}
                disabled={isLoading}
              >
                {isLoading ? (
                    <>
                        <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-r-2 border-white mr-2"></div>
                        Đang xử lý...
                    </>
                ) : "Đăng ký"}
              </button>
              <button
                type="button"
                className="w-full py-2.5 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg font-semibold text-base 
                           transition-all duration-300"
                onClick={() => navigate("/login-as")}
              >
                Hủy
              </button>
            </div>
          </form>

          <p className="mt-6 text-center text-sm text-gray-600"> {/* Reduced mt */}
            Đã có tài khoản?{" "}
            <Link to="/login-as" className="font-medium text-blue-600 hover:text-blue-700 hover:underline">
              Đăng nhập ngay
            </Link>
          </p>
        </div>
      </div>
      {notification.show && notification.onClose && (
        <NotificationToast
            message={notification.message}
            type={notification.type}
            onClose={notification.onClose}
        />
      )}
    </div>
  );
};

// Re-add dummy icons if not using Lucide properly yet
// const CheckCircle = ({ className }) => <svg className={className} fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"></path></svg>;
// const ZapIcon = ({ className }) => <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>;

export default SignUp;