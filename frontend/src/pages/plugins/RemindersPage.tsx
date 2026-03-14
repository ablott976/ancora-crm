import { useEffect, useState } from 'react';
import { Bell, Plus } from 'lucide-react';
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
  formatDateTime,
  formatError,
  inputClassName,
  primaryButtonClassName,
  textareaClassName,
} from './shared';

type Template = {
  id: number;
  name: string;
  type: string;
  hours_before: number;
  template_text: string;
  send_to: string;
  is_active: boolean;
};

type LogItem = {
  id: number;
  template_name?: string | null;
  recipient_phone: string;
  status: string;
  message_text: string;
  sent_at?: string | null;
  created_at: string;
};

const templateInitial = {
  name: '',
  type: 'pre',
  hours_before: 24,
  template_text: '',
  send_to: 'client',
};

export default function RemindersPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [logItems, setLogItems] = useState<LogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(templateInitial);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [templatesRes, logRes] = await Promise.all([
        api.get('/chatbot/dashboard/10/reminders/templates'),
        api.get('/chatbot/dashboard/10/reminders/log'),
      ]);
      setTemplates(templatesRes.data);
      setLogItems(logRes.data);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const createTemplate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/chatbot/dashboard/10/reminders/templates', {
        ...form,
        hours_before: Number(form.hours_before),
      });
      setModalOpen(false);
      setForm(templateInitial);
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const triggerCheck = async () => {
    try {
      await api.post('/chatbot/dashboard/10/reminders/check');
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reminders"
        description="Gestiona plantillas de recordatorio y revisa el log de envíos generados por el sistema."
        action={
          <div className="flex gap-2">
            <button type="button" onClick={triggerCheck} className={primaryButtonClassName}>Ejecutar check</button>
            <button type="button" onClick={() => setModalOpen(true)} className={primaryButtonClassName}><Plus className="mr-2 h-4 w-4" />Nueva plantilla</button>
          </div>
        }
      />

      {error ? <ErrorState message={error} onRetry={fetchData} /> : null}
      {loading ? <LoadingState label="Cargando recordatorios..." /> : null}

      {!loading ? (
        <>
          <Card>
            <SectionTitle title="Plantillas" subtitle={`${templates.length} plantillas configuradas`} />
            {templates.length === 0 ? (
              <EmptyState title="Sin plantillas" description="Crea una plantilla para activar recordatorios previos o posteriores." />
            ) : (
              <div className="grid gap-4 lg:grid-cols-2">
                {templates.map((template) => (
                  <div key={template.id} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-3">
                          <div className="rounded-md bg-brand-500/10 p-2 text-brand-400"><Bell className="h-4 w-4" /></div>
                          <div className="font-medium text-white">{template.name}</div>
                        </div>
                        <div className="mt-2 text-sm text-slate-400">{template.type} · {template.hours_before}h antes · Destinatario: {template.send_to}</div>
                        <p className="mt-3 text-sm text-slate-300">{template.template_text}</p>
                      </div>
                      <StatusBadge status={template.is_active ? 'active' : 'failed'} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card className="p-0">
            <div className="border-b border-slate-800 px-6 py-4">
              <SectionTitle title="Log de envíos" subtitle={`${logItems.length} eventos recientes`} />
            </div>
            {logItems.length === 0 ? (
              <div className="p-6"><EmptyState title="Sin log" description="Cuando se creen recordatorios aparecerán aquí." /></div>
            ) : (
              <table className="min-w-full divide-y divide-slate-800">
                <thead className="bg-slate-950">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Plantilla</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Destinatario</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Estado</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Fechas</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 bg-slate-900">
                  {logItems.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-800/40">
                      <td className="px-6 py-4 text-sm">
                        <div className="font-medium text-white">{item.template_name || 'Sin plantilla'}</div>
                        <p className="mt-1 max-w-md text-xs text-slate-400">{item.message_text}</p>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-300">{item.recipient_phone}</td>
                      <td className="px-6 py-4 text-sm"><StatusBadge status={item.status} /></td>
                      <td className="px-6 py-4 text-sm text-slate-300">
                        <div>Creado: {formatDateTime(item.created_at)}</div>
                        <div>Enviado: {formatDateTime(item.sent_at)}</div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      ) : null}

      {modalOpen ? (
        <Modal title="Nueva plantilla de recordatorio" onClose={() => setModalOpen(false)} footer={<ModalFormActions submitLabel="Guardar plantilla" onClose={() => setModalOpen(false)} submitting={submitting} />}>
          <SimpleForm onSubmit={createTemplate}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block text-sm text-slate-400">
                Nombre
                <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={inputClassName} />
              </label>
              <label className="block text-sm text-slate-400">
                Tipo
                <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className={inputClassName}>
                  <option value="pre">Pre</option>
                  <option value="post">Post</option>
                </select>
              </label>
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block text-sm text-slate-400">
                Horas antes
                <input type="number" value={form.hours_before} onChange={(e) => setForm({ ...form, hours_before: Number(e.target.value) })} className={inputClassName} />
              </label>
              <label className="block text-sm text-slate-400">
                Destinatario
                <select value={form.send_to} onChange={(e) => setForm({ ...form, send_to: e.target.value })} className={inputClassName}>
                  <option value="client">Cliente</option>
                  <option value="professional">Profesional</option>
                </select>
              </label>
            </div>
            <label className="block text-sm text-slate-400">
              Texto
              <textarea required value={form.template_text} onChange={(e) => setForm({ ...form, template_text: e.target.value })} className={textareaClassName} />
            </label>
          </SimpleForm>
        </Modal>
      ) : null}
    </div>
  );
}
