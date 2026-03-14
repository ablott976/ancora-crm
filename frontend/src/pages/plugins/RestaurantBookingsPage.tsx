import { useEffect, useState } from 'react';
import { Plus, Utensils } from 'lucide-react';
import api from '../../api/client';
import {
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Modal,
  ModalFormActions,
  PageHeader,
  SectionTitle,
  SimpleForm,
  StatusBadge,
  formatDate,
  formatError,
  inputClassName,
  pluginRoutePath,
  primaryButtonClassName,
} from './shared';

type Reservation = {
  id: number;
  client_name: string;
  client_phone: string;
  date: string;
  time: string;
  party_size: number;
  status: string;
  notes?: string | null;
};

type Zone = {
  id: number;
  name: string;
  capacity: number;
  is_active?: boolean;
};

const zoneInitial = { name: '', capacity: 20 };

export default function RestaurantBookingsPage() {
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoneModalOpen, setZoneModalOpen] = useState(false);
  const [zoneForm, setZoneForm] = useState(zoneInitial);
  const [submitting, setSubmitting] = useState(false);
  const [dateFilter, setDateFilter] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [reservationRes, zoneRes] = await Promise.all([
        api.get(pluginRoutePath('restaurant/reservations/10'), { params: { date_filter: dateFilter || undefined } }),
        api.get(pluginRoutePath('restaurant/zones/10')),
      ]);
      setReservations(reservationRes.data);
      setZones(zoneRes.data);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [dateFilter]);

  const createZone = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.post(pluginRoutePath('restaurant/zones'), { instance_id: 10, ...zoneForm, capacity: Number(zoneForm.capacity) });
      setZoneModalOpen(false);
      setZoneForm(zoneInitial);
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const totalCapacity = zones.reduce((sum, zone) => sum + zone.capacity, 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="RestaurantBookings"
        description="Consulta reservas de sala y gestiona la capacidad por zonas."
        action={
          <button type="button" onClick={() => setZoneModalOpen(true)} className={primaryButtonClassName}>
            <Plus className="mr-2 h-4 w-4" />
            Nueva zona
          </button>
        }
      />

      <Card className="grid gap-4 md:grid-cols-[1fr_280px]">
        <label className="block text-sm text-slate-400">
          Filtrar reservas por fecha
          <input type="date" value={dateFilter} onChange={(e) => setDateFilter(e.target.value)} className={inputClassName} />
        </label>
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
          <div className="text-sm text-slate-400">Capacidad activa</div>
          <div className="mt-2 text-2xl font-semibold text-white">{totalCapacity}</div>
        </div>
      </Card>

      {error ? <ErrorState message={error} onRetry={fetchData} /> : null}
      {loading ? <LoadingState label="Cargando reservas de restaurante..." /> : null}

      {!loading ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_360px]">
          <Card className="p-0">
            <div className="border-b border-slate-800 px-6 py-4">
              <SectionTitle title="Reservas" subtitle="Las reservas futuras aparecen por orden cronológico." />
            </div>
            {reservations.length === 0 ? (
              <div className="p-6">
                <EmptyState title="Sin reservas" description="No hay reservas para la fecha seleccionada." />
              </div>
            ) : (
              <table className="min-w-full divide-y divide-slate-800">
                <thead className="bg-slate-950">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Cliente</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Fecha</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Comensales</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 bg-slate-900">
                  {reservations.map((reservation) => (
                    <tr key={reservation.id} className="hover:bg-slate-800/40">
                      <td className="px-6 py-4 text-sm">
                        <div className="font-medium text-white">{reservation.client_name}</div>
                        <div className="text-slate-400">{reservation.client_phone}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-300">{formatDate(reservation.date)} · {reservation.time}</td>
                      <td className="px-6 py-4 text-sm text-slate-300">{reservation.party_size}</td>
                      <td className="px-6 py-4 text-sm"><StatusBadge status={reservation.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          <Card>
            <SectionTitle title="Zonas" subtitle={`${zones.length} zonas configuradas`} />
            {zones.length === 0 ? (
              <EmptyState title="Sin zonas" description="Añade zonas de comedor para modelar la capacidad del local." />
            ) : (
              <div className="space-y-3">
                {zones.map((zone) => (
                  <div key={zone.id} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="rounded-md bg-brand-500/10 p-2 text-brand-400"><Utensils className="h-4 w-4" /></div>
                        <div>
                          <div className="font-medium text-white">{zone.name}</div>
                          <div className="text-sm text-slate-400">Capacidad: {zone.capacity}</div>
                        </div>
                      </div>
                      <StatusBadge status={zone.is_active === false ? 'failed' : 'active'} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      ) : null}

      {zoneModalOpen ? (
        <Modal title="Nueva zona" onClose={() => setZoneModalOpen(false)} footer={<ModalFormActions submitLabel="Guardar zona" onClose={() => setZoneModalOpen(false)} submitting={submitting} />}>
          <SimpleForm onSubmit={createZone}>
            <label className="block text-sm text-slate-400">
              Nombre
              <input required value={zoneForm.name} onChange={(e) => setZoneForm({ ...zoneForm, name: e.target.value })} className={inputClassName} />
            </label>
            <label className="block text-sm text-slate-400">
              Capacidad
              <input type="number" min="1" value={zoneForm.capacity} onChange={(e) => setZoneForm({ ...zoneForm, capacity: Number(e.target.value) })} className={inputClassName} />
            </label>
          </SimpleForm>
        </Modal>
      ) : null}
    </div>
  );
}
