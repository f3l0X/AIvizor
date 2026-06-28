/**
 * Tabla de gestión de usuarios del panel admin.
 *
 * Lista los usuarios y permite, por fila: activar/desactivar, alternar el rol
 * (user ↔ admin) y borrar la cuenta. La fila del propio admin tiene las acciones
 * deshabilitadas: el backend las rechaza con 400 (no auto-bloqueo), aquí solo
 * evitamos ofrecer un botón que fallaría.
 *
 * Tras cada acción re-sincroniza la lista con la respuesta del backend (la
 * fuente de verdad), sin recargar la página.
 */

'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { useAuth } from './AuthProvider';
import { adminDeleteUser, adminListUsers, adminUpdateUser } from '../lib/api';
import { errorMessage } from '../lib/errors';
import type { UserPublic } from '../lib/types';

export function AdminUserTable() {
  const t = useTranslations('admin');
  const { user: me } = useAuth();

  const [users, setUsers] = useState<UserPublic[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async () => {
    try {
      setUsers(await adminListUsers());
    } catch (e) {
      setError(errorMessage(e, t));
    } finally {
      setLoaded(true);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Reemplaza una fila con la versión devuelta por el backend. */
  const replace = (updated: UserPublic) =>
    setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));

  const toggleActive = async (u: UserPublic) => {
    setBusyId(u.id);
    setError(null);
    try {
      replace(await adminUpdateUser(u.id, { is_active: !u.is_active }));
    } catch (e) {
      setError(errorMessage(e, t));
    } finally {
      setBusyId(null);
    }
  };

  const toggleRole = async (u: UserPublic) => {
    setBusyId(u.id);
    setError(null);
    try {
      replace(await adminUpdateUser(u.id, { role: u.role === 'admin' ? 'user' : 'admin' }));
    } catch (e) {
      setError(errorMessage(e, t));
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (u: UserPublic) => {
    if (!window.confirm(t('confirmDelete', { email: u.email }))) return;
    setBusyId(u.id);
    setError(null);
    try {
      await adminDeleteUser(u.id);
      setUsers((prev) => prev.filter((x) => x.id !== u.id));
    } catch (e) {
      setError(errorMessage(e, t));
    } finally {
      setBusyId(null);
    }
  };

  if (!loaded) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">{t('loading')}</p>;
  }

  return (
    <div>
      {error && (
        <div
          role="alert"
          className="mb-4 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        >
          {error}
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
            <tr>
              <th className="px-4 py-3 font-medium">{t('table.email')}</th>
              <th className="px-4 py-3 font-medium">{t('table.role')}</th>
              <th className="px-4 py-3 font-medium">{t('table.status')}</th>
              <th className="px-4 py-3 text-right font-medium">{t('table.actions')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {users.map((u) => {
              const isSelf = u.id === me?.id;
              const busy = busyId === u.id;
              return (
                <tr key={u.id} className="align-middle">
                  <td className="px-4 py-3">
                    <span className="font-medium">{u.email}</span>
                    {isSelf && (
                      <span className="ml-2 text-xs text-slate-400">{t('you')}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        u.role === 'admin'
                          ? 'rounded-full bg-brand/10 px-2 py-0.5 text-xs font-semibold text-brand dark:bg-brand/20'
                          : 'text-slate-600 dark:text-slate-300'
                      }
                    >
                      {t(`roles.${u.role}`)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {u.is_active ? (
                      <span className="inline-flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                        {t('status.active')}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
                        <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
                        {t('status.inactive')}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => toggleRole(u)}
                        disabled={isSelf || busy}
                        className="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                      >
                        {u.role === 'admin' ? t('actions.demote') : t('actions.promote')}
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleActive(u)}
                        disabled={isSelf || busy}
                        className="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                      >
                        {u.is_active ? t('actions.deactivate') : t('actions.activate')}
                      </button>
                      <button
                        type="button"
                        onClick={() => remove(u)}
                        disabled={isSelf || busy}
                        className="rounded-md border border-red-300 px-2 py-1 text-xs font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-red-900 dark:text-red-300 dark:hover:bg-red-950/40"
                      >
                        {t('actions.delete')}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
