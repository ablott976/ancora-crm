import { useEffect, useState } from 'react';
import { Pencil, Plus, Trash2, UtensilsCrossed } from 'lucide-react';
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
  dashboardPluginPath,
  formatCurrency,
  formatDate,
  formatError,
  inputClassName,
  primaryButtonClassName,
  textareaClassName,
} from './shared';

type MenuItem = {
  id: number;
  name: string;
  description?: string | null;
  course_type?: string | null;
  allergens?: string | null;
  sort_order: number;
};

type Menu = {
  id: number;
  date: string;
  name: string;
  price?: number | null;
  is_active: boolean;
  items: MenuItem[];
};

const emptyMenu = { date: '', name: '', price: '', is_active: true };
const emptyItem = { name: '', description: '', course_type: '', allergens: '', sort_order: 0 };

export default function DailyMenusPage() {
  const [menus, setMenus] = useState<Menu[]>([]);
  const [selectedMenuId, setSelectedMenuId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [menuModalOpen, setMenuModalOpen] = useState(false);
  const [itemModalOpen, setItemModalOpen] = useState(false);
  const [editingMenu, setEditingMenu] = useState<Menu | null>(null);
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null);
  const [menuForm, setMenuForm] = useState(emptyMenu);
  const [itemForm, setItemForm] = useState(emptyItem);
  const [submitting, setSubmitting] = useState(false);

  const fetchMenus = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(dashboardPluginPath('daily-menus/menus'));
      setMenus(response.data);
      setSelectedMenuId((current) => current ?? response.data[0]?.id ?? null);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMenus();
  }, []);

  const selectedMenu = menus.find((menu) => menu.id === selectedMenuId) ?? null;

  const submitMenu = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const payload = { ...menuForm, price: menuForm.price ? Number(menuForm.price) : null };
      if (editingMenu) {
        await api.put(dashboardPluginPath(`daily-menus/menus/${editingMenu.id}`), payload);
      } else {
        await api.post(dashboardPluginPath('daily-menus/menus'), payload);
      }
      setMenuModalOpen(false);
      setEditingMenu(null);
      setMenuForm(emptyMenu);
      await fetchMenus();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const submitItem = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedMenuId) return;
    setSubmitting(true);
    try {
      const payload = { ...itemForm, sort_order: Number(itemForm.sort_order) };
      if (editingItem) {
        await api.put(dashboardPluginPath(`daily-menus/menus/${selectedMenuId}/items/${editingItem.id}`), payload);
      } else {
        await api.post(dashboardPluginPath(`daily-menus/menus/${selectedMenuId}/items`), payload);
      }
      setItemModalOpen(false);
      setEditingItem(null);
      setItemForm(emptyItem);
      await fetchMenus();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const deleteMenu = async (menuId: number) => {
    if (!window.confirm('¿Eliminar este menú?')) return;
    try {
      await api.delete(dashboardPluginPath(`daily-menus/menus/${menuId}`));
      await fetchMenus();
    } catch (err) {
      setError(formatError(err));
    }
  };

  const deleteItem = async (itemId: number) => {
    if (!selectedMenuId || !window.confirm('¿Eliminar este plato?')) return;
    try {
      await api.delete(dashboardPluginPath(`daily-menus/menus/${selectedMenuId}/items/${itemId}`));
      await fetchMenus();
    } catch (err) {
      setError(formatError(err));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="DailyMenus"
        description="Configura menús diarios y sus platos anidados para la experiencia del chatbot en restauración."
        action={
          <button type="button" onClick={() => { setEditingMenu(null); setMenuForm(emptyMenu); setMenuModalOpen(true); }} className={primaryButtonClassName}>
            <Plus className="mr-2 h-4 w-4" />
            Nuevo menú
          </button>
        }
      />

      {error ? <ErrorState message={error} onRetry={fetchMenus} /> : null}
      {loading ? <LoadingState label="Cargando menús..." /> : null}

      {!loading ? (
        <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <Card className="p-0">
            <div className="border-b border-slate-800 px-6 py-4">
              <SectionTitle title="Menús" subtitle="Selecciona un menú para editar sus platos." />
            </div>
            <div className="divide-y divide-slate-800">
              {menus.length === 0 ? (
                <div className="p-6">
                  <EmptyState title="Sin menús" description="Crea el primer menú del día para empezar." />
                </div>
              ) : (
                menus.map((menu) => (
                  <button
                    key={menu.id}
                    type="button"
                    onClick={() => setSelectedMenuId(menu.id)}
                    className={`flex w-full items-start justify-between px-6 py-4 text-left transition-colors ${selectedMenuId === menu.id ? 'bg-brand-500/10' : 'hover:bg-slate-800/40'}`}
                  >
                    <div>
                      <div className="font-medium text-white">{menu.name}</div>
                      <div className="mt-1 text-sm text-slate-400">{formatDate(menu.date)} · {formatCurrency(menu.price)}</div>
                    </div>
                    <div className="text-xs text-slate-400">{menu.items.length} platos</div>
                  </button>
                ))
              )}
            </div>
          </Card>

          <Card>
            {selectedMenu ? (
              <>
                <SectionTitle
                  title={selectedMenu.name}
                  subtitle={`${formatDate(selectedMenu.date)} · ${selectedMenu.is_active ? 'Activo' : 'Inactivo'}`}
                  action={
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setEditingMenu(selectedMenu);
                          setMenuForm({ date: selectedMenu.date, name: selectedMenu.name, price: selectedMenu.price?.toString() || '', is_active: selectedMenu.is_active });
                          setMenuModalOpen(true);
                        }}
                        className="rounded-md bg-slate-800 p-2 text-slate-300 hover:bg-slate-700"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button type="button" onClick={() => deleteMenu(selectedMenu.id)} className="rounded-md bg-slate-800 p-2 text-red-300 hover:bg-red-500/10">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  }
                />
                <div className="mb-4 flex justify-end">
                  <button type="button" onClick={() => { setEditingItem(null); setItemForm(emptyItem); setItemModalOpen(true); }} className={primaryButtonClassName}>
                    <Plus className="mr-2 h-4 w-4" />
                    Añadir plato
                  </button>
                </div>
                {selectedMenu.items.length === 0 ? (
                  <EmptyState title="Sin platos" description="Añade entrantes, principales o postres al menú seleccionado." />
                ) : (
                  <div className="space-y-3">
                    {selectedMenu.items.map((item) => (
                      <div key={item.id} className="flex items-start justify-between rounded-lg border border-slate-800 bg-slate-950 p-4">
                        <div className="flex items-start gap-3">
                          <div className="rounded-md bg-brand-500/10 p-2 text-brand-400">
                            <UtensilsCrossed className="h-4 w-4" />
                          </div>
                          <div>
                            <div className="font-medium text-white">{item.name}</div>
                            <div className="mt-1 text-sm text-slate-400">{item.course_type || 'Sin categoría'} · Orden {item.sort_order}</div>
                            {item.description ? <p className="mt-2 text-sm text-slate-300">{item.description}</p> : null}
                            {item.allergens ? <p className="mt-2 text-xs text-amber-300">Alérgenos: {item.allergens}</p> : null}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setEditingItem(item);
                              setItemForm({
                                name: item.name,
                                description: item.description || '',
                                course_type: item.course_type || '',
                                allergens: item.allergens || '',
                                sort_order: item.sort_order,
                              });
                              setItemModalOpen(true);
                            }}
                            className="rounded-md bg-slate-800 p-2 text-slate-300 hover:bg-slate-700"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button type="button" onClick={() => deleteItem(item.id)} className="rounded-md bg-slate-800 p-2 text-red-300 hover:bg-red-500/10">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <EmptyState title="Selecciona un menú" description="Elige un menú de la columna izquierda para ver y gestionar sus platos." />
            )}
          </Card>
        </div>
      ) : null}

      {menuModalOpen ? (
        <Modal title={editingMenu ? 'Editar menú' : 'Nuevo menú'} onClose={() => setMenuModalOpen(false)} footer={<ModalFormActions submitLabel={editingMenu ? 'Guardar menú' : 'Crear menú'} onClose={() => setMenuModalOpen(false)} submitting={submitting} />}>
          <SimpleForm onSubmit={submitMenu}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block text-sm text-slate-400">
                Fecha
                <input type="date" required value={menuForm.date} onChange={(e) => setMenuForm({ ...menuForm, date: e.target.value })} className={inputClassName} />
              </label>
              <label className="block text-sm text-slate-400">
                Precio
                <input type="number" step="0.01" value={menuForm.price} onChange={(e) => setMenuForm({ ...menuForm, price: e.target.value })} className={inputClassName} placeholder="15.50" />
              </label>
            </div>
            <label className="block text-sm text-slate-400">
              Nombre
              <input required value={menuForm.name} onChange={(e) => setMenuForm({ ...menuForm, name: e.target.value })} className={inputClassName} />
            </label>
            <label className="flex items-center gap-3 rounded-md border border-slate-800 bg-slate-950 px-3 py-3 text-sm text-slate-300">
              <input type="checkbox" checked={menuForm.is_active} onChange={(e) => setMenuForm({ ...menuForm, is_active: e.target.checked })} className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-brand-500" />
              Publicar menú como activo
            </label>
          </SimpleForm>
        </Modal>
      ) : null}

      {itemModalOpen ? (
        <Modal title={editingItem ? 'Editar plato' : 'Nuevo plato'} onClose={() => setItemModalOpen(false)} footer={<ModalFormActions submitLabel={editingItem ? 'Guardar plato' : 'Crear plato'} onClose={() => setItemModalOpen(false)} submitting={submitting} />}>
          <SimpleForm onSubmit={submitItem}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block text-sm text-slate-400">
                Nombre
                <input required value={itemForm.name} onChange={(e) => setItemForm({ ...itemForm, name: e.target.value })} className={inputClassName} />
              </label>
              <label className="block text-sm text-slate-400">
                Tipo de plato
                <input value={itemForm.course_type} onChange={(e) => setItemForm({ ...itemForm, course_type: e.target.value })} className={inputClassName} placeholder="Entrante, principal..." />
              </label>
            </div>
            <label className="block text-sm text-slate-400">
              Descripción
              <textarea value={itemForm.description} onChange={(e) => setItemForm({ ...itemForm, description: e.target.value })} className={textareaClassName} />
            </label>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block text-sm text-slate-400">
                Alérgenos
                <input value={itemForm.allergens} onChange={(e) => setItemForm({ ...itemForm, allergens: e.target.value })} className={inputClassName} placeholder="Gluten, frutos secos..." />
              </label>
              <label className="block text-sm text-slate-400">
                Orden
                <input type="number" value={itemForm.sort_order} onChange={(e) => setItemForm({ ...itemForm, sort_order: Number(e.target.value) })} className={inputClassName} />
              </label>
            </div>
          </SimpleForm>
        </Modal>
      ) : null}
    </div>
  );
}
