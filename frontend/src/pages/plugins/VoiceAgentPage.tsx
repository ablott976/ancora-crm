import { useEffect, useState } from 'react';
import { Phone } from 'lucide-react';
import api from '../../api/client';
import {
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  SectionTitle,
  StatusBadge,
  formatDateTime,
  formatError,
  inputClassName,
  pluginRoutePath,
  primaryButtonClassName,
  textareaClassName,
} from './shared';

type VoiceConfig = {
  configured?: boolean;
  credentials_set?: boolean;
  provider?: string;
  phone_number?: string | null;
  voice_model?: string | null;
  greeting_text?: string | null;
  max_call_duration_seconds?: number;
};

type CallItem = {
  id: number;
  caller_phone: string;
  direction: string;
  status: string;
  duration_seconds?: number | null;
  summary?: string | null;
  started_at: string;
};

const initialForm = {
  provider: 'twilio',
  phone_number: '',
  voice_model: '',
  greeting_text: '',
  max_call_duration_seconds: 300,
  api_key: '',
  api_secret: '',
};

export default function VoiceAgentPage() {
  const [config, setConfig] = useState<VoiceConfig | null>(null);
  const [calls, setCalls] = useState<CallItem[]>([]);
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [configRes, callsRes] = await Promise.all([
        api.get(pluginRoutePath('voice/config/10')),
        api.get(pluginRoutePath('voice/calls/10')),
      ]);
      setConfig(configRes.data);
      setCalls(callsRes.data);
      setForm((current) => ({
        ...current,
        provider: configRes.data.provider || 'twilio',
        phone_number: configRes.data.phone_number || '',
        voice_model: configRes.data.voice_model || '',
        greeting_text: configRes.data.greeting_text || '',
        max_call_duration_seconds: configRes.data.max_call_duration_seconds || 300,
      }));
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const saveConfig = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    try {
      await api.post(pluginRoutePath('voice/config'), { instance_id: 10, ...form, max_call_duration_seconds: Number(form.max_call_duration_seconds) });
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="VoiceAgent" description="Gestiona la configuración VAPI/Twilio y revisa el historial de llamadas." />

      {error ? <ErrorState message={error} onRetry={fetchData} /> : null}
      {loading ? <LoadingState label="Cargando agente de voz..." /> : null}

      {!loading ? (
        <>
          <Card>
            <SectionTitle title="Configuración" subtitle="Las credenciales se almacenan en backend; aquí solo se reemplazan cuando hace falta." />
            <form onSubmit={saveConfig} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <label className="block text-sm text-slate-400">
                  Proveedor
                  <select value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })} className={inputClassName}>
                    <option value="twilio">Twilio</option>
                    <option value="vapi">Vapi</option>
                  </select>
                </label>
                <label className="block text-sm text-slate-400">
                  Número
                  <input value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} className={inputClassName} />
                </label>
                <label className="block text-sm text-slate-400">
                  Modelo de voz
                  <input value={form.voice_model} onChange={(e) => setForm({ ...form, voice_model: e.target.value })} className={inputClassName} />
                </label>
              </div>
              <label className="block text-sm text-slate-400">
                Greeting
                <textarea value={form.greeting_text} onChange={(e) => setForm({ ...form, greeting_text: e.target.value })} className={textareaClassName} />
              </label>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <label className="block text-sm text-slate-400">
                  Máx. duración (s)
                  <input type="number" value={form.max_call_duration_seconds} onChange={(e) => setForm({ ...form, max_call_duration_seconds: Number(e.target.value) })} className={inputClassName} />
                </label>
                <label className="block text-sm text-slate-400">
                  API key
                  <input value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} className={inputClassName} />
                </label>
                <label className="block text-sm text-slate-400">
                  API secret
                  <input value={form.api_secret} onChange={(e) => setForm({ ...form, api_secret: e.target.value })} className={inputClassName} />
                </label>
              </div>
              <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 p-4">
                <div className="text-sm text-slate-400">Credenciales almacenadas: {config?.credentials_set ? 'sí' : 'no'}</div>
                <button type="submit" className={primaryButtonClassName} disabled={saving}>{saving ? 'Guardando...' : 'Guardar configuración'}</button>
              </div>
            </form>
          </Card>

          <Card className="p-0">
            <div className="border-b border-slate-800 px-6 py-4">
              <SectionTitle title="Historial de llamadas" subtitle={`${calls.length} llamadas recientes`} />
            </div>
            {calls.length === 0 ? (
              <div className="p-6">
                <EmptyState title="Sin llamadas" description="Las llamadas entrantes y salientes aparecerán aquí." />
              </div>
            ) : (
              <div className="divide-y divide-slate-800">
                {calls.map((call) => (
                  <div key={call.id} className="px-6 py-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-2">
                        <div className="flex items-center gap-3">
                          <div className="rounded-md bg-brand-500/10 p-2 text-brand-400"><Phone className="h-4 w-4" /></div>
                          <div className="font-medium text-white">{call.caller_phone}</div>
                          <StatusBadge status={call.status} />
                        </div>
                        <p className="text-sm text-slate-400">{call.direction} · {call.duration_seconds ?? 0}s</p>
                        {call.summary ? <p className="text-sm text-slate-300">{call.summary}</p> : null}
                      </div>
                      <div className="text-sm text-slate-400">{formatDateTime(call.started_at)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      ) : null}
    </div>
  );
}
