import Sidebar from "./Sidebar";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-screen bg-gradient-to-br from-gray-900 to-black text-white">
      <Sidebar />
      <main className="flex-1 p-6 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
