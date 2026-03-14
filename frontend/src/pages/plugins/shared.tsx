import type { FormEvent, PropsWithChildren, ReactNode } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import clsx from 'clsx';

// TODO: instance_id should come from app context or a route param instead of a hardcoded value.
export const PLUGIN_INSTANCE_ID = 10;

export const inputClassName =
  'mt-1 block w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-brand-500 focus:outline-none';
export const textareaClassName = `${inputClassName} min-h-24`;
export const selectClassName = inputClassName;
export const primaryButtonClassName =
  'inline-flex items-center justify-center rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50';
export const secondaryButtonClassName =
  'inline-flex items-center justify-center rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50';

export function pluginApiPath(path: string) {
  return `/chatbot${path}`;
}

export function dashboardPluginPath(plugin: string, path = '') {
  return pluginApiPath(`/dashboard/${PLUGIN_INSTANCE_ID}/${plugin}${path}`);
}

export function pluginRoutePath(plugin: string, path = '') {
  return pluginApiPath(`/api/plugins/${plugin}${path}`);
}

export function formatError(error: unknown) {
  if (typeof error === 'object' && error !== null) {
    const candidate = error as {
      response?: { data?: { detail?: string } | string };
      message?: string;
    };
    if (typeof candidate.response?.data === 'string') {
      return candidate.response.data;
    }
    if (typeof candidate.response?.data === 'object' && candidate.response?.data && 'detail' in candidate.response.data) {
      const detail = candidate.response.data.detail;
      if (typeof detail === 'string') {
        return detail;
      }
    }
    if (typeof candidate.message === 'string') {
      return candidate.message;
    }
  }
  return 'Ha ocurrido un error inesperado.';
}

export function formatDate(value?: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleDateString('es-ES');
}

export function formatDateTime(value?: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleString('es-ES', {
    dateStyle: 'short',
    timeStyle: 'short',
  });
}

export function formatCurrency(value?: number | null) {
  if (value == null) return '-';
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
  }).format(value);
}

export function joinList(value?: string[] | null) {
  if (!value || value.length === 0) return '-';
  return value.join(', ');
}

export function parseTags(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
        <p className="mt-1 text-sm text-slate-400">{description}</p>
      </div>
      {action ? <div className="flex-shrink-0">{action}</div> : null}
    </div>
  );
}

export function Card({ className, children }: PropsWithChildren<{ className?: string }>) {
  return <div className={clsx('rounded-lg border border-slate-800 bg-slate-900 p-6', className)}>{children}</div>;
}

export function SectionTitle({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div>
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-slate-400">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function LoadingState({ label = 'Cargando...' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 rounded-lg border border-slate-800 bg-slate-900 p-8 text-slate-400">
      <Loader2 className="h-5 w-5 animate-spin" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 text-red-400" />
        <div className="space-y-3">
          <p className="text-sm text-red-100">{message}</p>
          {onRetry ? (
            <button type="button" onClick={onRetry} className={secondaryButtonClassName}>
              Reintentar
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-700 bg-slate-950/60 p-8 text-center">
      <h3 className="text-base font-medium text-white">{title}</h3>
      <p className="mt-2 text-sm text-slate-400">{description}</p>
    </div>
  );
}

export function StatusBadge({ status }: { status?: string | boolean | null }) {
  const normalized = String(status ?? '').toLowerCase();
  const positive = ['active', 'activo', 'activa', 'signed', 'firmado', 'sent', 'completed', 'confirmada', 'configured', 'draft'];
  const warning = ['pending', 'pendiente', 'pending_review', 'scheduled'];
  const negative = ['cancelled', 'cancelada', 'failed', 'inactive', 'inactivo', 'off', 'resolved'];
  const colorClass = positive.includes(normalized)
    ? 'bg-green-500/10 text-green-300'
    : warning.includes(normalized)
      ? 'bg-amber-500/10 text-amber-300'
      : negative.includes(normalized)
        ? 'bg-red-500/10 text-red-300'
        : 'bg-slate-800 text-slate-300';

  return <span className={clsx('inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize', colorClass)}>{normalized || '-'}</span>;
}

export function FilterInput({
  label,
  children,
}: PropsWithChildren<{ label: string }>) {
  return (
    <label className="block text-sm">
      <span className="text-slate-400">{label}</span>
      {children}
    </label>
  );
}

export function Modal({
  title,
  children,
  onClose,
  footer,
  width = 'max-w-2xl',
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  footer?: ReactNode;
  width?: string;
}) {
  return (
    <div className="fixed inset-0 z-20 overflow-y-auto">
      <div className="flex min-h-screen items-end justify-center px-4 pb-20 pt-4 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity" aria-hidden="true" onClick={onClose}>
          <div className="absolute inset-0 bg-slate-950 opacity-80" />
        </div>
        <span className="hidden sm:inline-block sm:h-screen sm:align-middle" aria-hidden="true">
          &#8203;
        </span>
        <div
          className={clsx(
            'inline-block w-full transform overflow-hidden rounded-lg border border-slate-800 bg-slate-900 text-left align-bottom shadow-xl transition-all sm:my-8 sm:align-middle',
            width
          )}
        >
          <div className="bg-slate-900 px-4 pb-4 pt-5 sm:p-6">
            <h3 className="mb-4 text-lg font-medium text-white">{title}</h3>
            {children}
          </div>
          {footer ? <div className="border-t border-slate-800 bg-slate-950 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">{footer}</div> : null}
        </div>
      </div>
    </div>
  );
}

export function ModalFormActions({
  submitLabel,
  onClose,
  submitting = false,
}: {
  submitLabel: string;
  onClose: () => void;
  submitting?: boolean;
}) {
  return (
    <>
      <button type="submit" form="modal-form" className={primaryButtonClassName} disabled={submitting}>
        {submitting ? 'Guardando...' : submitLabel}
      </button>
      <button type="button" onClick={onClose} className="mt-3 w-full sm:mr-3 sm:mt-0 sm:w-auto">
        <span className={clsx(secondaryButtonClassName, 'w-full')}>Cancelar</span>
      </button>
    </>
  );
}

export function SimpleForm({
  children,
  onSubmit,
  className = 'space-y-4',
}: {
  children: ReactNode;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  className?: string;
}) {
  return (
    <form id="modal-form" onSubmit={onSubmit} className={className}>
      {children}
    </form>
  );
}
