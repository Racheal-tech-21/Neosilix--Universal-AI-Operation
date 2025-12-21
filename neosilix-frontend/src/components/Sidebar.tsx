import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ServerCog,
  BrainCog,
  Activity,
  Gauge,
  LogOut,
} from "lucide-react";

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  // Helper to check active route
  const isActive = (path: string) => location.pathname === path;

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <aside className="w-64 min-h-screen bg-zinc-950 text-white p-6 shadow-lg flex flex-col justify-between">
      <div>
        <h2 className="text-2xl font-extrabold mb-8 tracking-wider select-none">
          NEOSILIX UNIVERSAL AIOps
        </h2>
        <nav className="flex flex-col gap-5 text-lg">
          <Link
            to="/"
            className={`flex gap-3 items-center px-3 py-2 rounded-md transition-colors duration-200 ${
              isActive("/")
                ? "bg-cyan-700 text-cyan-300 font-semibold"
                : "text-white hover:text-cyan-400 hover:bg-cyan-900"
            }`}
          >
            <LayoutDashboard className="w-6 h-6" /> Dashboard
          </Link>

          <Link
            to="/systems"
            className={`flex gap-3 items-center px-3 py-2 rounded-md transition-colors duration-200 ${
              isActive("/systems")
                ? "bg-cyan-700 text-cyan-300 font-semibold"
                : "text-white hover:text-cyan-400 hover:bg-cyan-900"
            }`}
          >
            <ServerCog className="w-6 h-6" /> Systems
          </Link>

          <Link
            to="/copilot"
            className={`flex gap-3 items-center px-3 py-2 rounded-md transition-colors duration-200 ${
              isActive("/copilot")
                ? "bg-cyan-700 text-cyan-300 font-semibold"
                : "text-white hover:text-cyan-400 hover:bg-cyan-900"
            }`}
          >
            <BrainCog className="w-6 h-6" /> Neosilix AI Centre
          </Link>

          <Link
            to="/monitoring"
            className={`flex gap-3 items-center px-3 py-2 rounded-md transition-colors duration-200 ${
              isActive("/monitoring")
                ? "bg-cyan-700 text-cyan-300 font-semibold"
                : "text-white hover:text-cyan-400 hover:bg-cyan-900"
            }`}
          >
            <Gauge className="w-6 h-6" /> System Monitor
          </Link>

          <Link
            to="/logs"
            className={`flex gap-3 items-center px-3 py-2 rounded-md transition-colors duration-200 ${
              isActive("/logs")
                ? "bg-cyan-700 text-cyan-300 font-semibold"
                : "text-white hover:text-cyan-400 hover:bg-cyan-900"
            }`}
          >
            <Activity className="w-6 h-6" /> Logs
          </Link>
        </nav>
      </div>

      {/* Footer with logout */}
      <div className="flex flex-col gap-4">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 rounded-md bg-red-600 hover:bg-red-700 transition-colors duration-200 font-semibold"
        >
          <LogOut className="w-6 h-6" /> Logout
        </button>
        <footer className="text-xs text-zinc-500 select-none tracking-wide text-center">
          © NEOSILIX by Racheal Inc. {new Date().getFullYear()}
        </footer>
      </div>
    </aside>
  );
}
