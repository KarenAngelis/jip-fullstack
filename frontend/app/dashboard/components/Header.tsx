// src/app/dashboard/components/Header.tsx
"use client";

import { useState } from "react";
import {
  Search,
  Bell,
  LogOut,
  User as UserIcon, // evita colisão com o tipo User
  Settings,
  ChevronDown,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { authAPI, type User } from "@/lib/api"; // ✅ usa o MESMO tipo User do SDK

type HeaderProps = {
  user: User;
};

export function Header({ user }: HeaderProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [notificationCount, setNotificationCount] = useState(3);

  const handleLogout = () => {
    authAPI.logout();               // ✅ limpa cookies/localStorage e header
    router.push("/auth/login");
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    // implemente se quiser: router.push(`/dashboard/search?q=${encodeURIComponent(searchQuery)}`)
    console.log("Buscando:", searchQuery);
  };

  const clearNotifications = () => setNotificationCount(0);

  const displayName = user.nome ?? user.email ?? "Usuário";
  const initial = (displayName[0] || "?").toUpperCase();

  return (
    <header className="flex items-center justify-between p-4 lg:p-6 border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm">
      {/* Título */}
      <div className="flex-1">
        <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
      </div>

      <div className="flex items-center gap-4">
        {/* Busca */}
        <form onSubmit={handleSearch} className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
          <input
            type="text"
            placeholder="Pesquisar trends, roteiros..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500 w-64 transition-all"
          />
        </form>

        {/* Notificações */}
        <div className="relative">
          <button
            onClick={clearNotifications}
            className="relative p-2 rounded-full hover:bg-gray-800 transition-colors"
            title="Notificações"
          >
            <Bell className="h-6 w-6 text-gray-400" />
            {notificationCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-cyan-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center font-medium">
                {notificationCount > 9 ? "9+" : notificationCount}
              </span>
            )}
          </button>
        </div>

        {/* Menu do Usuário */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu((v) => !v)}
            className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-800 transition-colors"
          >
            <div className="w-10 h-10 rounded-full bg-gradient-to-r from-cyan-500 to-purple-500 flex items-center justify-center font-bold text-white">
              {initial}
            </div>
            <div className="hidden sm:block text-left">
              <p className="font-semibold text-white text-sm">{displayName}</p>
              <p className="text-xs text-gray-400">{user.email}</p>
            </div>
            <ChevronDown
              className={`h-4 w-4 text-gray-400 transition-transform ${
                showUserMenu ? "rotate-180" : ""
              }`}
            />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 top-full mt-2 w-56 bg-gray-800 border border-gray-700 rounded-lg shadow-lg py-2 z-50">
              <div className="px-4 py-2 border-b border-gray-700">
                <p className="font-semibold text-white text-sm">{displayName}</p>
                <p className="text-xs text-gray-400">{user.email}</p>
              </div>

              <button
                onClick={() => {
                  setShowUserMenu(false);
                  router.push("/dashboard/profile");
                }}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
              >
                <UserIcon className="h-4 w-4" />
                Meu Perfil
              </button>

              <button
                onClick={() => {
                  setShowUserMenu(false);
                  router.push("/dashboard/settings");
                }}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
              >
                <Settings className="h-4 w-4" />
                Configurações
              </button>

              <div className="mt-2 border-t border-gray-700">
                <button
                  onClick={() => {
                    setShowUserMenu(false);
                    handleLogout();
                  }}
                  className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-400 hover:bg-gray-700 transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  Sair
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Overlay para fechar dropdown */}
      {showUserMenu && (
        <div className="fixed inset-0 z-40" onClick={() => setShowUserMenu(false)} />
      )}
    </header>
  );
}
