import { useEffect, useState } from 'react';
import { Calendar, Plus } from 'lucide-react';
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
  formatError,
  inputClassName,
  pluginRoutePath,
  primaryButtonClassName,
} from './shared';

type Shift = {
  id: number;
  professional_id: number;
  professional_name?: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
};

type Professional = {
  id: number;
  name: string;
};

type Agenda = {
  date: string;
  is_off: boolean;
  reason?: string;
  shifts?: Shift[];
  appointments: Array<{ id: number; client_name: string; start_time: string; status: string }>;
};

const shiftInitial = { professional_id: '', day_of_week: 0, start_time: '09:00', end_time: '18:00' };
const overrideInitial = { professional_id: '', date: '', is_off: false, start_time: '', end_time: '', reason: '' };
const dayLabels = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

export default function ShiftViewPage() {
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [selectedProfessional, setSelectedProfessional] = useState('');
  const [agendaDate, setAgendaDate] = useState('');
  const [agenda, setAgenda] = useState<Agenda | null>(null);
  const [loading, setLoading] = useState(true);
  const [agendaLoading, setAgendaLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shiftModalOpen, setShiftModalOpen] = useState(false);
  const [overrideModalOpen, setOverrideModalOpen] = useState(false);
  const [shiftForm, setShiftForm] = useState(shiftInitial);
  const [overrideForm, setOverrideForm] = useState(overrideInitial);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [shiftsRes, professionalsRes] = await Promise.all([
        api.get(pluginRoutePath('shifts/10')),
        api.get('/chatbot/dashboard/10/bookings/professionals'),
      ]);
      setShifts(shiftsRes.data);
      setProfessionals(professionalsRes.data);
      const nextProfessional = selectedProfessional || String(professionalsRes.data[0]?.id || '');
      setSelectedProfessional(nextProfessional);
      setShiftForm((current) => ({ ...current, professional_id: nextProfessional }));
      setOverrideForm((current) => ({ ...current, professional_id: nextProfessional }));
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  const fetchAgenda = async () => {
    if (!selectedProfessional || !agendaDate) return;
    setAgendaLoading(true);
    try {
      const response = await api.get(pluginRoutePath(`shifts/agenda/10/${selectedProfessional}`), { params: { date_str: agendaDate } });
      setAgenda(response.data);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setAgendaLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    fetchAgenda();
  }, [selectedProfessional, agendaDate]);

  const saveShift = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.post(pluginRoutePath('shifts/'), { instance_id: 10, ...shiftForm, professional_id: Number(shiftForm.professional_id), day_of_week: Number(shiftForm.day_of_week) });
      setShiftModalOpen(false);
      setShiftForm((current) => ({ ...shiftInitial, professional_id: current.professional_id }));
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const saveOverride = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.post(pluginRoutePath('shifts/overrides'), { instance_id: 10, ...overrideForm, professional_id: Number(overrideForm.professional_id) });
      setOverrideModalOpen(false);
      setOverrideForm((current) => ({ ...overrideInitial, professional_id: current.professional_id }));
      await fetchAgenda();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const groupedShifts = shifts.reduce<Record<string, Shift[]>>((acc, shift) => {
    const key = shift.professional_name || `Profesional ${shift.professional_id}`;
    acc[key] = acc[key] || [];
    acc[key].push(shift);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <PageHeader
        title="ShiftView"
        description="Consulta turnos semanales por profesional y aplica overrides sobre días concretos."
        action={
          <div className="flex gap-2">
            <button type="button" onClick={() => setShiftModalOpen(true)} className={primaryButtonClassName}><Plus className="mr-2 h-4 w-4" />Nuevo turno</button>
            <button type="button" onClick={() => setOverrideModalOpen(true)} className={primaryButtonClassName}><Calendar className="mr-2 h-4 w-4" />Nuevo override</button>
          </div>
        }
      />

      <Card className="grid gap-4 md:grid-cols-2">
        <label className="block text-sm text-slate-400">
          Profesional
          <select value={selectedProfessional} onChange={(e) => { setSelectedProfessional(e.target.value); setShiftForm({ ...shiftForm, professional_id: e.target.value }); setOverrideForm({ ...overrideForm, professional_id: e.target.value }); }} className={inputClassName}>
            <option value="">Selecciona...</option>
            {professionals.map((professional) => <option key={professional.id} value={professional.id}>{professional.name}</option>)}
          </select>
        </label>
        <label className="block text-sm text-slate-400">
          Día para agenda
          <input type="date" value={agendaDate} onChange={(e) => setAgendaDate(e.target.value)} className={inputClassName} />
        </label>
      </Card>

      {error ? <ErrorState message={error} onRetry={fetchData} /> : null}
      {loading ? <LoadingState label="Cargando turnos..." /> : null}

      {!loading ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_420px]">
          <Card>
            <SectionTitle title="Turnos semanales" subtitle="Vista agrupada por profesional." />
            {Object.keys(groupedShifts).length === 0 ? (
              <EmptyState title="Sin turnos" description="Configura al menos un turno para empezar a visualizar agendas." />
            ) : (
              <div className="space-y-4">
                {Object.entries(groupedShifts).map(([professional, items]) => (
                  <div key={professional} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                    <div className="mb-3 font-medium text-white">{professional}</div>
                    <div className="grid gap-2 md:grid-cols-2">
                      {items.map((shift) => (
                        <div key={shift.id} className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-300">
                          {dayLabels[shift.day_of_week]} · {shift.start_time} - {shift.end_time}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card>
            <SectionTitle title="Agenda diaria" subtitle={agendaDate || 'Selecciona una fecha'} />
            {!selectedProfessional || !agendaDate ? (
              <EmptyState title="Selecciona profesional y fecha" description="La agenda diaria requiere ambos filtros." />
            ) : agendaLoading ? (
              <LoadingState label="Cargando agenda..." />
            ) : agenda?.is_off ? (
              <EmptyState title="Día marcado como no laborable" description={agenda.reason || 'Hay un override que bloquea este día.'} />
            ) : (
              <div className="space-y-4">
                <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                  <div className="text-sm text-slate-400">Turnos activos</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {agenda?.shifts?.map((shift) => (
                      <span key={shift.id} className="rounded-full bg-slate-800 px-3 py-1 text-sm text-slate-200">{shift.start_time} - {shift.end_time}</span>
                    ))}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                  <div className="mb-3 text-sm text-slate-400">Citas del día</div>
                  {agenda?.appointments?.length ? (
                    <div className="space-y-2">
                      {agenda.appointments.map((appointment) => (
                        <div key={appointment.id} className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm">
                          <span className="text-white">{appointment.client_name}</span>
                          <span className="text-slate-400">{appointment.start_time} · {appointment.status}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState title="Sin citas" description="No hay reservas asignadas para esta fecha." />
                  )}
                </div>
              </div>
            )}
          </Card>
        </div>
      ) : null}

      {shiftModalOpen ? (
        <Modal title="Nuevo turno" onClose={() => setShiftModalOpen(false)} footer={<ModalFormActions submitLabel="Guardar turno" onClose={() => setShiftModalOpen(false)} submitting={submitting} />}>
          <SimpleForm onSubmit={saveShift}>
            <label className="block text-sm text-slate-400">
              Profesional
              <select value={shiftForm.professional_id} onChange={(e) => setShiftForm({ ...shiftForm, professional_id: e.target.value })} className={inputClassName}>
                {professionals.map((professional) => <option key={professional.id} value={professional.id}>{professional.name}</option>)}
              </select>
            </label>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <label className="block text-sm text-slate-400">
                Día
                <select value={shiftForm.day_of_week} onChange={(e) => setShiftForm({ ...shiftForm, day_of_week: Number(e.target.value) })} className={inputClassName}>
                  {dayLabels.map((day, index) => <option key={day} value={index}>{day}</option>)}
                </select>
              </label>
              <label className="block text-sm text-slate-400">
                Inicio
                <input type="time" value={shiftForm.start_time} onChange={(e) => setShiftForm({ ...shiftForm, start_time: e.target.value })} className={inputClassName} />
              </label>
              <label className="block text-sm text-slate-400">
                Fin
                <input type="time" value={shiftForm.end_time} onChange={(e) => setShiftForm({ ...shiftForm, end_time: e.target.value })} className={inputClassName} />
              </label>
            </div>
          </SimpleForm>
        </Modal>
      ) : null}

      {overrideModalOpen ? (
        <Modal title="Nuevo override" onClose={() => setOverrideModalOpen(false)} footer={<ModalFormActions submitLabel="Guardar override" onClose={() => setOverrideModalOpen(false)} submitting={submitting} />}>
          <SimpleForm onSubmit={saveOverride}>
            <label className="block text-sm text-slate-400">
              Profesional
              <select value={overrideForm.professional_id} onChange={(e) => setOverrideForm({ ...overrideForm, professional_id: e.target.value })} className={inputClassName}>
                {professionals.map((professional) => <option key={professional.id} value={professional.id}>{professional.name}</option>)}
              </select>
            </label>
            <label className="block text-sm text-slate-400">
              Fecha
              <input type="date" required value={overrideForm.date} onChange={(e) => setOverrideForm({ ...overrideForm, date: e.target.value })} className={inputClassName} />
            </label>
            <label className="flex items-center gap-3 rounded-md border border-slate-800 bg-slate-950 px-3 py-3 text-sm text-slate-300">
              <input type="checkbox" checked={overrideForm.is_off} onChange={(e) => setOverrideForm({ ...overrideForm, is_off: e.target.checked })} className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-brand-500" />
              Día libre completo
            </label>
            {!overrideForm.is_off ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <label className="block text-sm text-slate-400">
                  Inicio
                  <input type="time" value={overrideForm.start_time} onChange={(e) => setOverrideForm({ ...overrideForm, start_time: e.target.value })} className={inputClassName} />
                </label>
                <label className="block text-sm text-slate-400">
                  Fin
                  <input type="time" value={overrideForm.end_time} onChange={(e) => setOverrideForm({ ...overrideForm, end_time: e.target.value })} className={inputClassName} />
                </label>
              </div>
            ) : null}
            <label className="block text-sm text-slate-400">
              Motivo
              <input value={overrideForm.reason} onChange={(e) => setOverrideForm({ ...overrideForm, reason: e.target.value })} className={inputClassName} />
            </label>
          </SimpleForm>
        </Modal>
      ) : null}
    </div>
  );
}
