import React from "react";
import { BrowserRouter as Router, Routes, Route, useLocation, Navigate } from "react-router-dom";
import LoginPage from "./components/LoginPage";
import SignupPage from "./components/SignupPage";
import PaymentPage from "./components/PaymentPage";
import Sidebar from "./components/Sidebar";
import DashboardPage from "./components/DashboardPage";
import SystemsPage from "./components/SystemsPage";
import CopilotPage from "./components/CopilotPage";
import LogsPage from './components/LogsPage';
import UnifiedDashboard from "./components/monitoring/UnifiedDashboard";
import NeosilixLanding from "./components/NeosilixLanding";
import "./index.css";

const App: React.FC = () => {
  return (
    <Router>
      <MainLayout />
    </Router>
  );
};

const MainLayout: React.FC = () => {
  const location = useLocation();
  const token = localStorage.getItem("token");
  
  // Pages that don't require authentication
  const publicPages = ["/", "/login", "/signup", "/payment"];
  const isPublicPage = publicPages.includes(location.pathname);
  
  // If not authenticated and trying to access protected route, redirect to landing
  if (!token && !isPublicPage) {
    return <Navigate to="/" replace />;
  }

  // Landing page route (no sidebar)
  if (location.pathname === "/" && !token) {
    return <NeosilixLanding />;
  }

  // Auth pages (login, signup, payment) - no sidebar
  const hideSidebar = ["/login", "/signup", "/payment"].includes(location.pathname);
  
  return hideSidebar ? (
    <div className="min-h-screen flex items-center justify-center bg-black px-4">
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/payment" element={<PaymentPage />} />
      </Routes>
    </div>
  ) : (
    <div className="flex min-h-screen bg-gray-900 text-gray-100">
      <Sidebar />
      <main className="flex-1 p-6">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/systems" element={<SystemsPage />} />
          <Route path="/copilot" element={<CopilotPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/monitoring" element={<UnifiedDashboard />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
};

export default App;
