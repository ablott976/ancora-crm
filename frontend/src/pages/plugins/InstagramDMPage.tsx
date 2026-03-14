import { useEffect, useState } from 'react';
import { CheckCircle2, Instagram, MessageCircle } from 'lucide-react';
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

type IGConfig = {
  configured?: boolean;
  token_set?: boolean;
  ig_page_id?: string;
  ig_username?: string;
  webhook_verify_token?: string;
};

type Conversation = {
  id: number;
  ig_name?: string | null;
  ig_username?: string | null;
  ig_user_id: string;
  is_resolved: boolean;
  last_message_at?: string | null;
};

type Message = {
  id: number;
  direction: string;
  message_text: string;
  media_url?: string | null;
  created_at: string;
};

const emptyForm = {
  ig_page_id: '',
  ig_access_token: '',
  ig_username: '',
  webhook_verify_token: '',
};

export default function InstagramDMPage() {
  const [config, setConfig] = useState<IGConfig | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [threadLoading, setThreadLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [configRes, conversationsRes] = await Promise.all([
        api.get(pluginRoutePath('instagram-dm/config/10')),
        api.get(pluginRoutePath('instagram-dm/conversations/10')),
      ]);
      setConfig(configRes.data);
      setForm((current) => ({
        ...current,
        ig_page_id: configRes.data.ig_page_id || '',
        ig_username: configRes.data.ig_username || '',
        webhook_verify_token: configRes.data.webhook_verify_token || '',
      }));
      setConversations(conversationsRes.data);
      const nextConversation = conversationsRes.data[0] || null;
      setSelectedConversation(nextConversation);
      if (nextConversation) {
        await fetchMessages(nextConversation.id);
      } else {
        setMessages([]);
      }
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (conversationId: number) => {
    setThreadLoading(true);
    try {
      const response = await api.get(pluginRoutePath(`instagram-dm/messages/${conversationId}`));
      setMessages(response.data);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setThreadLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const saveConfig = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    try {
      await api.post(pluginRoutePath('instagram-dm/config'), { instance_id: 10, ...form });
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSaving(false);
    }
  };

  const resolveConversation = async () => {
    if (!selectedConversation) return;
    try {
      await api.post(pluginRoutePath(`instagram-dm/conversations/${selectedConversation.id}/resolve`));
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="InstagramDM"
        description="Configura el canal de Instagram Direct y revisa conversaciones activas con su hilo completo."
      />

      {error ? <ErrorState message={error} onRetry={fetchData} /> : null}
      {loading ? <LoadingState label="Cargando integración de Instagram..." /> : null}

      {!loading ? (
        <>
          <Card>
            <SectionTitle title="Configuración" subtitle="La API de Instagram usa rutas montadas bajo /api/chatbot/api/plugins." />
            <form onSubmit={saveConfig} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <label className="block text-sm text-slate-400">
                  Page ID
                  <input required value={form.ig_page_id} onChange={(e) => setForm({ ...form, ig_page_id: e.target.value })} className={inputClassName} />
                </label>
                <label className="block text-sm text-slate-400">
                  Username
                  <input value={form.ig_username} onChange={(e) => setForm({ ...form, ig_username: e.target.value })} className={inputClassName} />
                </label>
              </div>
              <label className="block text-sm text-slate-400">
                Access token
                <textarea value={form.ig_access_token} onChange={(e) => setForm({ ...form, ig_access_token: e.target.value })} className={textareaClassName} placeholder={config?.token_set ? 'Token ya configurado. Introduce uno nuevo solo si quieres reemplazarlo.' : ''} />
              </label>
              <label className="block text-sm text-slate-400">
                Webhook verify token
                <input value={form.webhook_verify_token} onChange={(e) => setForm({ ...form, webhook_verify_token: e.target.value })} className={inputClassName} />
              </label>
              <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 p-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-md bg-brand-500/10 p-2 text-brand-400">
                    <Instagram className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="font-medium text-white">{config?.configured ? 'Canal configurado' : 'Configuración pendiente'}</div>
                    <div className="text-sm text-slate-400">Token almacenado: {config?.token_set ? 'sí' : 'no'}</div>
                  </div>
                </div>
                <button type="submit" className={primaryButtonClassName} disabled={saving}>
                  {saving ? 'Guardando...' : 'Guardar configuración'}
                </button>
              </div>
            </form>
          </Card>

          <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
            <Card className="p-0">
              <div className="border-b border-slate-800 px-6 py-4">
                <SectionTitle title="Conversaciones" subtitle="Hilos abiertos y pendientes de resolución." />
              </div>
              <div className="divide-y divide-slate-800">
                {conversations.length === 0 ? (
                  <div className="p-6">
                    <EmptyState title="Sin conversaciones" description="Cuando entren mensajes desde Instagram aparecerán aquí." />
                  </div>
                ) : (
                  conversations.map((conversation) => (
                    <button
                      key={conversation.id}
                      type="button"
                      onClick={() => { setSelectedConversation(conversation); fetchMessages(conversation.id); }}
                      className={`w-full px-6 py-4 text-left transition-colors ${selectedConversation?.id === conversation.id ? 'bg-brand-500/10' : 'hover:bg-slate-800/40'}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-medium text-white">{conversation.ig_name || conversation.ig_username || conversation.ig_user_id}</div>
                          <div className="mt-1 text-sm text-slate-400">@{conversation.ig_username || 'sin-username'}</div>
                        </div>
                        <StatusBadge status={conversation.is_resolved ? 'resolved' : 'active'} />
                      </div>
                      <div className="mt-2 text-xs text-slate-500">{formatDateTime(conversation.last_message_at)}</div>
                    </button>
                  ))
                )}
              </div>
            </Card>

            <Card>
              {selectedConversation ? (
                <>
                  <SectionTitle
                    title={selectedConversation.ig_name || selectedConversation.ig_username || 'Conversación'}
                    subtitle={`Usuario: ${selectedConversation.ig_user_id}`}
                    action={
                      !selectedConversation.is_resolved ? (
                        <button type="button" onClick={resolveConversation} className={primaryButtonClassName}>
                          <CheckCircle2 className="mr-2 h-4 w-4" />
                          Resolver
                        </button>
                      ) : null
                    }
                  />
                  {threadLoading ? (
                    <LoadingState label="Cargando hilo..." />
                  ) : messages.length === 0 ? (
                    <EmptyState title="Sin mensajes" description="Este hilo no tiene mensajes almacenados todavía." />
                  ) : (
                    <div className="space-y-3">
                      {messages.map((message) => (
                        <div key={message.id} className={`max-w-2xl rounded-2xl px-4 py-3 ${message.direction === 'outbound' ? 'ml-auto bg-brand-600 text-white' : 'bg-slate-800 text-slate-100'}`}>
                          <div className="mb-2 flex items-center gap-2 text-xs opacity-80">
                            <MessageCircle className="h-3.5 w-3.5" />
                            <span>{message.direction === 'outbound' ? 'Equipo' : 'Cliente'}</span>
                            <span>{formatDateTime(message.created_at)}</span>
                          </div>
                          <p className="whitespace-pre-wrap text-sm">{message.message_text}</p>
                          {message.media_url ? <a href={message.media_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs underline">Ver media</a> : null}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <EmptyState title="Selecciona una conversación" description="Elige un hilo para ver el histórico de mensajes." />
              )}
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
