import { useEffect, useState } from 'react';
import { Mic, Timer, Waves } from 'lucide-react';
import api from '../../api/client';
import {
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  SectionTitle,
  formatDateTime,
  formatError,
  inputClassName,
  pluginRoutePath,
} from './shared';

type Transcription = {
  id: number;
  contact_phone: string;
  transcription_text: string;
  duration_seconds?: number | null;
  language?: string | null;
  model_used?: string | null;
  tokens_used?: number | null;
  created_at: string;
  original_media_url?: string | null;
};

type Stats = {
  total: number;
  total_duration?: number | null;
  total_tokens?: number | null;
};

export default function AudioTranscriptionPage() {
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [phoneFilter, setPhoneFilter] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [transcriptionRes, statsRes] = await Promise.all([
        api.get(pluginRoutePath('audio/transcriptions/10'), { params: { phone: phoneFilter || undefined } }),
        api.get(pluginRoutePath('audio/stats/10')),
      ]);
      setTranscriptions(transcriptionRes.data);
      setStats(statsRes.data);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [phoneFilter]);

  return (
    <div className="space-y-6">
      <PageHeader title="AudioTranscription" description="Revisa el histórico de audios transcritos y las métricas agregadas por instancia." />

      <Card className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-md bg-brand-500/10 p-2 text-brand-400"><Mic className="h-4 w-4" /></div>
            <div>
              <div className="text-sm text-slate-400">Total transcripciones</div>
              <div className="text-2xl font-semibold text-white">{stats?.total ?? 0}</div>
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-md bg-brand-500/10 p-2 text-brand-400"><Timer className="h-4 w-4" /></div>
            <div>
              <div className="text-sm text-slate-400">Duración total</div>
              <div className="text-2xl font-semibold text-white">{stats?.total_duration ?? 0}s</div>
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-md bg-brand-500/10 p-2 text-brand-400"><Waves className="h-4 w-4" /></div>
            <div>
              <div className="text-sm text-slate-400">Tokens consumidos</div>
              <div className="text-2xl font-semibold text-white">{stats?.total_tokens ?? 0}</div>
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <label className="block text-sm text-slate-400">
          Filtrar por teléfono
          <input value={phoneFilter} onChange={(e) => setPhoneFilter(e.target.value)} className={inputClassName} placeholder="+34..." />
        </label>
      </Card>

      {error ? <ErrorState message={error} onRetry={fetchData} /> : null}
      {loading ? <LoadingState label="Cargando transcripciones..." /> : null}

      {!loading ? (
        <Card className="p-0">
          <div className="border-b border-slate-800 px-6 py-4">
            <SectionTitle title="Histórico de audios" subtitle="Los registros más recientes se muestran primero." />
          </div>
          {transcriptions.length === 0 ? (
            <div className="p-6">
              <EmptyState title="Sin transcripciones" description="No hay audios registrados para el filtro actual." />
            </div>
          ) : (
            <div className="divide-y divide-slate-800">
              {transcriptions.map((item) => (
                <div key={item.id} className="px-6 py-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2">
                      <div className="text-sm text-slate-400">{item.contact_phone} · {item.language || 'es'} · {item.model_used || 'modelo no indicado'}</div>
                      <p className="text-sm text-white">{item.transcription_text}</p>
                      {item.original_media_url ? <a href={item.original_media_url} target="_blank" rel="noreferrer" className="text-xs text-brand-400 hover:text-brand-300">Abrir media original</a> : null}
                    </div>
                    <div className="text-right text-sm text-slate-400">
                      <div>{formatDateTime(item.created_at)}</div>
                      <div className="mt-1">{item.duration_seconds ?? 0}s · {item.tokens_used ?? 0} tokens</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      ) : null}
    </div>
  );
}
