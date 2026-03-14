import { useEffect, useState } from 'react';
import { Plus, Search, UserCheck } from 'lucide-react';
import api from '../../api/client';
import {
  Card,
  EmptyState,
  ErrorState,
  FilterInput,
  LoadingState,
  Modal,
  ModalFormActions,
  PageHeader,
  SectionTitle,
  SimpleForm,
  StatusBadge,
  formatCurrency,
  formatDateTime,
  formatError,
  inputClassName,
  pluginRoutePath,
  primaryButtonClassName,
  textareaClassName,
} from './shared';

type Profile = {
  id: number;
  name?: string | null;
  phone?: string | null;
  customer_code: string;
  vip_status: boolean;
  total_visits: number;
  total_spent: number;
  tags?: string[] | null;
  notes?: string | null;
  last_visit_at?: string | null;
};

type Interaction = {
  id: number;
  interaction_type: string;
  description?: string | null;
  amount?: number | null;
  created_at: string;
};

const interactionFormInitial = { interaction_type: 'visit', description: '', amount: '' };

export default function AdvancedCRMPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null);
  const [history, setHistory] = useState<Interaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [vipOnly, setVipOnly] = useState(false);
  const [interactionForm, setInteractionForm] = useState(interactionFormInitial);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const fetchProfiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(pluginRoutePath('crm/profiles/10'), { params: { search: search || undefined, vip_only: vipOnly || undefined } });
      setProfiles(response.data);
      const nextSelected = response.data.find((profile: Profile) => profile.id === selectedProfile?.id) || response.data[0] || null;
      setSelectedProfile(nextSelected);
      if (nextSelected) {
        await fetchHistory(nextSelected.id);
      } else {
        setHistory([]);
      }
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async (profileId: number) => {
    setHistoryLoading(true);
    try {
      const response = await api.get(pluginRoutePath(`crm/history/${profileId}`));
      setHistory(response.data);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchProfiles();
  }, [search, vipOnly]);

  const addInteraction = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedProfile) return;
    setSubmitting(true);
    try {
      await api.post(pluginRoutePath(`crm/interactions/${selectedProfile.id}`), {
        interaction_type: interactionForm.interaction_type,
        description: interactionForm.description || null,
        amount: interactionForm.amount ? Number(interactionForm.amount) : null,
      });
      setModalOpen(false);
      setInteractionForm(interactionFormInitial);
      await fetchProfiles();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="AdvancedCRM"
        description="Busca perfiles, aísla clientes VIP y revisa su histórico de interacciones desde el plugin CRM."
        action={
          <button type="button" onClick={() => setModalOpen(true)} className={primaryButtonClassName} disabled={!selectedProfile}>
            <Plus className="mr-2 h-4 w-4" />
            Nueva interacción
          </button>
        }
      />

      <Card>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-[1fr_auto]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-500" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar por nombre, teléfono o código..." className={`pl-10 ${inputClassName}`} />
          </div>
          <label className="flex items-center gap-3 rounded-md border border-slate-800 bg-slate-950 px-4 py-2 text-sm text-slate-300">
            <input type="checkbox" checked={vipOnly} onChange={(e) => setVipOnly(e.target.checked)} className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-brand-500" />
            Solo VIP
          </label>
        </div>
      </Card>

      {error ? <ErrorState message={error} onRetry={fetchProfiles} /> : null}
      {loading ? <LoadingState label="Cargando perfiles CRM..." /> : null}

      {!loading ? (
        <div className="grid gap-6 lg:grid-cols-[420px_minmax(0,1fr)]">
          <Card className="p-0">
            <div className="border-b border-slate-800 px-6 py-4">
              <SectionTitle title="Perfiles" subtitle={`${profiles.length} perfiles encontrados`} />
            </div>
            {profiles.length === 0 ? (
              <div className="p-6">
                <EmptyState title="Sin perfiles" description="No hay resultados para los filtros actuales." />
              </div>
            ) : (
              <div className="divide-y divide-slate-800">
                {profiles.map((profile) => (
                  <button
                    key={profile.id}
                    type="button"
                    onClick={() => { setSelectedProfile(profile); fetchHistory(profile.id); }}
                    className={`w-full px-6 py-4 text-left transition-colors ${selectedProfile?.id === profile.id ? 'bg-brand-500/10' : 'hover:bg-slate-800/40'}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-medium text-white">{profile.name || 'Sin nombre'}</div>
                        <div className="mt-1 text-sm text-slate-400">{profile.phone || 'Sin teléfono'} · {profile.customer_code}</div>
                      </div>
                      <StatusBadge status={profile.vip_status ? 'active' : 'pending'} />
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-3 text-xs text-slate-400">
                      <span>Visitas: {profile.total_visits}</span>
                      <span>Gasto: {formatCurrency(profile.total_spent)}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Card>

          <Card>
            {selectedProfile ? (
              <>
                <SectionTitle title={selectedProfile.name || selectedProfile.customer_code} subtitle={`Última visita: ${formatDateTime(selectedProfile.last_visit_at)}`} />
                <div className="mb-6 grid gap-4 md:grid-cols-3">
                  <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                    <div className="text-sm text-slate-400">Código cliente</div>
                    <div className="mt-2 text-lg font-semibold text-white">{selectedProfile.customer_code}</div>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                    <div className="text-sm text-slate-400">Total visitas</div>
                    <div className="mt-2 text-lg font-semibold text-white">{selectedProfile.total_visits}</div>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                    <div className="text-sm text-slate-400">Total gastado</div>
                    <div className="mt-2 text-lg font-semibold text-white">{formatCurrency(selectedProfile.total_spent)}</div>
                  </div>
                </div>

                <SectionTitle title="Histórico" subtitle="Interacciones registradas manualmente y desde automatizaciones." />
                {historyLoading ? (
                  <LoadingState label="Cargando histórico..." />
                ) : history.length === 0 ? (
                  <EmptyState title="Sin interacciones" description="Este perfil todavía no tiene actividad registrada." />
                ) : (
                  <div className="space-y-3">
                    {history.map((item) => (
                      <div key={item.id} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-3">
                              <div className="rounded-md bg-brand-500/10 p-2 text-brand-400">
                                <UserCheck className="h-4 w-4" />
                              </div>
                              <div className="font-medium text-white capitalize">{item.interaction_type}</div>
                            </div>
                            {item.description ? <p className="mt-3 text-sm text-slate-300">{item.description}</p> : null}
                          </div>
                          <div className="text-right text-sm text-slate-400">
                            <div>{formatDateTime(item.created_at)}</div>
                            {item.amount != null ? <div className="mt-2 font-medium text-white">{formatCurrency(item.amount)}</div> : null}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <EmptyState title="Selecciona un perfil" description="Elige un perfil para ver su histórico de cliente." />
            )}
          </Card>
        </div>
      ) : null}

      {modalOpen ? (
        <Modal title="Registrar interacción" onClose={() => setModalOpen(false)} footer={<ModalFormActions submitLabel="Guardar interacción" onClose={() => setModalOpen(false)} submitting={submitting} />}>
          <SimpleForm onSubmit={addInteraction}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <FilterInput label="Tipo">
                <select value={interactionForm.interaction_type} onChange={(e) => setInteractionForm({ ...interactionForm, interaction_type: e.target.value })} className={inputClassName}>
                  <option value="visit">Visita</option>
                  <option value="purchase">Compra</option>
                  <option value="call">Llamada</option>
                  <option value="note">Nota</option>
                </select>
              </FilterInput>
              <FilterInput label="Importe">
                <input type="number" step="0.01" value={interactionForm.amount} onChange={(e) => setInteractionForm({ ...interactionForm, amount: e.target.value })} className={inputClassName} />
              </FilterInput>
            </div>
            <label className="block text-sm text-slate-400">
              Descripción
              <textarea value={interactionForm.description} onChange={(e) => setInteractionForm({ ...interactionForm, description: e.target.value })} className={textareaClassName} />
            </label>
          </SimpleForm>
        </Modal>
      ) : null}
    </div>
  );
}
