import { useEffect, useState } from 'react';
import { FileCheck, Plus } from 'lucide-react';
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
  pluginRoutePath,
  primaryButtonClassName,
  textareaClassName,
} from './shared';

type Template = {
  id: number;
  name: string;
  requires_id_number: boolean;
  requires_signature: boolean;
  content_html: string;
};

type RecordItem = {
  id: number;
  template_name: string;
  client_name: string;
  client_phone?: string | null;
  status: string;
  signed_at?: string | null;
  created_at: string;
};

const templateInitial = {
  name: '',
  content_html: '',
  service_id: '',
  requires_id_number: false,
  requires_signature: true,
};

export default function ConsentFormsPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(templateInitial);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [templatesRes, recordsRes] = await Promise.all([
        api.get(pluginRoutePath('consents/templates/10')),
        api.get(pluginRoutePath('consents/records/10'), { params: { status: statusFilter || undefined } }),
      ]);
      setTemplates(templatesRes.data);
      setRecords(recordsRes.data);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const createTemplate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.post(pluginRoutePath('consents/templates'), {
        instance_id: 10,
        name: form.name,
        content_html: form.content_html,
        service_id: form.service_id ? Number(form.service_id) : null,
        requires_id_number: form.requires_id_number,
        requires_signature: form.requires_signature,
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

  return (
    <div className="space-y-6">
      <PageHeader
        title="ConsentForms"
        description="Gestiona plantillas de consentimiento y consulta los registros firmados o pendientes."
        action={
          <button type="button" onClick={() => setModalOpen(true)} className={primaryButtonClassName}>
            <Plus className="mr-2 h-4 w-4" />
            Nueva plantilla
          </button>
        }
      />

      <Card>
        <label className="block text-sm text-slate-400">
          Filtrar registros por estado
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className={inputClassName}>
            <option value="">Todos</option>
            <option value="pending">Pendiente</option>
            <option value="signed">Firmado</option>
          </select>
        </label>
      </Card>

      {error ? <ErrorState message={error} onRetry={fetchData} /> : null}
      {loading ? <LoadingState label="Cargando consentimientos..." /> : null}

      {!loading ? (
        <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
          <Card>
            <SectionTitle title="Plantillas" subtitle={`${templates.length} plantillas activas`} />
            {templates.length === 0 ? (
              <EmptyState title="Sin plantillas" description="Crea una plantilla para digitalizar consentimientos." />
            ) : (
              <div className="space-y-3">
                {templates.map((template) => (
                  <div key={template.id} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                    <div className="flex items-start gap-3">
                      <div className="rounded-md bg-brand-500/10 p-2 text-brand-400"><FileCheck className="h-4 w-4" /></div>
                      <div>
                        <div className="font-medium text-white">{template.name}</div>
                        <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-400">
                          <span>ID requerido: {template.requires_id_number ? 'sí' : 'no'}</span>
                          <span>Firma requerida: {template.requires_signature ? 'sí' : 'no'}</span>
                        </div>
                        <p className="mt-3 line-clamp-4 text-sm text-slate-300">{template.content_html}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card className="p-0">
            <div className="border-b border-slate-800 px-6 py-4">
              <SectionTitle title="Registros" subtitle="Estados de firma y trazabilidad." />
            </div>
            {records.length === 0 ? (
              <div className="p-6">
                <EmptyState title="Sin registros" description="No hay consentimientos para el filtro actual." />
              </div>
            ) : (
              <table className="min-w-full divide-y divide-slate-800">
                <thead className="bg-slate-950">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Cliente</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Plantilla</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Estado</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Fechas</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 bg-slate-900">
                  {records.map((record) => (
                    <tr key={record.id} className="hover:bg-slate-800/40">
                      <td className="px-6 py-4 text-sm">
                        <div className="font-medium text-white">{record.client_name}</div>
                        <div className="text-slate-400">{record.client_phone || 'Sin teléfono'}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-300">{record.template_name}</td>
                      <td className="px-6 py-4 text-sm"><StatusBadge status={record.status} /></td>
                      <td className="px-6 py-4 text-sm text-slate-300">
                        <div>Creado: {formatDateTime(record.created_at)}</div>
                        <div>Firmado: {formatDateTime(record.signed_at)}</div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      ) : null}

      {modalOpen ? (
        <Modal title="Nueva plantilla de consentimiento" onClose={() => setModalOpen(false)} footer={<ModalFormActions submitLabel="Guardar plantilla" onClose={() => setModalOpen(false)} submitting={submitting} />}>
          <SimpleForm onSubmit={createTemplate}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block text-sm text-slate-400">
                Nombre
                <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={inputClassName} />
              </label>
              <label className="block text-sm text-slate-400">
                Service ID
                <input value={form.service_id} onChange={(e) => setForm({ ...form, service_id: e.target.value })} className={inputClassName} />
              </label>
            </div>
            <label className="block text-sm text-slate-400">
              HTML de la plantilla
              <textarea required value={form.content_html} onChange={(e) => setForm({ ...form, content_html: e.target.value })} className={textareaClassName} />
            </label>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="flex items-center gap-3 rounded-md border border-slate-800 bg-slate-950 px-3 py-3 text-sm text-slate-300">
                <input type="checkbox" checked={form.requires_id_number} onChange={(e) => setForm({ ...form, requires_id_number: e.target.checked })} className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-brand-500" />
                Requerir DNI/NIE
              </label>
              <label className="flex items-center gap-3 rounded-md border border-slate-800 bg-slate-950 px-3 py-3 text-sm text-slate-300">
                <input type="checkbox" checked={form.requires_signature} onChange={(e) => setForm({ ...form, requires_signature: e.target.checked })} className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-brand-500" />
                Requerir firma
              </label>
            </div>
          </SimpleForm>
        </Modal>
      ) : null}
    </div>
  );
}
