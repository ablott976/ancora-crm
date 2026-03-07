import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, Box, FileText, LogOut, Anchor } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import clsx from 'clsx';

export default function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();

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
