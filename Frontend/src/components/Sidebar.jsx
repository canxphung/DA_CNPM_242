// src/components/Sidebar.jsx
import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth, AdminGate, PermissionGate } from '../contexts/AuthContext';
import { PERMISSIONS } from '../utils/constants';
import { Home, LayoutDashboard, Settings, User, Users, Bot, Lightbulb, Activity, LogOut, FileText } from 'lucide-react';

const Sidebar = () => {
  const { logout, currentUser, loading } = useAuth();
  const location = useLocation();

  const navItems = [
    { name: 'Trang chủ', icon: Home, path: '/', permission: PERMISSIONS.VIEW_DASHBOARD },
    { name: 'Thiết bị', icon: LayoutDashboard, path: '/devices', permission: PERMISSIONS.VIEW_DASHBOARD },
    { name: 'Lịch tưới', icon: Activity, path: '/schedule', permission: PERMISSIONS.MANAGE_SCHEDULES },
    { name: 'Báo cáo', icon: FileText, path: '/reports', permission: PERMISSIONS.VIEW_REPORTS },
    { name: 'Cấu hình', icon: Settings, path: '/config-device', permission: PERMISSIONS.VIEW_SETTINGS },
    { name: 'AI Chatbot', icon: Bot, path: '/ai-chat', permission: PERMISSIONS.VIEW_DASHBOARD },
    { name: 'Khuyến nghị AI', icon: Lightbulb, path: '/ai-recommendations', permission: PERMISSIONS.VIEW_REPORTS },
    { name: 'Phân tích', icon: Activity, path: '/advanced-analytics', permission: PERMISSIONS.VIEW_REPORTS },
    { name: 'Hồ sơ', icon: User, path: '/profile', permission: PERMISSIONS.EDIT_PROFILE },
  ];

  const adminNavItems = [
    { name: 'Quản lý người dùng', icon: Users, path: '/admin', permission: PERMISSIONS.MANAGE_USERS },
  ];

  // Debug log only once on mount and when currentUser changes
  useEffect(() => {
    if (currentUser) {
      console.log('Sidebar Debug - User loaded:', {
        id: currentUser.id,
        email: currentUser.email,
        roles: currentUser.roles,
        permissions: currentUser.permissions || currentUser.customPermissions,
        hasPermissions: Array.isArray(currentUser.permissions) || Array.isArray(currentUser.customPermissions),
        permissionCount: (currentUser.permissions || currentUser.customPermissions || []).length
      });
    }
  }, [currentUser?.id]); // Only re-run when user ID changes

  // If still loading, show loading state
  if (loading) {
    return (
      <div className="w-64 min-h-screen bg-gray-800 text-white flex flex-col p-4 shadow-lg fixed top-0 left-0">
        <div className="flex-shrink-0 mb-6 text-center">
          <h1 className="text-3xl font-bold text-green-400">SmartWater</h1>
        </div>
        <div className="flex-grow flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-green-400"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-64 min-h-screen bg-gray-800 text-white flex flex-col p-4 shadow-lg fixed top-0 left-0 overflow-y-auto">
      <div className="flex-shrink-0 mb-6 text-center">
        <h1 className="text-3xl font-bold text-green-400">SmartWater</h1>
        {currentUser && (
          <p className="text-sm text-gray-400 mt-1">
            Chào, {currentUser.firstName || currentUser.email?.split('@')[0] || 'User'}!
          </p>
        )}
      </div>

      <nav className="flex-grow">
        <span className="text-xs uppercase text-gray-500 font-semibold ml-3 mb-2 block">Chức năng</span>
        <ul className="space-y-2">
          {navItems.map((item) => (
            <li key={item.path}>
              <Link
                to={item.path}
                className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200 ${
                  location.pathname === item.path
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'hover:bg-gray-700 text-gray-300'
                }`}
              >
                <item.icon className="w-5 h-5 mr-3 flex-shrink-0" />
                {item.name}
              </Link>
            </li>
          ))}
        </ul>

        <AdminGate>
          <span className="text-xs uppercase text-gray-500 font-semibold ml-3 mt-6 mb-2 block pt-4 border-t border-gray-700">
            Quản trị
          </span>
          <ul className="space-y-2">
            {adminNavItems.map((item) => (
              <PermissionGate key={item.path} permission={item.permission}>
                <li>
                  <Link
                    to={item.path}
                    className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200 ${
                      location.pathname === item.path
                        ? 'bg-red-600 text-white shadow-md'
                        : 'hover:bg-gray-700 text-gray-300'
                    }`}
                  >
                    <item.icon className="w-5 h-5 mr-3 flex-shrink-0" />
                    {item.name}
                  </Link>
                </li>
              </PermissionGate>
            ))}
          </ul>
        </AdminGate>
      </nav>

      <div className="mt-auto pt-4 border-t border-gray-700">
        <button
          onClick={() => {
            console.log('Logout button clicked');
            logout();
          }}
          className="flex items-center px-3 py-2.5 w-full rounded-lg text-sm font-medium bg-red-500 text-white hover:bg-red-600 transition-colors duration-200"
        >
          <LogOut className="w-5 h-5 mr-3" />
          Đăng xuất
        </button>
      </div>
    </div>
  );
};

export default Sidebar;