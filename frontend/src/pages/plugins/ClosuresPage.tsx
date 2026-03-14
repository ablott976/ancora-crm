import { useEffect, useState } from 'react';
import { Lock, Pencil, Plus, Trash2 } from 'lucide-react';
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
  dashboardPluginPath,
  formatDate,
  formatError,
  inputClassName,
  primaryButtonClassName,
  selectClassName,
} from './shared';

type Closure = {
  id: number;
  start_date: string;
  end_date: string;
  reason?: string | null;
  closure_type: string;
  affects_all_services?: boolean;
};

const emptyForm = {
  start_date: '',
  end_date: '',
  reason: '',
  closure_type: 'other',
  affects_all_services: true,
};

export default function ClosuresPage() {
  const [closures, setClosures] = useState<Closure[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<Closure | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);

  const fetchClosures = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(dashboardPluginPath('closures'));
      setClosures(response.data);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClosures();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setIsModalOpen(true);
  };

  const openEdit = (closure: Closure) => {
    setEditing(closure);
    setForm({
      start_date: closure.start_date,
      end_date: closure.end_date,
      reason: closure.reason || '',
      closure_type: closure.closure_type,
      affects_all_services: Boolean(closure.affects_all_services),
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      if (editing) {
        await api.put(dashboardPluginPath(`closures/${editing.id}`), form);
      } else {
        await api.post(dashboardPluginPath('closures'), form);
      }
      setIsModalOpen(false);
      setForm(emptyForm);
      await fetchClosures();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (closureId: number) => {
    if (!window.confirm('¿Eliminar este cierre?')) return;
    try {
      await api.delete(dashboardPluginPath(`closures/${closureId}`));
      await fetchClosures();
    } catch (err) {
      setError(formatError(err));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Closures"
        description="Gestiona cierres temporales por vacaciones, mantenimiento o festivos para la instancia de Ancora Automations."
        action={
          <button type="button" onClick={openCreate} className={primaryButtonClassName}>
            <Plus className="mr-2 h-4 w-4" />
            Nuevo cierre
          </button>
        }
      />

      {error ? <ErrorState message={error} onRetry={fetchClosures} /> : null}
      {loading ? <LoadingState label="Cargando cierres..." /> : null}

      {!loading ? (
        <Card className="overflow-hidden p-0">
          <div className="border-b border-slate-800 px-6 py-4">
            <SectionTitle title="Calendario de cierres" subtitle="Cada cierre se aplicará sobre la instancia 10 hasta que conectemos el contexto real." />
          </div>
          {closures.length === 0 ? (
            <div className="p-6">
              <EmptyState title="Sin cierres registrados" description="Añade cierres para bloquear reservas o servicios en periodos concretos." />
            </div>
          ) : (
            <table className="min-w-full divide-y divide-slate-800">
              <thead className="bg-slate-950">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Periodo</th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Motivo</th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Tipo</th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Ámbito</th>
                  <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-400">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-slate-900">
                {closures.map((closure) => (
                  <tr key={closure.id} className="hover:bg-slate-800/40">
                    <td className="px-6 py-4 text-sm text-white">
                      <div className="flex items-center gap-3">
                        <div className="rounded-md bg-brand-500/10 p-2 text-brand-400">
                          <Lock className="h-4 w-4" />
                        </div>
                        <div>
                          <div>{formatDate(closure.start_date)} - {formatDate(closure.end_date)}</div>
                          <div className="text-xs text-slate-400">ID #{closure.id}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-300">{closure.reason || 'Sin motivo indicado'}</td>
                    <td className="px-6 py-4 text-sm text-slate-300 capitalize">{closure.closure_type}</td>
                    <td className="px-6 py-4 text-sm">
                      <StatusBadge status={closure.affects_all_services ? 'active' : 'pending'} />
                    </td>
                    <td className="px-6 py-4 text-right text-sm">
                      <div className="flex justify-end gap-2">
                        <button type="button" onClick={() => openEdit(closure)} className="rounded-md bg-slate-800 p-2 text-slate-300 hover:bg-slate-700">
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button type="button" onClick={() => handleDelete(closure.id)} className="rounded-md bg-slate-800 p-2 text-red-300 hover:bg-red-500/10">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      ) : null}

      {isModalOpen ? (
        <Modal
          title={editing ? 'Editar cierre' : 'Nuevo cierre'}
          onClose={() => setIsModalOpen(false)}
          footer={<ModalFormActions submitLabel={editing ? 'Guardar cambios' : 'Crear cierre'} onClose={() => setIsModalOpen(false)} submitting={submitting} />}
        >
          <SimpleForm onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block text-sm text-slate-400">
                Fecha inicio
                <input type="date" required value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} className={inputClassName} />
              </label>
              <label className="block text-sm text-slate-400">
                Fecha fin
                <input type="date" required value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} className={inputClassName} />
              </label>
            </div>
            <label className="block text-sm text-slate-400">
              Tipo
              <select value={form.closure_type} onChange={(e) => setForm({ ...form, closure_type: e.target.value })} className={selectClassName}>
                <option value="holiday">Festivo</option>
                <option value="vacation">Vacaciones</option>
                <option value="maintenance">Mantenimiento</option>
                <option value="other">Otro</option>
              </select>
            </label>
            <label className="block text-sm text-slate-400">
              Motivo
              <input value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} className={inputClassName} placeholder="Describe el motivo del cierre" />
            </label>
            <label className="flex items-center gap-3 rounded-md border border-slate-800 bg-slate-950 px-3 py-3 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={form.affects_all_services}
                onChange={(e) => setForm({ ...form, affects_all_services: e.target.checked })}
                className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-brand-500"
              />
              Aplicar a todos los servicios
            </label>
          </SimpleForm>
        </Modal>
      ) : null}
    </div>
  );
}
