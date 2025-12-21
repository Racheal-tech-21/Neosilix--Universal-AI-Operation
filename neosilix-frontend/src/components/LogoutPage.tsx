import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function LogoutButton() {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <Button 
      onClick={handleLogout} 
      className="bg-red-600 hover:bg-red-700 text-white font-bold px-4 py-2 rounded-lg"
    >
      Logout
    </Button>
  );
}
