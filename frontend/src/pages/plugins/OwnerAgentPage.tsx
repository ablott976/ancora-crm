import { useEffect, useState } from 'react';
import { Phone, Shield } from 'lucide-react';
import api from '../../api/client';
import {
  Card,
  ErrorState,
  LoadingState,
  PageHeader,
  SectionTitle,
  formatDate,
  formatError,
  inputClassName,
  pluginRoutePath,
  primaryButtonClassName,
} from './shared';

type OwnerConfig = {
  configured?: boolean;
  owner_phone?: string;
  daily_summary_enabled?: boolean;
  daily_summary_time?: string;
};

type Summary = {
  date: string;
  conversations: number;
  messages: number;
  new_bookings: number;
};

const initialForm = {
  owner_phone: '',
  daily_summary_enabled: true,
  daily_summary_time: '21:00',
};

export default function OwnerAgentPage() {
  const [config, setConfig] = useState<OwnerConfig | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summaryDate, setSummaryDate] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [configRes, summaryRes] = await Promise.all([
        api.get(pluginRoutePath('owner/config/10')),
        api.get(pluginRoutePath('owner/summary/10'), { params: { date: summaryDate || undefined } }),
      ]);
      setConfig(configRes.data);
      setSummary(summaryRes.data);
      setForm({
        owner_phone: configRes.data.owner_phone || '',
        daily_summary_enabled: configRes.data.daily_summary_enabled ?? true,
        daily_summary_time: configRes.data.daily_summary_time || '21:00',
      });
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [summaryDate]);

  const saveConfig = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    try {
      await api.post(pluginRoutePath('owner/config'), { instance_id: 10, ...form });
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="OwnerAgent" description="Configura el número del propietario y revisa el resumen diario generado para dirección." />

      {error ? <ErrorState message={error} onRetry={fetchData} /> : null}
      {loading ? <LoadingState label="Cargando agente del propietario..." /> : null}

      {!loading ? (
        <>
          <Card>
            <SectionTitle title="Configuración" subtitle="El resumen diario se enviará a este número una vez conectemos la automatización final." />
            <form onSubmit={saveConfig} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <label className="block text-sm text-slate-400">
                  Teléfono propietario
                  <input required value={form.owner_phone} onChange={(e) => setForm({ ...form, owner_phone: e.target.value })} className={inputClassName} />
                </label>
                <label className="block text-sm text-slate-400">
                  Hora de envío
                  <input type="time" value={form.daily_summary_time} onChange={(e) => setForm({ ...form, daily_summary_time: e.target.value })} className={inputClassName} />
                </label>
              </div>
              <label className="flex items-center gap-3 rounded-md border border-slate-800 bg-slate-950 px-3 py-3 text-sm text-slate-300">
                <input type="checkbox" checked={form.daily_summary_enabled} onChange={(e) => setForm({ ...form, daily_summary_enabled: e.target.checked })} className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-brand-500" />
                Activar resumen diario
              </label>
              <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 p-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-md bg-brand-500/10 p-2 text-brand-400"><Shield className="h-4 w-4" /></div>
                  <div>
                    <div className="font-medium text-white">{config?.configured === false ? 'Aún sin configurar' : 'Configuración activa'}</div>
                    <div className="text-sm text-slate-400">Teléfono actual: {config?.owner_phone || 'sin definir'}</div>
                  </div>
                </div>
                <button type="submit" className={primaryButtonClassName} disabled={saving}>
                  {saving ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </Card>

          <Card>
            <SectionTitle
              title="Resumen diario"
              subtitle={`Fecha del resumen: ${summary ? formatDate(summary.date) : '-'}`}
              action={<input type="date" value={summaryDate} onChange={(e) => setSummaryDate(e.target.value)} className={inputClassName} />}
            />
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-5">
                <div className="text-sm text-slate-400">Conversaciones</div>
                <div className="mt-3 text-3xl font-semibold text-white">{summary?.conversations ?? 0}</div>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-5">
                <div className="text-sm text-slate-400">Mensajes</div>
                <div className="mt-3 text-3xl font-semibold text-white">{summary?.messages ?? 0}</div>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-5">
                <div className="text-sm text-slate-400">Nuevas reservas</div>
                <div className="mt-3 flex items-center gap-3 text-3xl font-semibold text-white">
                  <Phone className="h-6 w-6 text-brand-400" />
                  {summary?.new_bookings ?? 0}
                </div>
              </div>
            </div>
          </Card>
        </>
      ) : null}
    </div>
  );
}
