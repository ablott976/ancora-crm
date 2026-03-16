import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Plus } from 'lucide-react';
import api from '../api/client';
import { Client, ClientService, Invoice, ServiceCatalog } from '../types';

export default function ClientDetail() {
  const { slug } = useParams<{ slug: string }>();
  const [client, setClient] = useState<Client | null>(null);
  const [services, setServices] = useState<ClientService[]>([]);
  const [catalog, setCatalog] = useState<ServiceCatalog[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal states
  const [isServiceModalOpen, setIsServiceModalOpen] = useState(false);
  const [newService, setNewService] = useState({ service_id: '', monthly_price: '', setup_price: '' });

  const fetchData = async () => {
    try {
      const clientRes = await api.get(`/clients/slug/${slug}`);
      const clientId = clientRes.data.id;
      setClient(clientRes.data);

      const [servRes, invRes, catRes] = await Promise.all([
        api.get(`/clients/${clientId}/services`),
        api.get(`/invoices?client_id=${clientId}`),
        api.get('/services')
      ]);

      setServices(servRes.data);
      setInvoices(invRes.data);
      setCatalog(catRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [slug]);

  const handleAddService = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!client) return;
    try {
      await api.post(`/clients/${client.id}/services`, {
        service_id: parseInt(newService.service_id),
        monthly_price: parseFloat(newService.monthly_price) || 0,
        setup_price: parseFloat(newService.setup_price) || 0
      });
      setIsServiceModalOpen(false);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) return <div>Cargando cliente...</div>;
  if (!client) return <div>Cliente no encontrado.</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-white">{client.name}</h1>
          <p className="text-slate-400 mt-1">{client.business_type} • {client.city}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-medium text-white mb-4">Información</h2>
          <div className="space-y-3 text-sm">
            <p><span className="text-slate-500">Contacto:</span> <span className="text-slate-300">{client.contact_name || '-'}</span></p>
            <p><span className="text-slate-500">Email:</span> <span className="text-slate-300">{client.contact_email || '-'}</span></p>
            <p><span className="text-slate-500">Teléfono:</span> <span className="text-slate-300">{client.contact_phone || '-'}</span></p>
            <p><span className="text-slate-500">Dirección:</span> <span className="text-slate-300">{client.address || '-'}</span></p>
            <p><span className="text-slate-500">Alta:</span> <span className="text-slate-300">{client.onboarding_date || '-'}</span></p>
            <p><span className="text-slate-500">Estado:</span> 
              <span className={`ml-2 px-2 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full ${
                client.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>{client.status}</span>
            </p>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-medium text-white">Servicios Contratados</h2>
            <button onClick={() => setIsServiceModalOpen(true)} className="text-brand-400 hover:text-brand-300">
              <Plus className="w-5 h-5" />
            </button>
          </div>
          <div className="space-y-3">
            {services.map(cs => (
              <div key={cs.id} className="flex justify-between items-center p-3 bg-slate-950 rounded border border-slate-800">
                <div>
                  <p className="font-medium text-white">{cs.service?.name}</p>
                  <p className="text-xs text-slate-400">Mensual: €{cs.monthly_price} | Setup: €{cs.setup_price}</p>
                </div>
                <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                  cs.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-800'
                }`}>
                  {cs.status}
                </span>
              </div>
            ))}
            {services.length === 0 && <p className="text-sm text-slate-500">Sin servicios</p>}
          </div>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 className="text-lg font-medium text-white mb-4">Facturas</h2>
        <table className="min-w-full divide-y divide-slate-800">
          <thead>
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-400 uppercase">Número</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-400 uppercase">Fecha</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-400 uppercase">Total</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-400 uppercase">Estado</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {invoices.map(inv => (
              <tr key={inv.id}>
                <td className="px-4 py-3 text-sm text-white">{inv.invoice_number || 'S/N'}</td>
                <td className="px-4 py-3 text-sm text-slate-300">{inv.invoice_date || '-'}</td>
                <td className="px-4 py-3 text-sm text-slate-300">€{inv.total_amount}</td>
                <td className="px-4 py-3 text-sm">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    inv.status === 'paid' ? 'bg-green-100 text-green-800' :
                    inv.status === 'pending' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {inv.status}
                  </span>
                </td>
              </tr>
            ))}
            {invoices.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-3 text-sm text-slate-500 text-center">Sin facturas</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {isServiceModalOpen && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true" onClick={() => setIsServiceModalOpen(false)}>
              <div className="absolute inset-0 bg-slate-950 opacity-75"></div>
            </div>
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div className="inline-block align-bottom bg-slate-900 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full border border-slate-800">
              <form onSubmit={handleAddService}>
                <div className="bg-slate-900 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                  <h3 className="text-lg leading-6 font-medium text-white mb-4">Añadir Servicio</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-300">Servicio</label>
                      <select required value={newService.service_id} onChange={e => {
                        const s = catalog.find(c => c.id === parseInt(e.target.value));
                        setNewService({
                          service_id: e.target.value,
                          monthly_price: s?.default_monthly_price?.toString() || '',
                          setup_price: s?.default_setup_price?.toString() || ''
                        });
                      }} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white">
                        <option value="">Seleccione...</option>
                        {catalog.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300">Precio Mensual (€)</label>
                      <input type="number" step="0.01" value={newService.monthly_price} onChange={e => setNewService({...newService, monthly_price: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300">Precio Setup (€)</label>
                      <input type="number" step="0.01" value={newService.setup_price} onChange={e => setNewService({...newService, setup_price: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                    </div>
                  </div>
                </div>
                <div className="bg-slate-950 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-slate-800">
                  <button type="submit" className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-brand-600 text-base font-medium text-white hover:bg-brand-700 sm:ml-3 sm:w-auto sm:text-sm">
                    Guardar
                  </button>
                  <button type="button" onClick={() => setIsServiceModalOpen(false)} className="mt-3 w-full inline-flex justify-center rounded-md border border-slate-700 shadow-sm px-4 py-2 bg-slate-800 text-base font-medium text-slate-300 hover:bg-slate-700 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
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
