import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import api from '../api/client';
import { Client } from '../types';

export default function Clients() {
  const [clients, setClients] = useState<Client[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newClient, setNewClient] = useState({ name: '', slug: '', contact_email: '', business_type: '' });

  const fetchClients = async () => {
    try {
      const res = await api.get('/clients');
      setClients(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/clients', newClient);
      setIsModalOpen(false);
      setNewClient({ name: '', slug: '', contact_email: '', business_type: '' });
      fetchClients();
    } catch (err) {
      console.error(err);
    }
  };

  const filteredClients = clients.filter(c => c.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">Clientes</h1>
        <button
          onClick={() => setIsModalOpen(true)}
          className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-md flex items-center text-sm font-medium"
        >
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Cliente
        </button>
      </div>

      <div className="flex items-center space-x-4">
        <div className="relative flex-1 max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-slate-500" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-2 border border-slate-700 rounded-md leading-5 bg-slate-900 text-slate-300 placeholder-slate-500 focus:outline-none focus:ring-brand-500 focus:border-brand-500 sm:text-sm"
            placeholder="Buscar cliente..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-slate-800">
          <thead className="bg-slate-950">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Nombre</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Tipo</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Estado</th>
              <th scope="col" className="relative px-6 py-3"><span className="sr-only">Acciones</span></th>
            </tr>
          </thead>
          <tbody className="bg-slate-900 divide-y divide-slate-800">
            {loading ? (
              <tr><td colSpan={4} className="px-6 py-4 text-center text-slate-400">Cargando...</td></tr>
            ) : filteredClients.map((client) => (
              <tr key={client.id} className="hover:bg-slate-800/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-white">{client.name}</div>
                  <div className="text-sm text-slate-400">{client.contact_email}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                  {client.business_type}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    client.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {client.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <Link to={`/clients/${client.slug}`} className="text-brand-400 hover:text-brand-300">
                    Ver Detalles
                  </Link>
                </td>
              </tr>
            ))}
            {!loading && filteredClients.length === 0 && (
              <tr><td colSpan={4} className="px-6 py-4 text-center text-slate-400">No se encontraron clientes.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true" onClick={() => setIsModalOpen(false)}>
              <div className="absolute inset-0 bg-slate-950 opacity-75"></div>
            </div>
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div className="inline-block align-bottom bg-slate-900 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full border border-slate-800">
              <form onSubmit={handleCreate}>
                <div className="bg-slate-900 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                  <h3 className="text-lg leading-6 font-medium text-white mb-4">Nuevo Cliente</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-300">Nombre</label>
                      <input type="text" required value={newClient.name} onChange={e => setNewClient({...newClient, name: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300">Slug</label>
                      <input type="text" required value={newClient.slug} onChange={e => setNewClient({...newClient, slug: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300">Email Contacto</label>
                      <input type="email" value={newClient.contact_email} onChange={e => setNewClient({...newClient, contact_email: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300">Tipo de Negocio</label>
                      <input type="text" value={newClient.business_type} onChange={e => setNewClient({...newClient, business_type: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                    </div>
                  </div>
                </div>
                <div className="bg-slate-950 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-slate-800">
                  <button type="submit" className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-brand-600 text-base font-medium text-white hover:bg-brand-700 sm:ml-3 sm:w-auto sm:text-sm">
                    Guardar
                  </button>
                  <button type="button" onClick={() => setIsModalOpen(false)} className="mt-3 w-full inline-flex justify-center rounded-md border border-slate-700 shadow-sm px-4 py-2 bg-slate-800 text-base font-medium text-slate-300 hover:bg-slate-700 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                    Cancelar
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
