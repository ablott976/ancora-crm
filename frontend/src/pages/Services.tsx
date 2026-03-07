import { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import api from '../api/client';
import { ServiceCatalog } from '../types';

export default function Services() {
  const [services, setServices] = useState<ServiceCatalog[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newService, setNewService] = useState({ name: '', description: '', default_monthly_price: '', default_setup_price: '', category: '' });

  const fetchServices = async () => {
    try {
      const res = await api.get('/services');
      setServices(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServices();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/services', {
        ...newService,
        default_monthly_price: parseFloat(newService.default_monthly_price) || 0,
        default_setup_price: parseFloat(newService.default_setup_price) || 0,
      });
      setIsModalOpen(false);
      setNewService({ name: '', description: '', default_monthly_price: '', default_setup_price: '', category: '' });
      fetchServices();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">Catálogo de Servicios</h1>
        <button
          onClick={() => setIsModalOpen(true)}
          className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-md flex items-center text-sm font-medium"
        >
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Servicio
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <p className="text-slate-400">Cargando...</p>
        ) : services.map(service => (
          <div key={service.id} className="bg-slate-900 border border-slate-800 rounded-lg p-6 flex flex-col">
            <div className="flex justify-between items-start mb-2">
              <h3 className="text-lg font-semibold text-white">{service.name}</h3>
              <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${service.is_active ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-800'}`}>
                {service.is_active ? 'Activo' : 'Inactivo'}
              </span>
            </div>
            <p className="text-sm text-slate-400 mb-4 flex-1">{service.description}</p>
            <div className="border-t border-slate-800 pt-4 mt-auto">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Mensual</span>
                <span className="font-medium text-slate-300">€{service.default_monthly_price}</span>
              </div>
              <div className="flex justify-between text-sm mt-1">
                <span className="text-slate-500">Setup</span>
                <span className="font-medium text-slate-300">€{service.default_setup_price}</span>
              </div>
            </div>
          </div>
        ))}
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
                  <h3 className="text-lg leading-6 font-medium text-white mb-4">Nuevo Servicio</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-300">Nombre</label>
                      <input type="text" required value={newService.name} onChange={e => setNewService({...newService, name: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300">Categoría</label>
                      <input type="text" value={newService.category} onChange={e => setNewService({...newService, category: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300">Descripción</label>
                      <textarea value={newService.description} onChange={e => setNewService({...newService, description: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-300">Precio Mensual (€)</label>
                        <input type="number" step="0.01" required value={newService.default_monthly_price} onChange={e => setNewService({...newService, default_monthly_price: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-300">Setup (€)</label>
                        <input type="number" step="0.01" required value={newService.default_setup_price} onChange={e => setNewService({...newService, default_setup_price: e.target.value})} className="mt-1 block w-full px-3 py-2 border border-slate-700 rounded-md bg-slate-800 text-white" />
                      </div>
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
