// pages/Authentication/Admin.jsx
import React, { useState, useEffect, useCallback } from "react";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Sidebar from "../../components/Sidebar";
import { useAuth, PERMISSIONS, PermissionGate } from "../../contexts/AuthContext"; // Import PERMISSIONS from AuthContext
import { useNavigate } from "react-router-dom";
import Modal from "../../components/Modal";
import NotificationToast from "../../components/NotificationToast";
import { PlusCircle, Trash2, Search, Filter, ChevronDown, ChevronUp, Edit, UserX, UserCheck } from 'lucide-react'; // Icons
import Loading from "../../components/Loading"; // General loading component


// CreateUserModal (cân nhắc nâng cấp dropdown vai trò)
const CreateUserModal = ({ isOpen, onClose, onCreateUser, isLoading, allRolesFromContext }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [roleName, setRoleName] = useState(allRolesFromContext?.[0]?.name || "customer"); // Default to first role or 'customer'
  const [error, setError] = useState("");

  useEffect(() => { // Set default role if roles are loaded
    if (allRolesFromContext && allRolesFromContext.length > 0 && !roleName) {
        setRoleName(allRolesFromContext.find(r => r.name === 'customer')?.id || allRolesFromContext[0].id);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allRolesFromContext]);


  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");
    if (!email || !password || !firstName || !lastName || !roleName) {
      setError("Vui lòng điền đầy đủ các trường bắt buộc và chọn vai trò.");
      return;
    }
    if (password.length < 6 || !/\d/.test(password) || !/[a-zA-Z]/.test(password)) {
      setError("Mật khẩu phải có ít nhất 6 ký tự, bao gồm cả chữ cái và số.");
      return;
    }
    // API POST /users (thông qua createUser trong AuthContext) cần:
    // { email, password, firstName, lastName, role (tên của role, ví dụ "customer") }
    // Hoặc backend có thể chấp nhận roleId nếu bạn dùng danh sách allRolesFromContext.
    // AuthContext.createUser đã được thiết kế để nhận {..., role: "rolename" }
    onCreateUser({ email, password, firstName, lastName, role: roleName });
  };
  
  const handleClose = () => {
      setEmail(""); setPassword(""); setFirstName(""); setLastName("");
      // Không reset roleName để giữ lựa chọn nếu modal mở lại nhanh
      setError("");
      onClose();
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Tạo người dùng mới">
      <form onSubmit={handleSubmit} className="space-y-4 text-sm">
        <div>
          <label className="block font-medium text-gray-700">Email (*)</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 focus:ring-blue-500 focus:border-blue-500" required />
        </div>
        <div>
          <label className="block font-medium text-gray-700">Mật khẩu (*)</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 focus:ring-blue-500 focus:border-blue-500" placeholder="Ít nhất 6 ký tự, có chữ & số" required />
        </div>
        <div className="grid grid-cols-2 gap-4">
            <div>
            <label className="block font-medium text-gray-700">Họ (*)</label>
            <input type="text" value={firstName} onChange={(e) => setFirstName(e.target.value)}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 focus:ring-blue-500 focus:border-blue-500" required />
            </div>
            <div>
            <label className="block font-medium text-gray-700">Tên (*)</label>
            <input type="text" value={lastName} onChange={(e) => setLastName(e.target.value)}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 focus:ring-blue-500 focus:border-blue-500" required />
            </div>
        </div>
        <div>
          <label className="block font-medium text-gray-700">Vai trò (*)</label>
          <select value={roleName} onChange={(e) => setRoleName(e.target.value)}
            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 bg-white focus:ring-blue-500 focus:border-blue-500">
            {/* Backend User Service API POST /users cần role là tên string ('customer', 'admin')
                Hoặc, nếu createUser trong AuthContext có thể xử lý việc gửi roleId nếu backend /users yêu cầu ID.
                Hiện tại AuthContext.createUser gửi `role` là string tên.
            */}
            {(allRolesFromContext && allRolesFromContext.length > 0) ? (
                 allRolesFromContext.map(r => <option key={r.id || r.name} value={r.name}>{r.name.charAt(0).toUpperCase() + r.name.slice(1)}</option>)
            ) : (
                <>
                <option value="customer">Khách hàng (Customer)</option>
                <option value="admin">Quản trị viên (Admin)</option>
                {/* Thêm các role khác nếu cần */}
                <option value="manager">Quản lý (Manager)</option>
                <option value="operator">Vận hành (Operator)</option>
                </>
            )}
          </select>
        </div>
        {error && <p className="text-red-500 text-xs">{error}</p>}
        <div className="flex justify-end space-x-3 pt-2">
          <button type="button" onClick={handleClose} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300">Hủy</button>
          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-60" disabled={isLoading}>
            {isLoading ? "Đang tạo..." : "Tạo người dùng"}
          </button>
        </div>
      </form>
    </Modal>
  );
};


const Admin = () => {
  const { 
    currentUser, // For conditional rendering or checks if needed
    isAdmin, 
    users: usersFromContext, // List of users from AuthContext
    fetchUsers, 
    deleteUser, 
    createUser,
    updateUserProfile, // For activate/deactivate
    loading: authContextLoading, // General loading from AuthContext
    allRoles, // Fetched list of all roles
    loadSystemRolesAndPermissions
  } = useAuth();
  const navigate = useNavigate();

  const [usersForDisplay, setUsersForDisplay] = useState([]);
  const [isLoadingPage, setIsLoadingPage] = useState(true); // Page specific loading
  const [isProcessingAction, setIsProcessingAction] = useState(false); // For create/delete/update actions
  const [notification, setNotification] = useState({ show: false, message: "", type: "success" });
  const [isCreateUserModalOpen, setIsCreateUserModalOpen] = useState(false);
  
  // For filtering and sorting (example)
  // const [searchTerm, setSearchTerm] = useState("");
  // const [filterRole, setFilterRole] = useState("");
  // const [sortConfig, setSortConfig] = useState({ key: 'createdAt', direction: 'descending' });


  const showToast = (message, type = "success") => {
    setNotification({ show: true, message, type, onClose: () => setNotification(p => ({ ...p, show: false })) });
  };
  
  // Initial check and data load
  useEffect(() => {
    if (!authContextLoading && !isAdmin()) {
      showToast("Bạn không có quyền truy cập trang này.", "error");
      navigate("/unauthorized");
    }
  }, [isAdmin, navigate, authContextLoading]);

  const loadInitialData = useCallback(async () => {
    if (isAdmin()) {
      setIsLoadingPage(true);
      await loadSystemRolesAndPermissions(); // Load roles for create modal first
      const result = await fetchUsers(); // Default: page 1, limit 20
      if (result.success) {
        setUsersForDisplay(result.data); // { users: [], pagination: {} }
      } else {
        showToast(result.message || "Tải danh sách người dùng thất bại", "error");
      }
      setIsLoadingPage(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, fetchUsers, loadSystemRolesAndPermissions]); // Dependencies of the memoized function

  useEffect(() => {
    if (!authContextLoading && isAdmin()){ // Ensure AuthContext isn't loading AND user is admin
        loadInitialData();
    }
  }, [authContextLoading, isAdmin, loadInitialData]); // Trigger loadInitialData


  const handleDeleteUser = async (userId, userName) => {
    if (window.confirm(`Bạn có chắc chắn muốn xóa người dùng "${userName}" (ID: ${userId})? Hành động này không thể hoàn tác.`)) {
      setIsProcessingAction(true);
      const result = await deleteUser(userId);
      if (result.success) {
        showToast(result.message || "Xóa người dùng thành công", "success");
        // fetchUsers() is called within deleteUser of AuthContext which updates usersFromContext,
        // or we can re-fetch here to update usersForDisplay based on fresh data.
        const fetchResult = await fetchUsers();
        if(fetchResult.success) setUsersForDisplay(fetchResult.data);
      } else {
        showToast(result.message || "Xóa người dùng thất bại", "error");
      }
      setIsProcessingAction(false);
    }
  };

  const handleCreateUserSubmit = async (userData) => {
    setIsProcessingAction(true);
    const result = await createUser(userData); // userData = { email, password, firstName, lastName, role (name string)}
    if (result.success) {
      showToast(result.message || "Tạo người dùng thành công!", "success");
      setIsCreateUserModalOpen(false);
      const fetchResult = await fetchUsers(); // Refresh list
      if(fetchResult.success) setUsersForDisplay(fetchResult.data);
    } else {
      // Error toast is already handled if createUser sets authError
      // But if it returns a message directly, we can show it.
      showToast(result.message || "Tạo người dùng thất bại. Kiểm tra console để biết chi tiết.", "error");
    }
    setIsProcessingAction(false);
  };

  const handleToggleUserActive = async (userId, currentIsActive) => {
    const action = currentIsActive ? "vô hiệu hóa" : "kích hoạt";
    if (window.confirm(`Bạn có chắc muốn ${action} người dùng ID: ${userId}?`)) {
      setIsProcessingAction(true);
      // API for activate/deactivate are /users/:id/activate and /users/:id/deactivate
      // These are not directly in AuthContext yet, so we make new calls or add to AuthContext.
      // For now, using updateUserProfile to set `isActive` if backend supports it directly via PUT /users/:id.
      // Otherwise, dedicated activate/deactivate functions would be needed in AuthContext using new endpoints.
      // Let's assume for now User Service `PUT /users/:id` can handle `isActive` field.
      const result = await updateUserProfile(userId, { isActive: !currentIsActive });
      
      if (result.success) {
        showToast(`Người dùng đã được ${action}.`, "success");
        const fetchResult = await fetchUsers(); // Refresh list
        if(fetchResult.success) setUsersForDisplay(fetchResult.data);
      } else {
        showToast(`Lỗi khi ${action} người dùng: ${result.message}`, "error");
      }
      setIsProcessingAction(false);
    }
  };


  if (authContextLoading || (!isAdmin() && !authContextLoading)) { // If Auth still loading, or if NOT admin AFTER auth loaded
    return <Loading />; // Show loading while auth status resolves
  }


  return (
    <div className="flex min-h-screen">
      <Sidebar /> {/* Fixed sidebar adjustment in component itself */}
      <div className="flex flex-col w-full md:w-5/6 ml-0 md:ml-64">
        <Header />
         {notification.show && notification.onClose && (
          <NotificationToast message={notification.message} type={notification.type} onClose={notification.onClose} />
        )}
        <main className="flex-grow container mx-auto py-8 px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row justify-between items-center mb-8 gap-3">
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-800">
              Quản lý Người dùng
            </h1>
            {/* Add User Button: Uses PERMISSIONS.USER_CREATE from constants via AuthContext */}
            <PermissionGate permission={PERMISSIONS.USER_CREATE}>
              <button onClick={() => setIsCreateUserModalOpen(true)}
                className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white font-bold py-2.5 px-5 rounded-lg transition duration-200 flex items-center justify-center text-sm shadow-md">
                <PlusCircle className="h-5 w-5 mr-2" />Thêm người dùng
              </button>
            </PermissionGate>
          </div>
          
          {/* TODO: Add Filters and Search UI here if needed */}

          {isLoadingPage ? (
             <div className="text-center py-10"><Loading /></div>
          ) : !usersForDisplay || usersForDisplay.length === 0 ? (
            <div className="text-center text-gray-500 mt-16 p-8 bg-white rounded-lg shadow">
              <Info size={40} className="mx-auto text-gray-400 mb-3"/>
              Không có người dùng nào để hiển thị.
            </div>
          ) : (
            <div className="overflow-x-auto bg-white shadow-xl rounded-lg border border-gray-200">
              <table className="min-w-full text-sm text-left text-gray-700">
                <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-5 py-3 text-center">#</th>
                    <th className="px-5 py-3">Email</th>
                    <th className="px-5 py-3">Họ Tên</th>
                    <th className="px-5 py-3">Vai trò</th>
                    <th className="px-5 py-3 text-center">Trạng thái</th>
                    <th className="px-5 py-3 text-center">Ngày tạo</th>
                    <th className="px-5 py-3 text-center">Hành động</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {usersForDisplay.map((user, index) => (
                    <tr key={user.id} className="hover:bg-gray-50/50 transition-colors">
                      <td className="px-5 py-3 text-center text-gray-500">{index + 1}</td>
                      <td className="px-5 py-3 font-medium text-gray-900 whitespace-nowrap">{user.email}</td>
                      <td className="px-5 py-3 text-gray-700 whitespace-nowrap">{user.firstName} {user.lastName}</td>
                      <td className="px-5 py-3 text-gray-700">
                        {/* API User service /users returns 'roles' as an array of role objects [{id, name, permissions}]
                            or could be array of strings. We need to display role names. */}
                        {(user.roles && Array.isArray(user.roles)) ? 
                            user.roles.map(role => typeof role === 'string' ? role : role.name).join(', ') 
                            : (user.role || 'N/A')} {/* Fallback if structure is simpler user.role */}
                      </td>
                       <td className="px-5 py-3 text-center">
                        <span className={`px-2.5 py-1 text-xs rounded-full font-semibold ${
                            user.isActive ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                        }`}>
                            {user.isActive ? 'Hoạt động' : 'Vô hiệu'}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-gray-500 text-center whitespace-nowrap">
                          {user.createdAt ? new Date(user.createdAt).toLocaleDateString('vi-VN') : 'N/A'}
                      </td>
                      <td className="px-5 py-3 text-center whitespace-nowrap">
                        {/* Update isActive via PUT /users/:id/activate or /deactivate, or directly via PUT /users/:id */}
                        <PermissionGate permission={PERMISSIONS.USER_MANAGE}>
                            <button onClick={() => handleToggleUserActive(user.id, user.isActive)}
                                title={user.isActive ? "Vô hiệu hóa" : "Kích hoạt"}
                                className={`p-1.5 rounded-full hover:bg-opacity-20 transition-colors ${user.isActive ? 'text-yellow-600 hover:bg-yellow-100' : 'text-green-600 hover:bg-green-100'}`}
                                disabled={isProcessingAction || currentUser?.id === user.id /* Admin can't deactivate self */}
                            >
                                {user.isActive ? <UserX size={16} /> : <UserCheck size={16}/>}
                            </button>
                        </PermissionGate>
                        {/* Edit User (redirect to profile page or open a different modal) - Placeholder */}
                        {/* <PermissionGate permission={PERMISSIONS.USER_UPDATE}>
                           <button title="Sửa" className="p-1.5 text-blue-600 hover:bg-blue-100 rounded-full transition-colors ml-1 disabled:opacity-50" disabled={isProcessingAction}><Edit size={16}/></button>
                        </PermissionGate> */}
                        <PermissionGate permission={PERMISSIONS.USER_DELETE}>
                          <button onClick={() => handleDeleteUser(user.id, `${user.firstName} ${user.lastName}`)}
                            title="Xóa"
                            className="p-1.5 text-red-600 hover:bg-red-100 rounded-full transition-colors ml-1 disabled:opacity-50"
                            disabled={isProcessingAction || currentUser?.id === user.id /* Admin can't delete self */}>
                            <Trash2 size={16}/>
                          </button>
                        </PermissionGate>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </main>

        <CreateUserModal
          isOpen={isCreateUserModalOpen}
          onClose={() => setIsCreateUserModalOpen(false)}
          onCreateUser={handleCreateUserSubmit}
          isLoading={isProcessingAction}
          allRolesFromContext={allRoles} // Pass fetched roles
        />
        <Footer />
      </div>
    </div>
  );
};

export default Admin;