// src/pages/Authentication/User.jsx
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Sidebar from "../../components/Sidebar";
import { useAuth, PermissionGate, PERMISSIONS } from "../../contexts/AuthContext"; // PERMISSIONS imported correctly
import NotificationToast from "../../components/NotificationToast";
import Modal from "../../components/Modal";
import api from "../../utils/api";
import { API_ENDPOINTS } from "../../utils/constants"; // Import API_ENDPOINTS
import { Camera, Edit3, KeyRound, Activity, ShieldCheck, Users, LogIn, Mail, Phone, MapPin, CalendarDays } from 'lucide-react';

const ChangePasswordModal = ({ isOpen, onClose, onChangePassword, isLoading }) => {
  // ... (Modal component remains the same)
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");
    if (newPassword !== confirmPassword) {
      setError("Mật khẩu mới và xác nhận mật khẩu không khớp.");
      return;
    }
    if (newPassword.length < 6 || !/\d/.test(newPassword) || !/[a-zA-Z]/.test(newPassword)) {
      setError("Mật khẩu mới phải có ít nhất 6 ký tự, bao gồm chữ cái và số.");
      return;
    }
    onChangePassword(oldPassword, newPassword); // oldPassword should be currentPassword
  };

  useEffect(() => { 
    if (!isOpen) {
        setOldPassword("");
        setNewPassword("");
        setConfirmPassword("");
        setError("");
    }
  }, [isOpen]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Đổi mật khẩu">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Mật khẩu hiện tại</label> {/* Changed from "cũ" */}
          <input
            type="password"
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
            required
            autoComplete="current-password"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Mật khẩu mới</label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
            required
            autoComplete="new-password"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Xác nhận mật khẩu mới</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
            required
            autoComplete="new-password"
          />
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <div className="flex justify-end space-x-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50"
            disabled={isLoading}
          >
            {isLoading ? "Đang đổi..." : "Đổi mật khẩu"}
          </button>
        </div>
      </form>
    </Modal>
  );
};


const User = () => {
  const { 
    currentUser, 
    userPermissions, // This contains strings of permission names
    hasPermission, 
    updateUserProfile, 
    changePassword, 
    loading: authLoading,
    isAdmin // Added isAdmin to potentially show more details for admin viewing own profile
  } = useAuth();
  const navigate = useNavigate();
  
  const [userInfo, setUserInfo] = useState({
    firstName: "", lastName: "", email: "", phone: "", address: "", profileImage: "https://via.placeholder.com/150", birth: ""
  }); 
  
  const [isEditProfileModalOpen, setIsEditProfileModalOpen] = useState(false);
  const [isChangePasswordModalOpen, setIsChangePasswordModalOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [notification, setNotification] = useState({ show: false, message: "", type: "success" });
  console.log('Full currentUser:', currentUser);
  useEffect(() => {
    if (!authLoading && !currentUser) {
      navigate("/login-as");
    } else if (currentUser) {
      setUserInfo({
        firstName: currentUser.firstName || "",
        lastName: currentUser.lastName || "",
        email: currentUser.email || "",
        phone: currentUser.phone || "",
        address: currentUser.address || "",
        profileImage: currentUser.profileImage || "https://via.placeholder.com/150",
        birth: currentUser.birth || "", 
        // Include other relevant fields from currentUser if they exist for the form
        username: currentUser.username || ""
      });
    }
  }, [currentUser, navigate, authLoading]);


  const showToast = (message, type = "success") => {
    setNotification({ show: true, message, type, onClose: () => setNotification(prev => ({...prev, show: false}))});
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setUserInfo(prev => ({ ...prev, [name]: value }));
  };
  
  const handleSaveProfile = async (e) => {
    e.preventDefault();
    if (!currentUser || !currentUser.id) {
      showToast("Không tìm thấy ID người dùng. Không thể cập nhật.", "error");
      return;
    }
    
    setIsProcessing(true);
    // API PUT /users/:id can accept various fields. Send only those managed by this form.
    // Note: Email changes might require re-verification on backend.
    // Username might also be updatable or fixed.
    const payload = {
        firstName: userInfo.firstName,
        lastName: userInfo.lastName,
        email: userInfo.email, 
        phone: userInfo.phone,
        address: userInfo.address,
        birth: userInfo.birth, // Ensure 'birth' is sent in a format backend expects (e.g., ISO string if date)
        username: userInfo.username,
        // profileImage is handled by handleProfileImageChange directly with its own updateUserProfile call
    };

    try {
      const result = await updateUserProfile(currentUser.id, payload);
      if (result.success) {
        showToast("Cập nhật hồ sơ thành công!", "success");
        setIsEditProfileModalOpen(false);
      } else {
        showToast(result.message || "Cập nhật hồ sơ thất bại.", "error");
      }
    } catch (error) {
      showToast(error.message || "Lỗi không xác định khi cập nhật hồ sơ.", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleChangePasswordSubmit = async (currentPassword, newPassword) => { // Renamed oldPassword to currentPassword for clarity
    setIsProcessing(true);
    try {
      // API_ENDPOINTS.USERS.CHANGE_PASSWORD in AuthContext is called, it's a POST, no userId in path
      const result = await changePassword(currentPassword, newPassword);
      if (result.success) {
        showToast("Đổi mật khẩu thành công!", "success");
        setIsChangePasswordModalOpen(false);
      } else {
        showToast(result.message || "Đổi mật khẩu thất bại.", "error");
      }
    } catch (error) {
      showToast(error.message || "Lỗi không xác định khi đổi mật khẩu.", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleProfileImageChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!hasPermission(PERMISSIONS.EDIT_PROFILE)) {
      showToast("Bạn không có quyền thay đổi ảnh đại diện.", "error");
      return;
    }

    setIsProcessing(true);
    const formData = new FormData();
    formData.append("image", file); // Ensure backend key is 'image'

    try {
      // Using the API_ENDPOINTS.UPLOAD.IMAGE which needs to be correctly defined.
      // Assuming API_BASE_URL is correctly prefixed by api.js for uploads too.
      const res = await api.upload(API_ENDPOINTS.UPLOAD.IMAGE, formData); // Use api.upload
      
      // Response from upload: assumed to be { data: { imageUrl: "..." } } or similar
      const newImageUrl = res.data.imageUrl; 

      if (!newImageUrl){
        throw new Error("Không nhận được URL ảnh sau khi tải lên.");
      }

      // Update only the profileImage field
      const result = await updateUserProfile(currentUser.id, { profileImage: newImageUrl });
      if (result.success) {
        // currentUser will be updated via AuthContext's loadUserCompleteData after updateUserProfile,
        // so userInfo useEffect will update. No need for setUserInfo here explicitly IF AuthContext handles it well.
        showToast("Cập nhật ảnh đại diện thành công!", "success");
      } else {
        showToast(result.message || "Lưu ảnh đại diện thất bại.", "error");
      }
    } catch (err) {
      console.error("Upload image error:", err.originalError || err.response?.data || err.message);
      showToast(err.message || "Cập nhật ảnh đại diện thất bại.", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  const getRoleBadgeColor = (rolesArray) => { // Assuming rolesArray comes from currentUser.roles
    if (!rolesArray || rolesArray.length === 0) return "bg-gray-200 text-gray-800";
    // Prioritize admin role for display if user has multiple roles
    if (rolesArray.some(role => (typeof role === 'string' ? role : role.name) === "admin")) {
      return "bg-red-100 text-red-700 border border-red-300";
    }
    if (rolesArray.some(role => (typeof role === 'string' ? role : role.name) === "customer")) {
      return "bg-green-100 text-green-700 border border-green-300";
    }
    // Add more roles (manager, operator)
    if (rolesArray.some(role => (typeof role === 'string' ? role : role.name) === "manager")) {
        return "bg-blue-100 text-blue-700 border border-blue-300";
    }
    if (rolesArray.some(role => (typeof role === 'string' ? role : role.name) === "operator")) {
        return "bg-yellow-100 text-yellow-700 border border-yellow-300";
    }
    return "bg-gray-100 text-gray-700 border border-gray-300";
  };

  const displayFullName = `${userInfo.firstName || ''} ${userInfo.lastName || ''}`.trim();

  if (authLoading || !currentUser) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gray-100">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        <span className="ml-3 text-lg text-gray-700">Đang tải thông tin người dùng...</span>
      </div>
    );
  }
  // Current user roles, ensure it's an array of strings or objects with name
  const currentUserRoles = Array.isArray(currentUser.roles) ? currentUser.roles.map(r => typeof r === 'string' ? r : r.name) : [];

  return (
    <div className="flex min-h-screen bg-gray-100">
      <Sidebar />
      <div className="flex flex-col w-full md:w-5/6 ml-0 md:ml-64">
        <Header />
        {notification.show && notification.onClose && (
          <NotificationToast
            message={notification.message}
            type={notification.type}
            onClose={notification.onClose}
          />
        )}

        <main className="flex-grow container mx-auto py-8 px-4 sm:px-6 lg:px-8">
          <div className="bg-white p-6 rounded-xl shadow-xl mb-8">
            <div className="flex flex-col md:flex-row items-center md:items-start mb-8">
              <div className="relative mb-6 md:mb-0 md:mr-8">
                <img
                  src={userInfo.profileImage || "https://via.placeholder.com/150"}
                  alt="Profile"
                  className="w-32 h-32 rounded-full object-cover border-4 border-blue-500 shadow-md"
                />
                <PermissionGate permission={PERMISSIONS.EDIT_PROFILE}>
                  <label className="absolute bottom-1 right-1 bg-blue-600 text-white p-2.5 rounded-full hover:bg-blue-700 transition cursor-pointer shadow-md">
                    <Camera size={18} />
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleProfileImageChange}
                      className="hidden"
                      disabled={isProcessing}
                    />
                  </label>
                </PermissionGate>
              </div>
              <div className="text-center md:text-left">
                <h1 className="text-3xl font-bold text-gray-800">
                  {displayFullName || currentUser.username || "Chưa có tên"} {/* Fallback to username */}
                </h1>
                <p className="text-gray-600 mt-1">{currentUser.email}</p>
                <div className="mt-2 flex flex-wrap justify-center md:justify-start gap-2">
                    {currentUserRoles.map(roleName => (
                         <span
                            key={roleName}
                            className={`text-xs px-3 py-1 rounded-full font-semibold ${getRoleBadgeColor([roleName])}`}
                         >
                            {roleName ? roleName.charAt(0).toUpperCase() + roleName.slice(1) : "N/A"}
                         </span>
                    ))}
                    {currentUserRoles.length === 0 &&  <span className={`text-xs px-3 py-1 rounded-full font-semibold ${getRoleBadgeColor([])}`}>Chưa có vai trò</span>}
                </div>
              </div>
            </div>
            
            <div className="flex flex-wrap gap-2 mb-6">
                <PermissionGate permission={PERMISSIONS.EDIT_PROFILE}>
                    <button
                    onClick={() => setIsEditProfileModalOpen(true)}
                    className="flex items-center py-2 px-4 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 transition duration-300 shadow"
                    >
                        <Edit3 size={16} className="mr-2"/> Chỉnh sửa hồ sơ
                    </button>
                </PermissionGate>
                 {/* Change Password is a permission of the user themselves */}
                 <button
                    onClick={() => setIsChangePasswordModalOpen(true)}
                    className="flex items-center py-2 px-4 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 transition duration-300 shadow"
                    >
                        <KeyRound size={16} className="mr-2"/> Đổi mật khẩu
                    </button>
            </div>


            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="p-6 border rounded-lg bg-white shadow-md">
                <h2 className="text-xl font-semibold text-gray-800 mb-4 border-b pb-2">Thông tin cá nhân</h2>
                <dl className="space-y-3">
                  {[
                    { label: "Họ", value: userInfo.firstName, icon: User },
                    { label: "Tên", value: userInfo.lastName, icon: User },
                    { label: "Tên đăng nhập", value: userInfo.username, icon: User },
                    { label: "Email", value: currentUser.email, icon: Mail },
                    { label: "SĐT", value: userInfo.phone, icon: Phone },
                    { label: "Địa chỉ", value: userInfo.address, icon: MapPin },
                    { label: "Ngày sinh", value: userInfo.birth ? new Date(userInfo.birth).toLocaleDateString('vi-VN') : "Chưa cập nhật", icon: CalendarDays}
                  ].map(item => (
                    <div key={item.label} className="flex items-start">
                        <dt className="w-1/3 text-sm font-medium text-gray-500 flex items-center shrink-0">
                            <item.icon size={16} className="mr-2 text-gray-400"/>{item.label}
                        </dt>
                        <dd className="w-2/3 text-sm text-gray-900">{item.value || <span className="italic text-gray-400">Chưa cập nhật</span>}</dd>
                    </div>
                  ))}
                </dl>
              </div>

              <div className="p-6 border rounded-lg bg-white shadow-md">
                <h2 className="text-xl font-semibold text-gray-800 mb-4 border-b pb-2">Thông tin hệ thống</h2>
                <dl className="space-y-3">
                    {[
                        { label: "Trạng thái TK", value: currentUser.isActive ? "Đang hoạt động" : "Vô hiệu hóa", icon: ShieldCheck, isStatus: true, statusColor: currentUser.isActive ? "text-green-600" : "text-red-600"},
                        { label: "Ngày tham gia", value: currentUser.createdAt ? new Date(currentUser.createdAt).toLocaleDateString('vi-VN') : "N/A", icon: CalendarDays },
                        { label: "Đăng nhập cuối", value: currentUser.lastLoginAt ? new Date(currentUser.lastLoginAt).toLocaleString('vi-VN') : "N/A", icon: LogIn } // Assuming lastLoginAt from User model
                    ].map(item => (
                        <div key={item.label} className="flex items-start">
                             <dt className="w-1/3 text-sm font-medium text-gray-500 flex items-center shrink-0">
                                <item.icon size={16} className="mr-2 text-gray-400"/>{item.label}
                            </dt>
                            <dd className={`w-2/3 text-sm font-semibold ${item.isStatus ? item.statusColor : 'text-gray-900'}`}>
                                {item.value}
                            </dd>
                        </div>
                    ))}
                    <div>
                        <dt className="text-sm font-medium text-gray-500 mb-1 flex items-center"><Users size={16} className="mr-2 text-gray-400" />Quyền hạn</dt>
                        <dd className="text-sm text-gray-900">
                            {userPermissions.length > 0 ? (
                                <div className="flex flex-wrap gap-1.5">
                                {userPermissions.map((permissionName, index) => (
                                    <span
                                    key={index}
                                    className="px-2.5 py-0.5 bg-blue-100 text-blue-800 text-xs rounded-full border border-blue-300"
                                    >
                                    {permissionName.replace(/[:_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                    </span>
                                ))}
                                </div>
                            ): (
                                <span className="italic text-gray-400">Không có quyền tùy chỉnh.</span>
                            )}
                        </dd>
                    </div>
                </dl>
              </div>
            </div>
            
            {isAdmin() && ( // Only show activity log for admin looking at any profile, or user looking at own if they have VIEW_REPORTS
            <PermissionGate permission={PERMISSIONS.VIEW_REPORTS}>
              <div className="mt-6 p-6 border rounded-lg bg-white shadow-md">
                <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center"><Activity size={20} className="mr-2 text-blue-500" /> Hoạt động gần đây (ví dụ)</h2>
                <ul className="space-y-3 text-sm">
                  {currentUser.lastLoginAt && <li className="flex items-center"><LogIn size={16} className="mr-2 text-gray-400"/> Đăng nhập thành công - {new Date(currentUser.lastLoginAt).toLocaleString('vi-VN')}</li>}
                  {/* Add more specific activity log items if backend provides them for user */}
                  <li className="italic text-gray-500">Tính năng log hoạt động chi tiết đang được phát triển.</li>
                </ul>
              </div>
            </PermissionGate>
            )}
            
            {isAdmin() && currentUser?.id && ( // Only admins can go to the full user management page
            <PermissionGate permission={PERMISSIONS.MANAGE_USERS}>
                 <div className="mt-6 p-6 border rounded-lg bg-white shadow-md">
                    <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center"><Users size={20} className="mr-2 text-purple-500" /> Quản lý Người dùng</h2>
                    <button
                        onClick={() => navigate("/admin")}
                        className="w-full py-2.5 px-4 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition duration-300 flex items-center justify-center shadow"
                    >
                        Đi đến trang quản lý tất cả người dùng
                    </button>
                 </div>
            </PermissionGate>
            )}

          </div>

          <Modal isOpen={isEditProfileModalOpen} onClose={() => setIsEditProfileModalOpen(false)} title="Chỉnh sửa hồ sơ">
            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Họ</label>
                  <input name="firstName" value={userInfo.firstName} onChange={handleFormChange} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tên</label>
                  <input name="lastName" value={userInfo.lastName} onChange={handleFormChange} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" />
                </div>
                 <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tên đăng nhập</label>
                  <input name="username" value={userInfo.username} onChange={handleFormChange} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" />
                </div>
                 <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Ngày sinh</label>
                  <input name="birth" type="date" value={userInfo.birth ? userInfo.birth.split('T')[0] : ''} onChange={handleFormChange} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input name="email" type="email" value={userInfo.email} onChange={handleFormChange} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Số điện thoại</label>
                <input name="phone" value={userInfo.phone} onChange={handleFormChange} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Địa chỉ</label>
                <input name="address" value={userInfo.address} onChange={handleFormChange} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setIsEditProfileModalOpen(false)} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors">Hủy</button>
                <button type="submit" disabled={isProcessing} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50">
                  {isProcessing ? "Đang lưu..." : "Lưu thay đổi"}
                </button>
              </div>
            </form>
          </Modal>

          <ChangePasswordModal
            isOpen={isChangePasswordModalOpen}
            onClose={() => setIsChangePasswordModalOpen(false)}
            onChangePassword={handleChangePasswordSubmit}
            isLoading={isProcessing}
          />
        </main>
        <Footer />
      </div>
    </div>
  );
};

export default User;