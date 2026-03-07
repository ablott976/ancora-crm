import { useEffect, useState } from 'react';
import { Users, Euro, FileWarning, TrendingUp } from 'lucide-react';
import api from '../api/client';
import { DashboardStats, Client } from '../types';
import { Link } from 'react-router-dom';

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, clientsRes] = await Promise.all([
          api.get('/dashboard/stats'),
          api.get('/clients')
        ]);
        setStats(statsRes.data);
        setClients(clientsRes.data.slice(0, 5)); // Just a few for the feed
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div>Cargando dashboard...</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-slate-900 p-6 rounded-lg border border-slate-800">
          <div className="flex items-center">
            <div className="p-3 rounded-md bg-brand-500/10 text-brand-500">
              <Users className="w-6 h-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-slate-400">Clientes Activos</p>
              <p className="text-2xl font-semibold text-white">{stats?.active_clients || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-900 p-6 rounded-lg border border-slate-800">
          <div className="flex items-center">
            <div className="p-3 rounded-md bg-green-500/10 text-green-500">
              <Euro className="w-6 h-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-slate-400">MRR</p>
              <p className="text-2xl font-semibold text-white">€{stats?.mrr || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-900 p-6 rounded-lg border border-slate-800">
          <div className="flex items-center">
            <div className="p-3 rounded-md bg-amber-500/10 text-amber-500">
              <FileWarning className="w-6 h-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-slate-400">Facturas Pendientes</p>
              <p className="text-2xl font-semibold text-white">{stats?.pending_invoices_count || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-900 p-6 rounded-lg border border-slate-800">
          <div className="flex items-center">
            <div className="p-3 rounded-md bg-brand-500/10 text-brand-500">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-slate-400">Ingresos YTD</p>
              <p className="text-2xl font-semibold text-white">€{stats?.ytd_revenue || 0}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        <h2 className="text-lg font-medium text-white mb-4">Clientes Recientes</h2>
        <div className="divide-y divide-slate-800">
          {clients.map(client => (
            <div key={client.id} className="py-4 flex justify-between items-center">
              <div>
                <Link to={`/clients/${client.slug}`} className="text-brand-400 hover:text-brand-300 font-medium">
                  {client.name}
                </Link>
                <p className="text-sm text-slate-400">{client.business_type} • {client.city}</p>
              </div>
              <div>
                <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                  client.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {client.status}
                </span>
              </div>
            </div>
          ))}
          {clients.length === 0 && <p className="text-slate-400 py-4">No hay clientes recientes.</p>}
        </div>
      </div>
    </div>
  );
}
