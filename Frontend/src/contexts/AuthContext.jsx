// contexts/AuthContext.jsx
import React, { createContext, useState, useEffect, useContext, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import api from "../utils/api";
import { API_ENDPOINTS, STORAGE_KEYS, ERROR_MESSAGES, PERMISSIONS as APP_PERMISSIONS, HTTP_STATUS } from "../utils/constants";

export const AuthContext = createContext();

export const PERMISSIONS = APP_PERMISSIONS;

export const DEFAULT_ROLES = {
  ADMIN: "admin",
  CUSTOMER: "customer",
  USER: "user", // Added this
  MANAGER: "manager",
  OPERATOR: "operator",
};

// Default permissions for each role
const DEFAULT_ROLE_PERMISSIONS = {
  admin: [
    PERMISSIONS.ADMIN_ACCESS,
    PERMISSIONS.MANAGE_USERS,
    PERMISSIONS.MANAGE_DEVICES,
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_REPORTS,
    PERMISSIONS.MANAGE_SCHEDULES,
    PERMISSIONS.VIEW_SETTINGS,
    PERMISSIONS.EDIT_PROFILE,
    PERMISSIONS.MANAGE_ROLES,
    PERMISSIONS.MANAGE_PERMISSIONS
  ],
  user: [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_REPORTS,
    PERMISSIONS.MANAGE_SCHEDULES,
    PERMISSIONS.VIEW_SETTINGS,
    PERMISSIONS.EDIT_PROFILE
  ],
  customer: [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_REPORTS,
    PERMISSIONS.EDIT_PROFILE
  ]
};

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [userPermissions, setUserPermissions] = useState([]);
  const [userRoles, setUserRoles] = useState([]);
  const [allRoles, setAllRoles] = useState([]);
  const [allPermissions, setAllPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");

  const navigate = useNavigate();

  // Memoize clearAuthDataAndRedirect to prevent re-creation
  const clearAuthDataAndRedirect = useCallback(() => {
    api.clearAuthData();
    setCurrentUser(null);
    setUserPermissions([]);
    setUserRoles([]);
    setUsers([]);
    navigate("/login-as");
  }, [navigate]);

  useEffect(() => {
    const handleAuthFailure = (event) => {
      console.log('Auth failure detected in AuthContext:', event.detail);
      setAuthError(event.detail.message || ERROR_MESSAGES.UNAUTHORIZED);
      clearAuthDataAndRedirect();
    };

    window.addEventListener('authFailure', handleAuthFailure);
    return () => window.removeEventListener('authFailure', handleAuthFailure);
  }, [clearAuthDataAndRedirect]);

  useEffect(() => {
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    if (token) {
      checkLoggedInUser();
    } else {
      setLoading(false);
    }
  }, []);

  const clearAuthDataOnly = () => {
    api.clearAuthData();
    setCurrentUser(null);
    setUserPermissions([]);
    setUserRoles([]);
  };

  const loadUserCompleteData = async (baseUserData) => {
    if (!baseUserData || !baseUserData.id) {
      console.error("Cannot load complete data without base user ID.");
      clearAuthDataAndRedirect();
      return;
    }
    
    try {
      const userDetailResponse = await api.get(API_ENDPOINTS.USERS.BY_ID(baseUserData.id));
      console.log("userDetailResponse", userDetailResponse);
      const completeUserData = userDetailResponse.data;
      console.log("completeUserData", completeUserData);
      
      if (completeUserData && (completeUserData.id || completeUserData._id)) {
        // Extract permissions and roles
        let permissions = completeUserData.customPermissions || completeUserData.permissions || [];
        let roles = completeUserData.roles || [];
        
        // Handle the single 'role' field if 'roles' array is empty
        if ((!roles || roles.length === 0) && completeUserData.role) {
          roles = [completeUserData.role];
        }
        
        // If user has no custom permissions, assign default permissions based on role
        if (permissions.length === 0 && completeUserData.role) {
          permissions = DEFAULT_ROLE_PERMISSIONS[completeUserData.role] || [];
          console.log(`Assigning default permissions for role ${completeUserData.role}:`, permissions);
        }
        
        // Convert to string arrays
        const permissionStrings = permissions.map(p => (typeof p === 'string' ? p : p.name));
        const roleStrings = roles.map(r => (typeof r === 'string' ? r : r.name));
        
        setCurrentUser(completeUserData);
        setUserPermissions(permissionStrings);
        setUserRoles(roleStrings);

        // Store in localStorage
        localStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(completeUserData));
        localStorage.setItem(STORAGE_KEYS.PERMISSIONS, JSON.stringify(permissionStrings));
        localStorage.setItem(STORAGE_KEYS.USER_ROLES, JSON.stringify(roleStrings));
        
        console.log("User data loaded successfully:", {
          userId: completeUserData.id || completeUserData._id,
          email: completeUserData.email,
          roles: roleStrings,
          permissions: permissionStrings
        });
      } else {
        throw new Error("Invalid complete user data from server");
      }
    } catch (error) {
      console.error("Error loading complete user data:", error.message, error.originalError);
      setAuthError(error.message || "Lỗi tải thông tin người dùng chi tiết.");
      clearAuthDataAndRedirect();
    }
  };

  const checkLoggedInUser = async () => {
    setLoading(true);
    setAuthError("");
    try {
      const response = await api.get(API_ENDPOINTS.AUTH.ME);
      const userDataFromAuthMe = response.data;

      if (userDataFromAuthMe && userDataFromAuthMe.id) {
        await loadUserCompleteData(userDataFromAuthMe);
      } else {
        throw new Error("Invalid user data from /auth/me");
      }
    } catch (error) {
      console.error("Error checking logged in user:", error.message, error.originalError);
      setAuthError(error.message || ERROR_MESSAGES.UNAUTHORIZED);
      clearAuthDataAndRedirect();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password, type = "customer") => {
    setLoading(true);
    setAuthError("");
    try {
      const response = await api.post(API_ENDPOINTS.AUTH.LOGIN, { email, password });
      const { user, tokens } = response.data;
      console.log("Login response:", response.data);
      
      if (tokens?.accessToken && user?.id) {
        api.setTokens(tokens.accessToken, tokens.refreshToken);
        await loadUserCompleteData(user);

        // Navigation based on role
        const userRole = user.role || (user.roles && user.roles[0]);
        if (userRole === DEFAULT_ROLES.ADMIN) {
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
      clearAuthDataOnly();
      return { success: false, message: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  const register = async (userData) => {
    setLoading(true);
    setAuthError("");
    try {
      const { firstName, lastName, email, password } = userData;
      const payload = { email, password, firstName, lastName };

      const response = await api.post(API_ENDPOINTS.AUTH.REGISTER, payload);
      const { accessToken, refreshToken, user } = response.data;

      if (accessToken && user?.id) {
        api.setTokens(accessToken, refreshToken);
        await loadUserCompleteData(user);
        navigate("/");
      }
      
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

  const logout = async (allDevices = false) => {
    setLoading(true);
    try {
      const refreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
      if (refreshToken) {
        const endpoint = allDevices ? API_ENDPOINTS.AUTH.LOGOUT_ALL : API_ENDPOINTS.AUTH.LOGOUT;
        if (allDevices) {
          await api.post(endpoint);
        } else {
          await api.post(endpoint, { refreshToken });
        }
      }
    } catch (error) {
      console.error("Logout API call failed:", error.message, error.originalError);
    } finally {
      clearAuthDataAndRedirect();
      setLoading(false);
    }
  };

  // Memoize permission checking functions
  const hasPermission = useCallback((permissionName) => {
    if (loading || !Array.isArray(userPermissions)) return false;
    
    // Check direct permissions
    if (userPermissions.includes(permissionName)) return true;
    
    // Check role-based permissions
    for (const role of userRoles) {
      const rolePermissions = DEFAULT_ROLE_PERMISSIONS[role];
      if (rolePermissions && rolePermissions.includes(permissionName)) {
        return true;
      }
    }
    
    return false;
  }, [loading, userPermissions, userRoles]);
  
  const hasRole = useCallback((roleNameToCheck) => {
    if (loading || !Array.isArray(userRoles)) return false;
    return userRoles.includes(roleNameToCheck);
  }, [loading, userRoles]);

  const isAdmin = useCallback(() => {
    return hasRole(DEFAULT_ROLES.ADMIN) || hasPermission(PERMISSIONS.ADMIN_ACCESS);
  }, [hasRole, hasPermission]);

  // Other functions remain the same...
  const fetchUsers = async (filters = {}) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== '' && value !== null) {
          params.append(key, value);
        }
      });

      const response = await api.get(`${API_ENDPOINTS.USERS.BASE}${params.toString() ? `?${params.toString()}` : ''}`);
      const usersData = response.data.users || response.data || [];
      const totalUsers = response.data.total || usersData.length;
      
      setUsers(usersData);
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
    setLoading(true);
    try {
      const response = await api.post(API_ENDPOINTS.USERS.BASE, userData);
      const newUser = response.data;
      setUsers(prevUsers => [...prevUsers, newUser]);
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
    setLoading(true);
    try {
      const canUpdate = hasPermission(PERMISSIONS.UPDATE_USER) || 
                        (currentUser && currentUser.id === userId && hasPermission(PERMISSIONS.EDIT_PROFILE));
      
      if (!canUpdate) {
        setAuthError("Không có quyền cập nhật thông tin người dùng này.");
        return { success: false, message: "Không có quyền cập nhật thông tin người dùng này." };
      }

      const response = await api.put(API_ENDPOINTS.USERS.BY_ID(userId), updatedData);
      const updatedUserFromServer = response.data;
      
      if (currentUser && currentUser.id === userId) {
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

  const changePassword = async (currentPassword, newPassword) => {
    setLoading(true);
    try {
      const response = await api.post(API_ENDPOINTS.USERS.CHANGE_PASSWORD, { currentPassword, newPassword });
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
      await api.delete(API_ENDPOINTS.USERS.BY_ID(userId));
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

  const loadSystemRolesAndPermissions = async () => {
    setLoading(true);
    try {
      const [rolesRes, permissionsRes] = await Promise.all([
        api.get(API_ENDPOINTS.ROLES.BASE),
        api.get(API_ENDPOINTS.PERMISSIONS.BASE)
      ]);
      setAllRoles(rolesRes.data || []);
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

  // Memoize the context value to prevent unnecessary re-renders
  const value = useMemo(() => ({
    currentUser,
    userPermissions,
    userRoles,
    loading,
    authError,
    login,
    register,
    logout,
    checkLoggedInUser,
    hasPermission,
    hasRole,
    isAdmin,
    users,
    fetchUsers,
    createUser,
    updateUserProfile,
    changePassword,
    deleteUser,
    allRoles,
    allPermissions,
    loadSystemRolesAndPermissions,
    setAuthError,
    PERMISSIONS,
    DEFAULT_ROLES,
  }), [currentUser, userPermissions, userRoles, loading, authError, users, allRoles, allPermissions, hasPermission, hasRole, isAdmin]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const PermissionGate = ({ children, permission, fallback = null }) => {
  const { hasPermission, loading } = useAuth();
  
  if (loading) return null; // Don't render children during loading
  if (!permission || hasPermission(permission)) return children;
  return fallback;
};

export const RoleGate = ({ children, role, fallback = null }) => {
  const { hasRole, loading } = useAuth();
  
  if (loading) return null;
  if (!role || hasRole(role)) return children;
  return fallback;
};

export const AdminGate = ({ children, fallback = null }) => {
  const { isAdmin, loading } = useAuth();
  
  if (loading) return null;
  if (isAdmin()) return children;
  return fallback;
};