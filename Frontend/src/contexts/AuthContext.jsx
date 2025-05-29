// contexts/AuthContext.jsx
import React, { createContext, useState, useEffect, useContext } from "react";
import { useNavigate } from "react-router-dom";
import api from "../utils/api"; // Sử dụng instance đã được cấu hình
import { API_ENDPOINTS, STORAGE_KEYS, ERROR_MESSAGES, PERMISSIONS as APP_PERMISSIONS, HTTP_STATUS } from "../utils/constants"; // Đổi tên PERMISSIONS để tránh nhầm lẫn

export const AuthContext = createContext();

// PERMISSIONS constant - should be THE authoritative source
// If your backend actually sends down different permission strings,
// this APP_PERMISSIONS object should be mapped or generated from those.
// For now, using what you defined.
export const PERMISSIONS = APP_PERMISSIONS;


export const DEFAULT_ROLES = {
  ADMIN: "admin",
  CUSTOMER: "customer",
  MANAGER: "manager",
  OPERATOR: "operator",
};

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [userPermissions, setUserPermissions] = useState([]);
  const [userRoles, setUserRoles] = useState([]); // Assuming roles are strings like 'admin', 'customer' or objects like {id, name, permissions}
  const [allRoles, setAllRoles] = useState([]); // For admin interface to assign roles
  const [allPermissions, setAllPermissions] = useState([]); // For admin interface to assign permissions
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    const handleAuthFailure = (event) => {
      console.log('Auth failure detected in AuthContext:', event.detail);
      setAuthError(event.detail.message || ERROR_MESSAGES.UNAUTHORIZED);
      clearAuthDataAndRedirect();
    };

    window.addEventListener('authFailure', handleAuthFailure);
    return () => window.removeEventListener('authFailure', handleAuthFailure);
  }, [navigate]); // Added navigate to dependency array as clearAuthDataAndRedirect uses it.

  useEffect(() => {
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    if (token) {
      checkLoggedInUser();
    } else {
      setLoading(false);
    }
  }, []);

  const clearAuthDataAndRedirect = () => {
    api.clearAuthData();
    setCurrentUser(null);
    setUserPermissions([]);
    setUserRoles([]);
    setUsers([]); // Clear users list as well
    // No loading change here as it might cause flashes; let navigate handle UI change.
    navigate("/login-as");
  };

  const clearAuthDataOnly = () => {
    api.clearAuthData();
    setCurrentUser(null);
    setUserPermissions([]);
    setUserRoles([]);
  };

  const loadUserCompleteData = async (baseUserData) => {
    if (!baseUserData || !baseUserData.id) {
      console.error("Cannot load complete data without base user ID.");
      clearAuthDataAndRedirect(); // Critical data missing
      return;
    }
    try {
      // Use API_ENDPOINTS.USERS.ME if your backend provides full user details (including roles/permissions) here
      // Or, if /auth/me already provided sufficient role/permission info, use that.
      // The current structure implies /auth/me gives basic user, then /users/:id gives details.
      const userDetailResponse = await api.get(API_ENDPOINTS.USERS.BY_ID(baseUserData.id));
      console.log("userDetailResponse", userDetailResponse);
      const completeUserData = userDetailResponse.data; // Assuming response.data IS the user object
      console.log("completeUserData", completeUserData);
      if (completeUserData && (userDetailResponse.data.id || userDetailResponse.data._id)) {
        setCurrentUser(completeUserData);
        
        // Permissions can be an array of strings or objects {id, name, resource, action}
        // Roles can be an array of strings or objects {id, name, permissions: [...]}
        const permissions = completeUserData.customPermissions || []; // Or completeUserData.permissions from role
        const roles = completeUserData.roles || []; // Expecting this to be array of role objects/strings
        
        setUserPermissions(permissions.map(p => (typeof p === 'string' ? p : p.name)));
        setUserRoles(roles.map(r => (typeof r === 'string' ? r : r.name)));

        localStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(completeUserData));
        localStorage.setItem(STORAGE_KEYS.PERMISSIONS, JSON.stringify(permissions.map(p => (typeof p === 'string' ? p : p.name))));
        // Storing roles might also be useful if needed for UI directly
        localStorage.setItem(STORAGE_KEYS.USER_ROLES, JSON.stringify(roles.map(r => (typeof r === 'string' ? r : r.name))));


      } else {
          throw new Error("Invalid complete user data from server");
      }

    } catch (error) {
      console.error("Error loading complete user data:", error.message, error.originalError);
      // Fallback to basic data if detailed loading fails, but this might leave user in inconsistent state
      // Better to log out if essential data like permissions can't be loaded.
      setAuthError(error.message || "Lỗi tải thông tin người dùng chi tiết.");
      clearAuthDataAndRedirect();
    }
  };

  const checkLoggedInUser = async () => {
    setLoading(true);
    setAuthError("");
    try {
      const response = await api.get(API_ENDPOINTS.AUTH.ME);
      const userDataFromAuthMe = response.data; // Expects { id, email, role, possibly basic permissions }

      if (userDataFromAuthMe && userDataFromAuthMe.id) {
        // Now, fetch more complete user details if needed, or directly use userDataFromAuthMe
        // Your loadUserCompleteData implies /auth/me gives base, then /users/:id gives full.
        await loadUserCompleteData(userDataFromAuthMe); 
      } else {
        throw new Error("Invalid user data from /auth/me");
      }
    } catch (error) {
      console.error("Error checking logged in user:", error.message, error.originalError);
      setAuthError(error.message || ERROR_MESSAGES.UNAUTHORIZED);
      clearAuthDataAndRedirect(); // Redirect to login if 'me' fails
    } finally {
      setLoading(false);
    }
  };


  const login = async (email, password, type = "customer") => { // 'type' param might be deprecated if not used by backend
    setLoading(true);
    setAuthError("");
    try {
      const response = await api.post(API_ENDPOINTS.AUTH.LOGIN, { email, password });
      // API Doc expects: { user: { id, email, role,... }, accessToken, refreshToken }
      const { user, tokens } = response.data;
      console.log("Login response:", response.data);
      if (tokens.accessToken && user && user.id) {
        api.setTokens(tokens.accessToken, tokens.refreshToken);
        await loadUserCompleteData(user); // Load full user details after login

        // Navigation logic (already present, seems fine)
        const userRolesArray = Array.isArray(user.roles) ? user.roles : (user.role ? [user.role] : []);
        if (userRolesArray.some(role => (typeof role === 'string' ? role : role.name) === DEFAULT_ROLES.ADMIN)) {
            navigate("/admin");
        } else {
            navigate("/");
        }
        return { success: true, message: "Đăng nhập thành công!" };
      } else {
        throw new Error("Dữ liệu đăng nhập không hợp lệ từ server.");
      }
    } catch (error) {
      console.error("Login failed:", error.message, error.originalError);
      const errorMessage = error.message || ERROR_MESSAGES.SERVER_ERROR;
      setAuthError(errorMessage);
      clearAuthDataOnly(); // Clear tokens but don't redirect immediately, let UI show error
      return { success: false, message: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  const register = async (userData) => {
    setLoading(true);
    setAuthError("");
    try {
      // User Service API POST /auth/register expects: email, password, firstName, lastName
      const { firstName, lastName, email, password } = userData;
      const payload = { email, password, firstName, lastName };

      // Other fields like phone, address, birth, username would be updated via PUT /users/me or PUT /users/:id AFTER registration & login
      // For now, this context function only handles the registration call.

      const response = await api.post(API_ENDPOINTS.AUTH.REGISTER, payload);
      
      // API Doc: Output { message, user (created), accessToken, refreshToken }
      const { accessToken, refreshToken, user } = response.data;

      if (accessToken && user && user.id) { // If backend auto-logs in
        api.setTokens(accessToken, refreshToken);
        await loadUserCompleteData(user);
        // Potentially navigate here, or let SignUp page handle success (e.g., show success message then redirect to login)
      }
      // Even if not auto-login, registration might be successful
      return { success: true, message: response.data.message || "Đăng ký thành công!" };

    } catch (error) {
      console.error("Registration failed:", error.message, error.originalError);
      const errorMessage = error.message || ERROR_MESSAGES.SERVER_ERROR;
      setAuthError(errorMessage);
      return { success: false, message: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  const logout = async (allDevices = false) => { // 'allDevices' seems to correspond to /auth/logout-all
    setLoading(true);
    try {
      const refreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
      if (refreshToken) {
        const endpoint = allDevices ? API_ENDPOINTS.AUTH.LOGOUT_ALL : API_ENDPOINTS.AUTH.LOGOUT;
        // LOGOUT_ALL POST expects no body but uses the token. LOGOUT POST expects { refreshToken }.
        // This needs to be consistent. Assuming LOGOUT takes refreshToken in body, LOGOUT_ALL takes nothing.
        if (allDevices) {
             await api.post(endpoint);
        } else {
             await api.post(endpoint, { refreshToken });
        }
      }
    } catch (error) {
      console.error("Logout API call failed:", error.message, error.originalError);
      // Still proceed with local logout
    } finally {
      clearAuthDataAndRedirect();
      setLoading(false); // Ensure loading is set to false
    }
  };

  const hasPermission = (permissionName) => {
    if (loading || !Array.isArray(userPermissions)) return false;
    // Assuming userPermissions is an array of permission strings like "user:read", "device:control"
    // And userRoles is an array of role objects, each potentially having a 'permissions' array.
    
    const hasDirectPermission = userPermissions.includes(permissionName);
    if (hasDirectPermission) return true;

    // Check permissions from roles
    // This part assumes userRoles is an array of role *objects* like: [{ name: 'admin', permissions: ['user:manage', ...] }]
    // If userRoles is just an array of role *names*, this check needs adjustment or more data fetching for role details.
    // Given loadUserCompleteData fetches /users/:id, 'roles' field in 'completeUserData' should be rich.
    if (Array.isArray(userRoles)) {
        for (const role of userRoles) {
            if (typeof role === 'object' && role !== null && Array.isArray(role.permissions)) {
                if (role.permissions.some(p => (typeof p === 'string' ? p === permissionName : p.name === permissionName))) {
                    return true;
                }
            }
            // If role is a string, we can't check its permissions here without fetching role details
        }
    }
    return false;
  };
  
  const hasRole = (roleNameToCheck) => {
    if (loading || !Array.isArray(userRoles)) return false;
    return userRoles.some(role => (typeof role === 'string' ? role === roleNameToCheck : role.name === roleNameToCheck));
  };

  const isAdmin = () => {
    return hasRole(DEFAULT_ROLES.ADMIN) || hasPermission(PERMISSIONS.ADMIN_ACCESS);
  };

  const fetchUsers = async (filters = {}) => {
    setLoading(true); // Or a specific loading state for user fetching
    try {
      // Permission check should ideally be here or in Admin.jsx before calling
      // if (!hasPermission(PERMISSIONS.READ_USER)) { // Using specific READ_USER permission
      //   setAuthError("Không có quyền xem danh sách người dùng");
      //   return { success: false, message: "Không có quyền xem danh sách người dùng", data: [] };
      // }
      
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== '' && value !== null) {
          params.append(key, value);
        }
      });

      // API_ENDPOINTS.USERS.BASE should be just "/users" (without prefix, api.userService will add it)
      const response = await api.get(`${API_ENDPOINTS.USERS.BASE}${params.toString() ? `?${params.toString()}` : ''}`);
      // API DOC User Service GET /api/v1/users: returns { users: [], total, page, limit }
      const usersData = response.data.users || response.data || []; // Handle if response structure is just an array
      const totalUsers = response.data.total || usersData.length;
      
      setUsers(usersData); // Update local state for components like Admin.jsx
      
      return { success: true, data: usersData, total: totalUsers };
    } catch (error) {
      console.error("Error fetching users:", error.message, error.originalError);
      setAuthError(error.message || "Lỗi tải danh sách người dùng.");
      return { success: false, message: error.message || "Lỗi tải danh sách người dùng.", data: [] };
    } finally {
      setLoading(false);
    }
  };
  
  const createUser = async (userData) => {
    // Admin.jsx CreateUserModal passes: { email, password, firstName, lastName, role }
    // API POST /api/v1/users expects: email, password, firstName, lastName, role (optional, default 'customer')
    setLoading(true);
    try {
      // if (!hasPermission(PERMISSIONS.CREATE_USER)) { ... }
      const response = await api.post(API_ENDPOINTS.USERS.BASE, userData);
      // API DOC User Service: returns created user object
      const newUser = response.data;
      setUsers(prevUsers => [...prevUsers, newUser]); // Update local cache
      return { success: true, message: "Tạo người dùng thành công", user: newUser };
    } catch (error) {
      console.error("Error creating user:", error.message, error.originalError);
      const message = error.message || "Lỗi tạo người dùng.";
      setAuthError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };
  
  const updateUserProfile = async (userId, updatedData) => {
    // User.jsx calls this with currentUser.id and payload: { firstName, lastName, email, phone, address }
    // Also for profileImage update: { profileImage: newImageUrl }
    // API PUT /api/v1/users/:id can update these fields.
    // Ensure that 'email' update is handled carefully by backend (e.g., re-verification)
    // Permission check: user:update for admins, or profile:update if it's the user's own profile.
    
    setLoading(true);
    try {
        const canUpdate = hasPermission(PERMISSIONS.UPDATE_USER) || 
                          (currentUser && currentUser.id === userId && hasPermission(PERMISSIONS.EDIT_PROFILE));
      
        if (!canUpdate) {
            setAuthError("Không có quyền cập nhật thông tin người dùng này.");
            return { success: false, message: "Không có quyền cập nhật thông tin người dùng này." };
        }

      const response = await api.put(API_ENDPOINTS.USERS.BY_ID(userId), updatedData);
      // API Doc User Service: returns updated user object
      const updatedUserFromServer = response.data;
      
      if (currentUser && currentUser.id === userId) {
        // If updating own profile, we need to re-process roles/permissions
        // loadUserCompleteData does this and sets currentUser
        await loadUserCompleteData(updatedUserFromServer); 
      }
      
      setUsers(prevUsers => 
        prevUsers.map(user => (user.id === userId ? updatedUserFromServer : user))
      );
      
      return { success: true, message: "Cập nhật thông tin thành công", user: updatedUserFromServer };
    } catch (error) {
      console.error("Error updating user profile:", error.message, error.originalError);
      const message = error.message || "Lỗi cập nhật thông tin.";
      setAuthError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  const changePassword = async (currentPassword, newPassword) => { // userId is implicit (current user)
    // API POST /api/v1/users/change-password expects: { currentPassword, newPassword }
    setLoading(true);
    try {
      // No userId needed as API works on the authenticated user
      const response = await api.post(API_ENDPOINTS.USERS.CHANGE_PASSWORD, { currentPassword, newPassword });
      // API Doc User Service: returns success message
      return { success: true, message: response.data.message || "Thay đổi mật khẩu thành công" };
    } catch (error) {
      console.error("Error changing password:", error.message, error.originalError);
      const message = error.message || "Lỗi đổi mật khẩu.";
      setAuthError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };
  
  const deleteUser = async (userId) => {
    setLoading(true);
    try {
      // if (!hasPermission(PERMISSIONS.DELETE_USER)) { ... }
      await api.delete(API_ENDPOINTS.USERS.BY_ID(userId));
      // API Doc User Service: should return 204 No Content or a success message
      setUsers(prevUsers => prevUsers.filter(user => user.id !== userId));
      return { success: true, message: "Xóa người dùng thành công" };
    } catch (error) {
      console.error("Error deleting user:", error.message, error.originalError);
      const message = error.message || "Lỗi xóa người dùng.";
      setAuthError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  // Load system roles and permissions (for admin panels)
  const loadSystemRolesAndPermissions = async () => {
    setLoading(true);
    try {
      const [rolesRes, permissionsRes] = await Promise.all([
        api.get(API_ENDPOINTS.ROLES.BASE), // GET /api/v1/roles
        api.get(API_ENDPOINTS.PERMISSIONS.BASE) // GET /api/v1/permissions
      ]);
      // API Doc: /roles returns array of roles, /permissions returns array of permissions
      setAllRoles(rolesRes.data || []); // Assuming response.data is the array
      setAllPermissions(permissionsRes.data || []);
      return { success: true };
    } catch (error) {
      console.error("Error loading system roles/permissions:", error.message, error.originalError);
      setAuthError(error.message || "Lỗi tải danh sách vai trò/quyền hệ thống.");
      return { success: false, message: error.message || "Lỗi tải danh sách vai trò/quyền hệ thống." };
    } finally {
      setLoading(false);
    }
  };


  const value = {
    currentUser,
    userPermissions,
    userRoles, // This now stores role names or objects
    loading,
    authError,
    login,
    register,
    logout,
    checkLoggedInUser, // Renamed to avoid conflict if imported directly
    hasPermission,
    hasRole,
    isAdmin,
    users, // List of all users for admin
    fetchUsers,
    createUser,
    updateUserProfile, // Used by User.jsx
    changePassword,    // Used by User.jsx
    deleteUser,
    allRoles,
    allPermissions,
    loadSystemRolesAndPermissions,
    setAuthError,
    PERMISSIONS, // Export PERMISSIONS constant from here
    DEFAULT_ROLES, // Export DEFAULT_ROLES from here too
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

// PermissionGate, RoleGate, AdminGate components remain the same
// ... (Copy PermissionGate, RoleGate, AdminGate from your original file)
export const PermissionGate = ({ children, permission, fallback = null }) => {
  const { hasPermission, loading: authLoadingContext } = useAuth(); // Renamed loading to avoid conflict
  
  if (authLoadingContext) return null; // Or a loading spinner
  if (!permission || hasPermission(permission)) return children;
  return fallback;
};

export const RoleGate = ({ children, role, fallback = null }) => {
  const { hasRole, loading: authLoadingContext } = useAuth();
  
  if (authLoadingContext) return null;
  if (!role || hasRole(role)) return children;
  return fallback;
};

export const AdminGate = ({ children, fallback = null }) => {
  const { isAdmin, loading: authLoadingContext } = useAuth();
  
  if (authLoadingContext) return null;
  if (isAdmin()) return children;
  return fallback;
};