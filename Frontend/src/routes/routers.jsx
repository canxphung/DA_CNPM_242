// src/routes/routers.jsx
import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import Home from "../pages/Home/Home";
import About from "../pages/FAQ/About";
import Devices from "../pages/Devices/Devices";
import Reports from "../pages/Reports/Reports";
import Schedule from "../pages/Schedule/Schedule";
import User from "../pages/Authentication/User";
import Admin from "../pages/Authentication/Admin";
import ConfigDevice from "../pages/Configdevice/ConfigDevice";
import Login from "../pages/Login/Login";
import SignUp from "../pages/SignUp/SignUp";
import { PERMISSIONS } from "../contexts/AuthContext"; // Keep this if PERMISSIONS is used elsewhere
import Unauthorized from "../pages/Authentication/Unauthorized";
import NotFound from "../pages/Authentication/NotFound";
import LandingPage from "../pages/LangdingPage/LandingPage";

import AIRecommendations from "../pages/AI/AIRecommendations";
import AIChat from "../pages/AI/AIChat";
import AdvancedAnalytics from "../pages/AI/AdvancedAnalytics";


import { AuthProvider, useAuth } from "../contexts/AuthContext";

const ProtectedRoute = () => { // Removed requiredPermission, handled by AdminOnlyRoute or specific PermissionGate in component
  const { currentUser, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        <span className="ml-3 text-lg">Đang tải...</span>
      </div>
    );
  }

  if (!currentUser) {
    return <Navigate to="/login-as" replace />;
  }

  // No specific permission check here, AdminOnlyRoute handles admin access.
  // Individual components can use <PermissionGate> for finer control.
  return <Outlet />;
};

const AuthLayout = () => {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  );
};

const AdminOnlyRoute = () => {
  const { currentUser, isAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        <span className="ml-3 text-lg">Đang tải...</span>
      </div>
    );
  }

  if (!currentUser) {
    // Could also check if already on /login-as to prevent redirect loop, though navigate 'replace' helps
    return <Navigate to="/login-as" replace />;
  }

  if (!isAdmin()) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
};

export const router = createBrowserRouter([
  {
    element: <AuthLayout />,
    children: [
      // Public routes
      {
        path: "/login-as",
        element: <LandingPage />,
      },
      {
        path: "/login/:userType", // Handles both /login/customer and /login/admin
        element: <Login />,
      },
      {
        path: "/register",
        element: <SignUp />,
      },
      {
        path: "/unauthorized",
        element: <Unauthorized />,
      },

      // Protected routes - require login
      {
        element: <ProtectedRoute />, // This wrapper ensures user is logged in
        children: [
          {
            path: "/",
            element: <Home />,
          },
          {
            path: "/about", // Assuming /about is for logged-in users, if public, move out
            element: <About />,
          },
          {
            path: "/profile", // Changed from /account to /profile to match Sidebar
            element: <User />,
          },
          {
            path: "/devices",
            element: <Devices />,
          },
          {
            path: "/reports", // Uncommented
            element: <Reports />,
          },
          {
            path: "/schedule",
            element: <Schedule />,
          },
          {
            path: "/config-device", // Changed to match Sidebar
            element: <ConfigDevice />,
          },
          {
            path: "/ai-recommendations",
            element: <AIRecommendations />,
          },
          {
            path: "/ai-chat",
            element: <AIChat />,
          },
          {
            path: "/advanced-analytics",
            element: <AdvancedAnalytics />,
          }
        ],
      },

      // Admin-only routes
      {
        element: <AdminOnlyRoute />, // This wrapper ensures user is logged in AND is an admin
        children: [
          {
            path: "/admin", // Main admin page for user management
            element: <Admin />,
          },
          // Add other admin-specific routes here if needed
          // e.g., { path: "/admin/settings", element: <AdminSettings /> }
        ],
      },
      
      // Fallback for /login to redirect to /login-as
      {
        path: "/login",
        element: <Navigate to="/login-as" replace />,
      },

      // Not Found Route - must be the last one in this level
      {
        path: "*",
        element: <NotFound />,
      },
    ],
  },
]);