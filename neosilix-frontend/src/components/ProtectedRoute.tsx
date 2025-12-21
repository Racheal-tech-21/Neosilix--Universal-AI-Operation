import React, { ReactNode } from "react";
import { Navigate } from "react-router-dom";

interface ProtectedRouteProps {
  children: ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const token = localStorage.getItem("token"); // or your auth context

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
