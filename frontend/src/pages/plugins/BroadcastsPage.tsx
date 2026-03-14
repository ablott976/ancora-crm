import { useEffect, useState } from 'react';
import { Megaphone, Plus, ShieldBan } from 'lucide-react';
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
  parseTags,
  pluginRoutePath,
  primaryButtonClassName,
  secondaryButtonClassName,
  textareaClassName,
} from './shared';

type Campaign = {
  id: number;
  name: string;
  message_template: string;
  target_tags?: string[];
  scheduled_at?: string | null;
  status: string;
  created_at: string;
};

type Recipient = {
  id: number;
  phone: string;
  name?: string | null;
  tags?: string[];
  opt_in_marketing: boolean;
  opted_out_at?: string | null;
};

const emptyCampaign = { name: '', message_template: '', target_tags: '', scheduled_at: '' };
const emptyRecipient = { phone: '', name: '', tags: '', opt_in_marketing: false };

export default function BroadcastsPage() {
  const [activeTab, setActiveTab] = useState<'campaigns' | 'recipients'>('campaigns');
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<'campaign' | 'recipient' | null>(null);
  const [campaignForm, setCampaignForm] = useState(emptyCampaign);
  const [recipientForm, setRecipientForm] = useState(emptyRecipient);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [campaignRes, recipientRes] = await Promise.all([
        api.get(pluginRoutePath('broadcasts/campaigns/10')),
        api.get(pluginRoutePath('broadcasts/recipients/10')),
      ]);
      setCampaigns(campaignRes.data);
      setRecipients(recipientRes.data);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const createCampaign = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.post(pluginRoutePath('broadcasts/campaigns'), {
        instance_id: 10,
        name: campaignForm.name,
        message_template: campaignForm.message_template,
        target_tags: parseTags(campaignForm.target_tags),
        scheduled_at: campaignForm.scheduled_at || null,
      });
      setModal(null);
      setCampaignForm(emptyCampaign);
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const createRecipient = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.post(pluginRoutePath('broadcasts/recipients'), {
        instance_id: 10,
        phone: recipientForm.phone,
        name: recipientForm.name || null,
        tags: parseTags(recipientForm.tags),
        opt_in_marketing: recipientForm.opt_in_marketing,
      });
      setModal(null);
      setRecipientForm(emptyRecipient);
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const optOut = async (phone: string) => {
    try {
      await api.post(pluginRoutePath(`broadcasts/recipients/10/${encodeURIComponent(phone)}/opt-out`));
      await fetchData();
    } catch (err) {
      setError(formatError(err));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Broadcasts"
        description="Administra campañas salientes y la base de destinatarios con consentimiento comercial."
        action={
          <button
            type="button"
            onClick={() => setModal(activeTab === 'campaigns' ? 'campaign' : 'recipient')}
            className={primaryButtonClassName}
          >
            <Plus className="mr-2 h-4 w-4" />
            {activeTab === 'campaigns' ? 'Nueva campaña' : 'Nuevo destinatario'}
          </button>
        }
      />

      <div className="flex gap-2">
        <button type="button" onClick={() => setActiveTab('campaigns')} className={activeTab === 'campaigns' ? primaryButtonClassName : secondaryButtonClassName}>Campañas</button>
        <button type="button" onClick={() => setActiveTab('recipients')} className={activeTab === 'recipients' ? primaryButtonClassName : secondaryButtonClassName}>Destinatarios</button>
      </div>

      {error ? <ErrorState message={error} onRetry={fetchData} /> : null}
      {loading ? <LoadingState label="Cargando broadcasts..." /> : null}

      {!loading && activeTab === 'campaigns' ? (
        <Card className="p-0">
          <div className="border-b border-slate-800 px-6 py-4">
            <SectionTitle title="Campañas" subtitle="Borradores y envíos programados para la instancia 10." />
          </div>
          {campaigns.length === 0 ? (
            <div className="p-6">
              <EmptyState title="Sin campañas" description="Crea la primera campaña para empezar a segmentar envíos." />
            </div>
          ) : (
            <table className="min-w-full divide-y divide-slate-800">
              <thead className="bg-slate-950">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Campaña</th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Etiquetas</th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Programación</th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-slate-900">
                {campaigns.map((campaign) => (
                  <tr key={campaign.id} className="hover:bg-slate-800/40">
                    <td className="px-6 py-4">
                      <div className="flex items-start gap-3">
                        <div className="rounded-md bg-brand-500/10 p-2 text-brand-400">
                          <Megaphone className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="font-medium text-white">{campaign.name}</div>
                          <p className="mt-1 max-w-xl text-sm text-slate-400">{campaign.message_template}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-300">{campaign.target_tags?.join(', ') || 'Todas'}</td>
                    <td className="px-6 py-4 text-sm text-slate-300">{campaign.scheduled_at ? formatDateTime(campaign.scheduled_at) : 'Sin programar'}</td>
                    <td className="px-6 py-4 text-sm"><StatusBadge status={campaign.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      ) : null}

      {!loading && activeTab === 'recipients' ? (
        <Card className="p-0">
          <div className="border-b border-slate-800 px-6 py-4">
            <SectionTitle title="Destinatarios" subtitle="Controla el opt-in y las etiquetas de segmentación." />
          </div>
          {recipients.length === 0 ? (
            <div className="p-6">
              <EmptyState title="Sin destinatarios" description="Añade números de teléfono y etiquetas para alimentar las campañas." />
            </div>
          ) : (
            <table className="min-w-full divide-y divide-slate-800">
              <thead className="bg-slate-950">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Contacto</th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Etiquetas</th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-400">Consentimiento</th>
                  <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-400">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-slate-900">
                {recipients.map((recipient) => (
                  <tr key={recipient.id} className="hover:bg-slate-800/40">
                    <td className="px-6 py-4 text-sm">
                      <div className="font-medium text-white">{recipient.name || 'Sin nombre'}</div>
                      <div className="text-slate-400">{recipient.phone}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-300">{recipient.tags?.join(', ') || '-'}</td>
                    <td className="px-6 py-4 text-sm"><StatusBadge status={recipient.opted_out_at ? 'failed' : recipient.opt_in_marketing ? 'signed' : 'pending'} /></td>
                    <td className="px-6 py-4 text-right text-sm">
                      {!recipient.opted_out_at ? (
                        <button type="button" onClick={() => optOut(recipient.phone)} className="inline-flex items-center gap-2 rounded-md bg-slate-800 px-3 py-2 text-slate-200 hover:bg-slate-700">
                          <ShieldBan className="h-4 w-4" />
                          Opt-out
                        </button>
                      ) : (
                        <span className="text-slate-500">Baja registrada</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      ) : null}

      {modal === 'campaign' ? (
        <Modal title="Nueva campaña" onClose={() => setModal(null)} footer={<ModalFormActions submitLabel="Crear campaña" onClose={() => setModal(null)} submitting={submitting} />}>
          <SimpleForm onSubmit={createCampaign}>
            <label className="block text-sm text-slate-400">
              Nombre
              <input required value={campaignForm.name} onChange={(e) => setCampaignForm({ ...campaignForm, name: e.target.value })} className={inputClassName} />
            </label>
            <label className="block text-sm text-slate-400">
              Mensaje
              <textarea required value={campaignForm.message_template} onChange={(e) => setCampaignForm({ ...campaignForm, message_template: e.target.value })} className={textareaClassName} />
            </label>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block text-sm text-slate-400">
                Etiquetas objetivo
                <input value={campaignForm.target_tags} onChange={(e) => setCampaignForm({ ...campaignForm, target_tags: e.target.value })} className={inputClassName} placeholder="vip, nuevos, madrid" />
              </label>
              <label className="block text-sm text-slate-400">
                Programar para
                <input type="datetime-local" value={campaignForm.scheduled_at} onChange={(e) => setCampaignForm({ ...campaignForm, scheduled_at: e.target.value })} className={inputClassName} />
              </label>
            </div>
          </SimpleForm>
        </Modal>
      ) : null}

      {modal === 'recipient' ? (
        <Modal title="Nuevo destinatario" onClose={() => setModal(null)} footer={<ModalFormActions submitLabel="Guardar destinatario" onClose={() => setModal(null)} submitting={submitting} />}>
          <SimpleForm onSubmit={createRecipient}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block text-sm text-slate-400">
                Nombre
                <input value={recipientForm.name} onChange={(e) => setRecipientForm({ ...recipientForm, name: e.target.value })} className={inputClassName} />
              </label>
              <label className="block text-sm text-slate-400">
                Teléfono
                <input required value={recipientForm.phone} onChange={(e) => setRecipientForm({ ...recipientForm, phone: e.target.value })} className={inputClassName} />
              </label>
            </div>
            <label className="block text-sm text-slate-400">
              Etiquetas
              <input value={recipientForm.tags} onChange={(e) => setRecipientForm({ ...recipientForm, tags: e.target.value })} className={inputClassName} placeholder="clientes-vip, interesados" />
            </label>
            <label className="flex items-center gap-3 rounded-md border border-slate-800 bg-slate-950 px-3 py-3 text-sm text-slate-300">
              <input type="checkbox" checked={recipientForm.opt_in_marketing} onChange={(e) => setRecipientForm({ ...recipientForm, opt_in_marketing: e.target.checked })} className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-brand-500" />
              Consentimiento de marketing confirmado
            </label>
          </SimpleForm>
        </Modal>
      ) : null}
    </div>
  );
}
