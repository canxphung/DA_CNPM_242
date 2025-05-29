import React from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import routes from "./routers";
import PrivateRoute from "./PrivateRoute";
import AdminRoute from "./AdminRoute";
import UserRoute from "./UserRoute";
import PublicRoute from "./PublicRoute";

// Tạo router dựa trên cấu hình routes
const router = createBrowserRouter(
  routes
    .map((route) => {
      // Xử lý public routes
      if (route.public) {
        return {
          path: route.path,
          element: (
            <PublicRoute
              redirectAuthenticated={route.redirectAuthenticated !== false}
            >
              <route.element />
            </PublicRoute>
          ),
        };
      }

      // Xử lý admin routes
      if (route.admin) {
        return {
          path: route.path,
          element: (
            <AdminRoute>
              <route.element />
            </AdminRoute>
          ),
        };
      }

      // Xử lý user routes
      if (route.user) {
        return {
          path: route.path,
          element: (
            <UserRoute>
              <route.element />
            </UserRoute>
          ),
        };
      }

      // Xử lý private routes (cần đăng nhập, mọi role)
      if (route.private) {
        return {
          path: route.path,
          element: (
            <PrivateRoute>
              <route.element />
            </PrivateRoute>
          ),
        };
      }

      // Routes mặc định
      return {
        path: route.path,
        element: <route.element />,
      };
    })
    .concat([
      // Route mặc định - chuyển hướng đến trang chủ nếu không tìm thấy route
      {
        path: "*",
        element: <Navigate to="/" replace />,
      },
    ])
);

export default router;
