import { useEffect, useState } from 'react';
import { CalendarCheck, Plus } from 'lucide-react';
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
  primaryButtonClassName,
  textareaClassName,
} from './shared';

type Appointment = {
  id: number;
  client_name: string;
  client_phone: string;
  date: string;
  start_time: string;
  status: string;
  professional_name?: string;
  service_name?: string;
};

type Professional = {
  id: number;
  name: string;
  phone?: string | null;
  email?: string | null;
  services?: Array<{ id: number; name: string }>;
  is_active?: boolean;
};

type BookingService = {
  id: number;
  name: string;
  duration_minutes: number;
  description?: string | null;
  price?: number | null;
  is_active?: boolean;
};

const professionalInitial = { name: '', phone: '', email: '', service_ids: '' };
const serviceInitial = { name: '', duration_minutes: 60, description: '', price: '' };

export default function BookingsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [services, setServices] = useState<BookingService[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<'professional' | 'service' | null>(null);
  const [professionalForm, setProfessionalForm] = useState(professionalInitial);
  const [serviceForm, setServiceForm] = useState(serviceInitial);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [appointmentsRes, professionalsRes, servicesRes] = await Promise.all([
        api.get('/chatbot/dashboard/10/bookings/appointments'),
        api.get('/chatbot/dashboard/10/bookings/professionals'),
        api.get('/chatbot/dashboard/10/bookings/services'),
      ]);
      setAppointments(appointmentsRes.data);
      setProfessionals(professionalsRes.data);
      setServices(servicesRes.data);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const createProfessional = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/chatbot/dashboard/10/bookings/professionals', {
        name: professionalForm.name,
        phone: professionalForm.phone || null,
        email: professionalForm.email || null,
        service_ids: professionalForm.service_ids.split(',').map((item) => Number(item.trim())).filter(Boolean),
      });
      setModal(null);
      setProfessionalForm(professionalInitial);
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const createService = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/chatbot/dashboard/10/bookings/services', {
        name: serviceForm.name,
        duration_minutes: Number(serviceForm.duration_minutes),
        description: serviceForm.description || null,
        price: serviceForm.price ? Number(serviceForm.price) : null,
      });
      setModal(null);
      setServiceForm(serviceInitial);
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Bookings"
        description="Supervisa citas y mantén actualizados profesionales y servicios disponibles."
        action={
          <div className="flex gap-2">
            <button type="button" onClick={() => setModal('professional')} className={primaryButtonClassName}><Plus className="mr-2 h-4 w-4" />Profesional</button>
            <button type="button" onClick={() => setModal('service')} className={primaryButtonClassName}><Plus className="mr-2 h-4 w-4" />Servicio</button>
          </div>
        }
      />

      {error ? <ErrorState message={error} onRetry={fetchData} /> : null}
      {loading ? <LoadingState label="Cargando bookings..." /> : null}

      {!loading ? (
        <>
          <Card className="p-0">
            <div className="border-b border-slate-800 px-6 py-4">
              <SectionTitle title="Citas" subtitle={`${appointments.length} citas registradas`} />
            </div>
            {appointments.length === 0 ? (
              <div className="p-6"><EmptyState title="Sin citas" description="Las reservas creadas por chatbot o dashboard aparecerán aquí." /></div>
            ) : (
              <table className="min-w-full divide-y divide-slate-800">
                <thead className="bg-slate-950">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Cliente</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Fecha</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Profesional</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Servicio</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 bg-slate-900">
                  {appointments.map((appointment) => (
                    <tr key={appointment.id} className="hover:bg-slate-800/40">
                      <td className="px-6 py-4 text-sm">
                        <div className="font-medium text-white">{appointment.client_name}</div>
                        <div className="text-slate-400">{appointment.client_phone}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-300">{formatDate(appointment.date)} · {appointment.start_time}</td>
                      <td className="px-6 py-4 text-sm text-slate-300">{appointment.professional_name || '-'}</td>
                      <td className="px-6 py-4 text-sm text-slate-300">{appointment.service_name || '-'}</td>
                      <td className="px-6 py-4 text-sm"><StatusBadge status={appointment.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          <div className="grid gap-6 xl:grid-cols-2">
            <Card>
              <SectionTitle title="Profesionales" subtitle={`${professionals.length} configurados`} />
              {professionals.length === 0 ? (
                <EmptyState title="Sin profesionales" description="Añade profesionales para abrir agenda." />
              ) : (
                <div className="space-y-3">
                  {professionals.map((professional) => (
                    <div key={professional.id} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="font-medium text-white">{professional.name}</div>
                          <div className="text-sm text-slate-400">{professional.phone || 'Sin teléfono'} · {professional.email || 'Sin email'}</div>
                          <div className="mt-2 text-xs text-slate-500">{professional.services?.map((service) => service.name).join(', ') || 'Sin servicios asignados'}</div>
                        </div>
                        <StatusBadge status={professional.is_active === false ? 'failed' : 'active'} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card>
              <SectionTitle title="Servicios" subtitle={`${services.length} servicios disponibles`} />
              {services.length === 0 ? (
                <EmptyState title="Sin servicios" description="Añade servicios para que los profesionales puedan reservarlos." />
              ) : (
                <div className="space-y-3">
                  {services.map((service) => (
                    <div key={service.id} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-3">
                            <div className="rounded-md bg-brand-500/10 p-2 text-brand-400"><CalendarCheck className="h-4 w-4" /></div>
                            <div className="font-medium text-white">{service.name}</div>
                          </div>
                          <div className="mt-2 text-sm text-slate-400">{service.duration_minutes} min · {service.price != null ? `${service.price} €` : 'Sin precio'}</div>
                          {service.description ? <p className="mt-2 text-sm text-slate-300">{service.description}</p> : null}
                        </div>
                        <StatusBadge status={service.is_active === false ? 'failed' : 'active'} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </>
      ) : null}

      {modal === 'professional' ? (
        <Modal title="Nuevo profesional" onClose={() => setModal(null)} footer={<ModalFormActions submitLabel="Guardar profesional" onClose={() => setModal(null)} submitting={submitting} />}>
          <SimpleForm onSubmit={createProfessional}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block text-sm text-slate-400">
                Nombre
                <input required value={professionalForm.name} onChange={(e) => setProfessionalForm({ ...professionalForm, name: e.target.value })} className={inputClassName} />
              </label>
              <label className="block text-sm text-slate-400">
                Teléfono
                <input value={professionalForm.phone} onChange={(e) => setProfessionalForm({ ...professionalForm, phone: e.target.value })} className={inputClassName} />
              </label>
            </div>
            <label className="block text-sm text-slate-400">
              Email
              <input value={professionalForm.email} onChange={(e) => setProfessionalForm({ ...professionalForm, email: e.target.value })} className={inputClassName} />
            </label>
            <label className="block text-sm text-slate-400">
              IDs de servicios
              <input value={professionalForm.service_ids} onChange={(e) => setProfessionalForm({ ...professionalForm, service_ids: e.target.value })} className={inputClassName} placeholder="1, 2, 3" />
            </label>
          </SimpleForm>
        </Modal>
      ) : null}

      {modal === 'service' ? (
        <Modal title="Nuevo servicio" onClose={() => setModal(null)} footer={<ModalFormActions submitLabel="Guardar servicio" onClose={() => setModal(null)} submitting={submitting} />}>
          <SimpleForm onSubmit={createService}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block text-sm text-slate-400">
                Nombre
                <input required value={serviceForm.name} onChange={(e) => setServiceForm({ ...serviceForm, name: e.target.value })} className={inputClassName} />
              </label>
              <label className="block text-sm text-slate-400">
                Duración
                <input type="number" value={serviceForm.duration_minutes} onChange={(e) => setServiceForm({ ...serviceForm, duration_minutes: Number(e.target.value) })} className={inputClassName} />
              </label>
            </div>
            <label className="block text-sm text-slate-400">
              Descripción
              <textarea value={serviceForm.description} onChange={(e) => setServiceForm({ ...serviceForm, description: e.target.value })} className={textareaClassName} />
            </label>
            <label className="block text-sm text-slate-400">
              Precio
              <input type="number" step="0.01" value={serviceForm.price} onChange={(e) => setServiceForm({ ...serviceForm, price: e.target.value })} className={inputClassName} />
            </label>
          </SimpleForm>
        </Modal>
      ) : null}
    </div>
  );
}
