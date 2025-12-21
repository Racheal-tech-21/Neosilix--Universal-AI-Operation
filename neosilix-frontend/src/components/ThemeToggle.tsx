import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const storedTheme = localStorage.getItem("theme");

    if (storedTheme === "dark") {
      document.documentElement.classList.add("dark");
      setIsDark(true);
    } else {
      document.documentElement.classList.remove("dark");
      setIsDark(false);
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = isDark ? "light" : "dark";

    document.documentElement.classList.toggle("dark", newTheme === "dark");
    localStorage.setItem("theme", newTheme);
    setIsDark(!isDark);
  };

  return (
    <button
      onClick={toggleTheme}
      className="text-white dark:text-gray-300 bg-gray-800 hover:bg-gray-700 px-3 py-2 rounded-md flex items-center gap-2 text-sm"
    >
      {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      {isDark ? "Light Mode" : "Dark Mode"}
    </button>
  );
}
