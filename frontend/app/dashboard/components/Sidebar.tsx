"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { 
  LayoutDashboard, 
  CheckSquare, 
  BrainCircuit, 
  Search, 
  BarChart2, 
  Settings, 
  LifeBuoy, 
  TrendingUp, 
  Sparkles, 
  ChevronDown,
  Mic,
  Menu,
  X,
  Wand2, // Para geração de conteúdo
  MessageCircle, // Para threads/comentários
  Lightbulb, // Para insights
  Target, // Para oportunidades
  Scale, // Para compliance
  FileText, // Para pautas
  User,
  LogOut,
  Crown,
  Zap
} from 'lucide-react';

interface NavItem {
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  badge?: string;
  children?: NavItem[];
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: "Principal",
    items: [
      { 
        name: 'Dashboard', 
        icon: LayoutDashboard, 
        href: '/dashboard' 
      },
      { 
        name: 'Geração de Conteúdo', 
        icon: Wand2, 
        href: '/dashboard/geracao-conteudo',
        badge: 'IA'
      },
      { 
        name: 'Pautas IA', 
        icon: FileText, 
        href: '/dashboard/pautas',
        badge: 'Popular'
      },
    ]
  },
  {
    title: "Análise & Insights",
    items: [
      { 
        name: 'Compliance', 
        icon: Scale, 
        href: '/dashboard/compliance',
        badge: 'Novo'
      },
      { 
        name: 'Tendências', 
        icon: TrendingUp, 
        href: '/dashboard/trends' 
      },
      { 
        name: 'Oportunidades', 
        icon: Target, 
        href: '/dashboard/oportunidades' 
      },
    ]
  },
  {
    title: "Criação",
    items: [
      { 
        name: 'Roteiros', 
        icon: Mic, 
        href: '/dashboard/roteiros',
        badge: 'Beta'
      },
      { 
        name: 'Insights', 
        icon: Lightbulb, 
        href: '/dashboard/insights' 
      },
    ]
  },
  {
    title: "Configurações",
    items: [
      { 
        name: 'Configurações', 
        icon: Settings, 
        href: '/dashboard/settings' 
      },
      { 
        name: 'Suporte', 
        icon: LifeBuoy, 
        href: '/dashboard/support' 
      },
    ]
  }
];

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onToggle }) => {
  const pathname = usePathname();
  const router = useRouter();
  const [expandedSections, setExpandedSections] = useState<string[]>(['Principal', 'Análise & Insights']);

  const toggleSection = (sectionTitle: string) => {
    setExpandedSections(prev => 
      prev.includes(sectionTitle) 
        ? prev.filter(title => title !== sectionTitle)
        : [...prev, sectionTitle]
    );
  };

  const handleLogout = () => {
    // Aqui você pode adicionar sua lógica de logout
    localStorage.removeItem('authToken');
    router.push('/auth/login');
  };

  const getBadgeColor = (badge: string) => {
    switch (badge) {
      case 'IA': return 'bg-gradient-to-r from-purple-500 to-pink-500';
      case 'Novo': return 'bg-gradient-to-r from-cyan-500 to-blue-500';
      case 'Beta': return 'bg-gradient-to-r from-orange-500 to-red-500';
      case 'Popular': return 'bg-gradient-to-r from-green-500 to-emerald-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <>
      {/* Mobile Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onToggle}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{
          x: isOpen ? 0 : -320,
          transition: { type: "spring", damping: 25, stiffness: 200 }
        }}
        className="fixed left-0 top-0 h-full w-80 bg-gray-900/95 backdrop-blur-xl border-r border-gray-800 z-50 lg:translate-x-0 lg:static lg:z-auto"
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-800">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-lg flex items-center justify-center">
                <BrainCircuit className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">JIP AI</h1>
                <p className="text-xs text-gray-400">Plataforma de IA</p>
              </div>
            </div>
            <button
              onClick={onToggle}
              className="lg:hidden p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* User Info */}
          <div className="p-4 border-b border-gray-800">
            <div className="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg">
              <div className="w-10 h-10 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">Usuário</p>
                <div className="flex items-center gap-1">
                  <Crown className="w-3 h-3 text-yellow-400" />
                  <span className="text-xs text-gray-400">Plano Pro</span>
                </div>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-4 space-y-6">
            {navSections.map((section) => (
              <div key={section.title}>
                <button
                  onClick={() => toggleSection(section.title)}
                  className="flex items-center justify-between w-full p-2 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:text-gray-300 transition-colors"
                >
                  <span>{section.title}</span>
                  <ChevronDown 
                    className={`w-4 h-4 transition-transform duration-200 ${
                      expandedSections.includes(section.title) ? 'rotate-180' : ''
                    }`} 
                  />
                </button>
                
                <AnimatePresence initial={false}>
                  {expandedSections.includes(section.title) && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="space-y-1 mt-2">
                        {section.items.map((item) => {
                          const isActive = pathname === item.href;
                          const Icon = item.icon;
                          
                          return (
                            <Link key={item.href} href={item.href}>
                              <motion.div
                                whileHover={{ x: 4 }}
                                className={`group flex items-center justify-between p-3 rounded-lg transition-all duration-200 ${
                                  isActive
                                    ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 text-cyan-300'
                                    : 'text-gray-300 hover:bg-gray-800/50 hover:text-white'
                                }`}
                              >
                                <div className="flex items-center gap-3">
                                  <Icon className={`w-5 h-5 ${isActive ? 'text-cyan-400' : 'text-gray-400 group-hover:text-gray-300'}`} />
                                  <span className="font-medium">{item.name}</span>
                                </div>
                                
                                {item.badge && (
                                  <span className={`px-2 py-1 text-xs font-bold text-white rounded-full ${getBadgeColor(item.badge)}`}>
                                    {item.badge}
                                  </span>
                                )}
                              </motion.div>
                            </Link>
                          );
                        })}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-800 space-y-3">
            {/* Upgrade Card */}
            <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="w-4 h-4 text-yellow-400" />
                <span className="text-sm font-semibold text-white">Upgrade</span>
              </div>
              <p className="text-xs text-gray-300 mb-3">
                Desbloqueie recursos avançados de IA
              </p>
              <button className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs font-medium py-2 px-3 rounded-lg hover:opacity-90 transition-opacity">
                Ver Planos
              </button>
            </div>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 w-full p-3 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all duration-200 group"
            >
              <LogOut className="w-5 h-5" />
              <span className="font-medium">Sair</span>
            </button>
          </div>
        </div>
      </motion.aside>
    </>
  );
};