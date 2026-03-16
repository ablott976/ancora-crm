import { useEffect, useState } from 'react';
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Pencil,
  Plus,
  Trash2,
  UserX,
  Utensils,
  XCircle,
} from 'lucide-react';
import api from '../../api/client';
import {
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Modal,
  ModalFormActions,
  PageHeader,
  PLUGIN_INSTANCE_ID,
  SectionTitle,
  SimpleForm,
  StatusBadge,
  dashboardPluginPath,
  formatDate,
  formatError,
  inputClassName,
  primaryButtonClassName,
  secondaryButtonClassName,
  selectClassName,
  textareaClassName,
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
  allergies?: string | null;
  zone_id?: number | null;
  table_id?: number | null;
  zone_name?: string | null;
  table_number?: string | null;
};

type Zone = {
  id: number;
  name: string;
  capacity: number;
  is_active: boolean;
  active_tables?: number;
  active_table_seats?: number;
};

type Table = {
  id: number;
  zone_id: number;
  table_number: string;
  seats: number;
  is_active: boolean;
};

const reservationInitial = {
  client_name: '',
  client_phone: '',
  date: '',
  time: '',
  party_size: 2,
  zone_id: '',
  table_id: '',
  notes: '',
  allergies: '',
};

const zoneInitial = { name: '', capacity: 20 };
const tableInitial = { table_number: '', seats: 4 };

export default function RestaurantBookingsPage() {
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [tablesByZone, setTablesByZone] = useState<Record<number, Table[]>>({});
  const [expandedZones, setExpandedZones] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [dateFilter, setDateFilter] = useState('');

  const [reservationModalOpen, setReservationModalOpen] = useState(false);
  const [editingReservation, setEditingReservation] = useState<Reservation | null>(null);
  const [reservationForm, setReservationForm] = useState(reservationInitial);

  const [zoneModalOpen, setZoneModalOpen] = useState(false);
  const [editingZone, setEditingZone] = useState<Zone | null>(null);
  const [zoneForm, setZoneForm] = useState(zoneInitial);

  const [tableModalOpen, setTableModalOpen] = useState(false);
  const [editingTable, setEditingTable] = useState<Table | null>(null);
  const [tableZoneId, setTableZoneId] = useState<number | null>(null);
  const [tableForm, setTableForm] = useState(tableInitial);

  const activeZones = zones.filter((zone) => zone.is_active !== false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [reservationRes, zoneRes] = await Promise.all([
        api.get(dashboardPluginPath('restaurant', '/reservations'), {
          params: { date_filter: dateFilter || undefined },
        }),
        api.get(dashboardPluginPath('restaurant', '/zones')),
      ]);

      const zoneList: Zone[] = zoneRes.data;
      setReservations(reservationRes.data);
      setZones(zoneList);

      const tableEntries = await Promise.all(
        zoneList.map(async (zone) => {
          const response = await api.get(dashboardPluginPath('restaurant', `/zones/${zone.id}/tables`));
          return [zone.id, response.data as Table[]] as const;
        })
      );
      setTablesByZone(Object.fromEntries(tableEntries));
      setExpandedZones((current) => current.filter((zoneId) => zoneList.some((zone) => zone.id === zoneId)));
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [dateFilter]);

  const resetReservationModal = () => {
    setEditingReservation(null);
    setReservationForm(reservationInitial);
    setReservationModalOpen(false);
  };

  const resetZoneModal = () => {
    setEditingZone(null);
    setZoneForm(zoneInitial);
    setZoneModalOpen(false);
  };

  const resetTableModal = () => {
    setEditingTable(null);
    setTableZoneId(null);
    setTableForm(tableInitial);
    setTableModalOpen(false);
  };

  const openCreateReservation = () => {
    setEditingReservation(null);
    setReservationForm(reservationInitial);
    setReservationModalOpen(true);
  };

  const openEditReservation = (reservation: Reservation) => {
    setEditingReservation(reservation);
    setReservationForm({
      client_name: reservation.client_name,
      client_phone: reservation.client_phone,
      date: reservation.date,
      time: reservation.time,
      party_size: reservation.party_size,
      zone_id: reservation.zone_id ? String(reservation.zone_id) : '',
      table_id: reservation.table_id ? String(reservation.table_id) : '',
      notes: reservation.notes ?? '',
      allergies: reservation.allergies ?? '',
    });
    setReservationModalOpen(true);
  };

  const openCreateZone = () => {
    setEditingZone(null);
    setZoneForm(zoneInitial);
    setZoneModalOpen(true);
  };

  const openEditZone = (zone: Zone) => {
    setEditingZone(zone);
    setZoneForm({ name: zone.name, capacity: zone.capacity });
    setZoneModalOpen(true);
  };

  const openCreateTable = (zoneId: number) => {
    setEditingTable(null);
    setTableZoneId(zoneId);
    setTableForm(tableInitial);
    setTableModalOpen(true);
  };

  const openEditTable = (table: Table) => {
    setEditingTable(table);
    setTableZoneId(table.zone_id);
    setTableForm({ table_number: table.table_number, seats: table.seats });
    setTableModalOpen(true);
  };

  const submitReservation = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        ...reservationForm,
        party_size: Number(reservationForm.party_size),
        zone_id: reservationForm.zone_id ? Number(reservationForm.zone_id) : null,
        table_id: reservationForm.table_id ? Number(reservationForm.table_id) : null,
        notes: reservationForm.notes || null,
        allergies: reservationForm.allergies || null,
      };
      if (editingReservation) {
        await api.put(dashboardPluginPath('restaurant', `/reservations/${editingReservation.id}`), payload);
      } else {
        await api.post(dashboardPluginPath('restaurant', '/reservations'), payload);
      }
      resetReservationModal();
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const submitZone = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload = { ...zoneForm, capacity: Number(zoneForm.capacity) };
      if (editingZone) {
        await api.put(dashboardPluginPath('restaurant', `/zones/${editingZone.id}`), payload);
      } else {
        await api.post(dashboardPluginPath('restaurant', '/zones'), payload);
      }
      resetZoneModal();
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const submitTable = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!tableZoneId) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload = { ...tableForm, seats: Number(tableForm.seats) };
      if (editingTable) {
        await api.put(dashboardPluginPath('restaurant', `/tables/${editingTable.id}`), payload);
      } else {
        await api.post(dashboardPluginPath('restaurant', `/zones/${tableZoneId}/tables`), payload);
      }
      resetTableModal();
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const runReservationAction = async (reservationId: number, action: 'confirm' | 'cancel' | 'noshow') => {
    setSubmitting(true);
    setError(null);
    try {
      await api.post(dashboardPluginPath('restaurant', `/reservations/${reservationId}/${action}`));
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const removeZone = async (zoneId: number) => {
    setSubmitting(true);
    setError(null);
    try {
      await api.delete(dashboardPluginPath('restaurant', `/zones/${zoneId}`));
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const removeTable = async (tableId: number) => {
    setSubmitting(true);
    setError(null);
    try {
      await api.delete(dashboardPluginPath('restaurant', `/tables/${tableId}`));
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const toggleZone = (zoneId: number) => {
    setExpandedZones((current) =>
      current.includes(zoneId) ? current.filter((value) => value !== zoneId) : [...current, zoneId]
    );
  };

  const selectedZoneId = reservationForm.zone_id ? Number(reservationForm.zone_id) : null;
  const selectableTables = selectedZoneId ? (tablesByZone[selectedZoneId] ?? []).filter((table) => table.is_active !== false) : [];
  const totalCapacity = activeZones.reduce((sum, zone) => sum + zone.capacity, 0);
  const totalTables = activeZones.reduce((sum, zone) => sum + (zone.active_tables ?? 0), 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Restaurant Bookings"
        description="Gestiona reservas, zonas y mesas desde el dashboard del restaurante."
        action={
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={openCreateReservation} className={primaryButtonClassName}>
              <Plus className="mr-2 h-4 w-4" />
              Nueva reserva
            </button>
            <button type="button" onClick={openCreateZone} className={secondaryButtonClassName}>
              <Utensils className="mr-2 h-4 w-4" />
              Nueva zona
            </button>
          </div>
        }
      />

      <Card className="grid gap-4 md:grid-cols-[1fr_220px_220px]">
        <label className="block text-sm text-slate-400">
          Filtrar reservas por fecha
          <input type="date" value={dateFilter} onChange={(e) => setDateFilter(e.target.value)} className={inputClassName} />
        </label>
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
          <div className="text-sm text-slate-400">Capacidad activa</div>
          <div className="mt-2 text-2xl font-semibold text-white">{totalCapacity}</div>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
          <div className="text-sm text-slate-400">Mesas activas</div>
          <div className="mt-2 text-2xl font-semibold text-white">{totalTables}</div>
        </div>
      </Card>

      {error ? <ErrorState message={error} onRetry={fetchData} /> : null}
      {loading ? <LoadingState label="Cargando reservas de restaurante..." /> : null}

      {!loading ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_380px]">
          <Card className="p-0">
            <div className="border-b border-slate-800 px-6 py-4">
              <SectionTitle title="Reservas" subtitle="Crea, edita y cambia el estado de cada reserva." />
            </div>
            {reservations.length === 0 ? (
              <div className="p-6">
                <EmptyState title="Sin reservas" description="No hay reservas para la fecha seleccionada." />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-800">
                  <thead className="bg-slate-950">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Cliente</th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Fecha</th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Zona</th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Estado</th>
                      <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-400">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 bg-slate-900">
                    {reservations.map((reservation) => (
                      <tr key={reservation.id} className="align-top hover:bg-slate-800/40">
                        <td className="px-6 py-4 text-sm">
                          <div className="font-medium text-white">{reservation.client_name}</div>
                          <div className="text-slate-400">{reservation.client_phone}</div>
                          <div className="mt-1 text-slate-500">{reservation.party_size} comensales</div>
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-300">
                          <div>{formatDate(reservation.date)}</div>
                          <div className="text-slate-400">{reservation.time}</div>
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-300">
                          <div>{reservation.zone_name || 'Sin zona'}</div>
                          <div className="text-slate-400">{reservation.table_number ? `Mesa ${reservation.table_number}` : 'Sin mesa'}</div>
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <StatusBadge status={reservation.status} />
                          {reservation.notes ? <div className="mt-2 max-w-xs text-xs text-slate-400">{reservation.notes}</div> : null}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex justify-end gap-2">
                            <button type="button" onClick={() => openEditReservation(reservation)} className={secondaryButtonClassName}>
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button type="button" onClick={() => runReservationAction(reservation.id, 'confirm')} className={secondaryButtonClassName} disabled={submitting || reservation.status !== 'pendiente'}>
                              <CheckCircle2 className="h-4 w-4" />
                            </button>
                            <button type="button" onClick={() => runReservationAction(reservation.id, 'cancel')} className={secondaryButtonClassName} disabled={submitting || !['pendiente', 'confirmada'].includes(reservation.status)}>
                              <XCircle className="h-4 w-4" />
                            </button>
                            <button type="button" onClick={() => runReservationAction(reservation.id, 'noshow')} className={secondaryButtonClassName} disabled={submitting || reservation.status !== 'confirmada'}>
                              <UserX className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card>
            <SectionTitle title="Zonas y mesas" subtitle={`${zones.length} zonas configuradas`} />
            {zones.length === 0 ? (
              <EmptyState title="Sin zonas" description="Añade zonas de comedor para modelar la capacidad del local." />
            ) : (
              <div className="space-y-3">
                {zones.map((zone) => {
                  const expanded = expandedZones.includes(zone.id);
                  const tables = tablesByZone[zone.id] ?? [];
                  return (
                    <div key={zone.id} className="rounded-lg border border-slate-800 bg-slate-950">
                      <div className="flex items-center justify-between gap-3 p-4">
                        <button type="button" onClick={() => toggleZone(zone.id)} className="flex min-w-0 flex-1 items-center gap-3 text-left">
                          {expanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                          <div className="rounded-md bg-brand-500/10 p-2 text-brand-400">
                            <Utensils className="h-4 w-4" />
                          </div>
                          <div className="min-w-0">
                            <div className="font-medium text-white">{zone.name}</div>
                            <div className="text-sm text-slate-400">
                              Capacidad {zone.capacity} · {zone.active_tables ?? 0} mesas activas
                            </div>
                          </div>
                        </button>
                        <div className="flex items-center gap-2">
                          <StatusBadge status={zone.is_active === false ? 'inactive' : 'active'} />
                          <button type="button" onClick={() => openEditZone(zone)} className={secondaryButtonClassName}>
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button type="button" onClick={() => removeZone(zone.id)} className={secondaryButtonClassName} disabled={submitting || zone.is_active === false}>
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                      {expanded ? (
                        <div className="border-t border-slate-800 p-4">
                          <div className="mb-3 flex items-center justify-between">
                            <div className="text-sm text-slate-400">
                              {tables.length} mesas registradas · {zone.active_table_seats ?? 0} plazas activas
                            </div>
                            <button type="button" onClick={() => openCreateTable(zone.id)} className={secondaryButtonClassName}>
                              <Plus className="mr-2 h-4 w-4" />
                              Nueva mesa
                            </button>
                          </div>
                          {tables.length === 0 ? (
                            <EmptyState title="Sin mesas" description="Esta zona aún no tiene mesas configuradas." />
                          ) : (
                            <div className="space-y-2">
                              {tables.map((table) => (
                                <div key={table.id} className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-900 px-3 py-2">
                                  <div>
                                    <div className="text-sm font-medium text-white">Mesa {table.table_number}</div>
                                    <div className="text-xs text-slate-400">{table.seats} plazas</div>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <StatusBadge status={table.is_active === false ? 'inactive' : 'active'} />
                                    <button type="button" onClick={() => openEditTable(table)} className={secondaryButtonClassName}>
                                      <Pencil className="h-4 w-4" />
                                    </button>
                                    <button type="button" onClick={() => removeTable(table.id)} className={secondaryButtonClassName} disabled={submitting || table.is_active === false}>
                                      <Trash2 className="h-4 w-4" />
                                    </button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>
      ) : null}

      {reservationModalOpen ? (
        <Modal
          title={editingReservation ? 'Editar reserva' : 'Nueva reserva'}
          onClose={resetReservationModal}
          footer={<ModalFormActions submitLabel={editingReservation ? 'Guardar cambios' : 'Crear reserva'} onClose={resetReservationModal} submitting={submitting} />}
          width="max-w-3xl"
        >
          <SimpleForm onSubmit={submitReservation} className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm text-slate-400">
              Nombre
              <input required value={reservationForm.client_name} onChange={(e) => setReservationForm({ ...reservationForm, client_name: e.target.value })} className={inputClassName} />
            </label>
            <label className="block text-sm text-slate-400">
              Teléfono
              <input required value={reservationForm.client_phone} onChange={(e) => setReservationForm({ ...reservationForm, client_phone: e.target.value })} className={inputClassName} />
            </label>
            <label className="block text-sm text-slate-400">
              Fecha
              <input required type="date" value={reservationForm.date} onChange={(e) => setReservationForm({ ...reservationForm, date: e.target.value })} className={inputClassName} />
            </label>
            <label className="block text-sm text-slate-400">
              Hora
              <input required type="time" value={reservationForm.time} onChange={(e) => setReservationForm({ ...reservationForm, time: e.target.value })} className={inputClassName} />
            </label>
            <label className="block text-sm text-slate-400">
              Comensales
              <input type="number" min="1" value={reservationForm.party_size} onChange={(e) => setReservationForm({ ...reservationForm, party_size: Number(e.target.value) })} className={inputClassName} />
            </label>
            <label className="block text-sm text-slate-400">
              Zona
              <select
                value={reservationForm.zone_id}
                onChange={(e) => setReservationForm({ ...reservationForm, zone_id: e.target.value, table_id: '' })}
                className={selectClassName}
              >
                <option value="">Sin zona concreta</option>
                {activeZones.map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm text-slate-400">
              Mesa
              <select value={reservationForm.table_id} onChange={(e) => setReservationForm({ ...reservationForm, table_id: e.target.value })} className={selectClassName} disabled={!selectedZoneId}>
                <option value="">Sin mesa concreta</option>
                {selectableTables.map((table) => (
                  <option key={table.id} value={table.id}>
                    Mesa {table.table_number} · {table.seats} plazas
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm text-slate-400 md:col-span-2">
              Notas
              <textarea value={reservationForm.notes} onChange={(e) => setReservationForm({ ...reservationForm, notes: e.target.value })} className={textareaClassName} />
            </label>
            <label className="block text-sm text-slate-400 md:col-span-2">
              Alergias
              <textarea value={reservationForm.allergies} onChange={(e) => setReservationForm({ ...reservationForm, allergies: e.target.value })} className={textareaClassName} />
            </label>
          </SimpleForm>
        </Modal>
      ) : null}

      {zoneModalOpen ? (
        <Modal
          title={editingZone ? 'Editar zona' : 'Nueva zona'}
          onClose={resetZoneModal}
          footer={<ModalFormActions submitLabel={editingZone ? 'Guardar zona' : 'Crear zona'} onClose={resetZoneModal} submitting={submitting} />}
        >
          <SimpleForm onSubmit={submitZone}>
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

      {tableModalOpen ? (
        <Modal
          title={editingTable ? 'Editar mesa' : 'Nueva mesa'}
          onClose={resetTableModal}
          footer={<ModalFormActions submitLabel={editingTable ? 'Guardar mesa' : 'Crear mesa'} onClose={resetTableModal} submitting={submitting} />}
        >
          <SimpleForm onSubmit={submitTable}>
            <label className="block text-sm text-slate-400">
              Zona
              <input value={zones.find((zone) => zone.id === tableZoneId)?.name ?? `Instancia ${PLUGIN_INSTANCE_ID}`} className={inputClassName} disabled />
            </label>
            <label className="block text-sm text-slate-400">
              Número o nombre de mesa
              <input required value={tableForm.table_number} onChange={(e) => setTableForm({ ...tableForm, table_number: e.target.value })} className={inputClassName} />
            </label>
            <label className="block text-sm text-slate-400">
              Plazas
              <input type="number" min="1" value={tableForm.seats} onChange={(e) => setTableForm({ ...tableForm, seats: Number(e.target.value) })} className={inputClassName} />
            </label>
          </SimpleForm>
        </Modal>
      ) : null}
    </div>
  );
}
