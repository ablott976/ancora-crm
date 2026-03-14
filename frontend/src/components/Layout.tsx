import { useState } from 'react';
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  Anchor,
  Bell,
  Box,
  Calendar,
  CalendarCheck,
  ChevronDown,
  FileCheck,
  FileText,
  LayoutDashboard,
  Lock,
  LogOut,
  Megaphone,
  MessageCircle,
  Mic,
  Phone,
  Shield,
  UserCheck,
  Users,
  Utensils,
  UtensilsCrossed,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import clsx from 'clsx';

export default function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const isPluginRoute = location.pathname.startsWith('/plugins');
  const [pluginsOpen, setPluginsOpen] = useState(isPluginRoute);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/clients', icon: Users, label: 'Clientes' },
    { to: '/services', icon: Box, label: 'Servicios' },
    { to: '/invoices', icon: FileText, label: 'Facturas' },
  ];

  const pluginItems = [
    { to: '/plugins/closures', icon: Lock, label: 'Closures' },
    { to: '/plugins/daily-menus', icon: UtensilsCrossed, label: 'DailyMenus' },
    { to: '/plugins/broadcasts', icon: Megaphone, label: 'Broadcasts' },
    { to: '/plugins/instagram-dm', icon: MessageCircle, label: 'InstagramDM' },
    { to: '/plugins/advanced-crm', icon: UserCheck, label: 'AdvancedCRM' },
    { to: '/plugins/audio-transcription', icon: Mic, label: 'AudioTranscription' },
    { to: '/plugins/restaurant-bookings', icon: Utensils, label: 'RestaurantBookings' },
    { to: '/plugins/owner-agent', icon: Shield, label: 'OwnerAgent' },
    { to: '/plugins/consent-forms', icon: FileCheck, label: 'ConsentForms' },
    { to: '/plugins/shift-view', icon: Calendar, label: 'ShiftView' },
    { to: '/plugins/voice-agent', icon: Phone, label: 'VoiceAgent' },
    { to: '/plugins/bookings', icon: CalendarCheck, label: 'Bookings' },
    { to: '/plugins/reminders', icon: Bell, label: 'Reminders' },
  ];

  return (
    <div className="flex h-screen bg-slate-900 text-slate-50">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 flex flex-col bg-slate-950">
        <div className="h-16 flex items-center px-6 border-b border-slate-800 text-brand-500">
          <Anchor className="w-6 h-6 mr-3" />
          <span className="text-xl font-bold tracking-tight text-white">Ancora CRM</span>
        </div>
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center px-3 py-2.5 rounded-md text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-500/10 text-brand-500'
                    : 'text-slate-400 hover:text-slate-50 hover:bg-slate-800/50'
                )
              }
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.label}
            </NavLink>
          ))}

          <div className="pt-3">
            <button
              type="button"
              onClick={() => setPluginsOpen((current) => !current)}
              className={clsx(
                'flex w-full items-center justify-between rounded-md px-3 py-2.5 text-sm font-medium transition-colors',
                isPluginRoute
                  ? 'bg-brand-500/10 text-brand-500'
                  : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-50'
              )}
            >
              <span className="flex items-center">
                <Box className="mr-3 h-5 w-5" />
                Plugins
              </span>
              <ChevronDown className={clsx('h-4 w-4 transition-transform', pluginsOpen && 'rotate-180')} />
            </button>
            {pluginsOpen ? (
              <div className="mt-2 space-y-1 pl-3">
                {pluginItems.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      clsx(
                        'flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-brand-500/10 text-brand-500'
                          : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-50'
                      )
                    }
                  >
                    <item.icon className="mr-3 h-4 w-4" />
                    {item.label}
                  </NavLink>
                ))}
              </div>
            ) : null}
          </div>
        </nav>
        <div className="p-4 border-t border-slate-800">
          <button
            onClick={handleLogout}
            className="flex items-center w-full px-3 py-2.5 text-sm font-medium text-slate-400 rounded-md hover:text-slate-50 hover:bg-slate-800/50 transition-colors"
          >
            <LogOut className="w-5 h-5 mr-3" />
            Cerrar Sesión
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="h-16 border-b border-slate-800 flex items-center justify-between px-8 bg-slate-900/50 backdrop-blur-sm">
          <h1 className="text-xl font-semibold">Ancora Automations</h1>
          <div className="flex items-center space-x-4">
            <div className="w-8 h-8 rounded-full bg-brand-500 flex items-center justify-center text-sm font-bold text-white">
              A
            </div>
          </div>
        </header>
        <div className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
