/**
 * Gestión de las claves BYOK del usuario (pantalla de ajustes).
 *
 * Multi-clave (Fase 7.6): el usuario guarda una clave por proveedor (gemini/claude)
 * y elige cuál está **activa** (la que usan Analyzer/Trainer). Flujo:
 *   - Al montar, `GET /api/keys` → lista (vacía si no hay).
 *   - `PUT /api/keys` crea/reemplaza la clave de un proveedor (la clave en claro solo
 *     entra; la respuesta viene enmascarada). La primera del usuario queda activa.
 *   - `PUT /api/keys/active` cambia la activa; `DELETE /api/keys/{provider}` la borra.
 *
 * `mock` no admite BYOK: el selector solo ofrece gemini/claude (espejo del backend).
 */

'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  deleteApiKey,
  getApiKeys,
  putApiKey,
  setActiveProvider,
} from '../lib/api';
import { errorMessage } from '../lib/errors';
import { BYOK_MODELS_BY_PROVIDER, type ApiKeyPublic, type ByokProvider } from '../lib/types';

const PROVIDERS: ByokProvider[] = ['gemini', 'claude'];

/** Valor centinela del <select> que activa el campo de modelo personalizado. */
const CUSTOM_MODEL = '__custom__';

/**
 * Adivina el proveedor por el prefijo de la clave: las de Claude empiezan por
 * `sk-ant-` y las de Gemini por `AIza`. Ajusta el desplegable solo al pegarla,
 * para no guardar una clave con el proveedor equivocado.
 */
function detectProvider(key: string): ByokProvider | null {
  const k = key.trim();
  if (k.startsWith('sk-ant-')) return 'claude';
  if (k.startsWith('AIza')) return 'gemini';
  return null;
}

export function ApiKeyManager() {
  const t = useTranslations('settings.byok');

  const [keys, setKeys] = useState<ApiKeyPublic[]>([]);
  const [loaded, setLoaded] = useState(false);

  // Campos del formulario de alta/reemplazo.
  const [provider, setProvider] = useState<ByokProvider>('gemini');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('');
  // El modelo se elige de un desplegable según el proveedor; "Personalizado"
  // revela un campo de texto para IDs que no estén en la lista.
  const [customModel, setCustomModel] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Cambiar de proveedor invalida el modelo elegido (los IDs no se comparten).
  const changeProvider = (next: ByokProvider) => {
    setProvider(next);
    setModel('');
    setCustomModel(false);
  };

  const refresh = async () => {
    setKeys(await getApiKeys());
  };

  const load = async () => {
    try {
      await refresh();
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

  /** Envuelve una acción: limpia avisos, marca busy y refresca la lista. */
  const run = async (action: () => Promise<void>, successKey: string) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      await refresh();
      setNotice(t(successKey));
    } catch (err) {
      setError(errorMessage(err, t));
    } finally {
      setBusy(false);
    }
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (apiKey.trim().length < 8) return;
    void run(async () => {
      await putApiKey({ provider, api_key: apiKey.trim(), model: model.trim() || null });
      setApiKey(''); // nunca conservamos la clave en claro en memoria de la UI
    }, 'saved');
  };

  const handleActivate = (p: ByokProvider) =>
    run(async () => {
      await setActiveProvider(p);
    }, 'activated');

  const handleDelete = (p: ByokProvider) =>
    run(async () => {
      await deleteApiKey(p);
    }, 'deleted');

  const canSave = apiKey.trim().length >= 8 && !busy;

  return (
    <section className="rounded-lg border border-slate-200 p-6 dark:border-slate-800">
      <h2 className="text-lg font-semibold">{t('title')}</h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{t('description')}</p>

      {error && (
        <div
          role="alert"
          className="mt-4 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        >
          {error}
        </div>
      )}
      {notice && (
        <div
          role="status"
          className="mt-4 rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200"
        >
          {notice}
        </div>
      )}

      {/* Claves guardadas */}
      <div className="mt-4">
        {!loaded ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">{t('loading')}</p>
        ) : keys.length === 0 ? (
          <p className="rounded-md bg-slate-100 p-3 text-sm text-slate-500 dark:bg-slate-900 dark:text-slate-400">
            {t('none')}
          </p>
        ) : (
          <ul className="space-y-2">
            {keys.map((k) => (
              <li
                key={k.provider}
                className={
                  k.is_active
                    ? 'flex flex-wrap items-center justify-between gap-2 rounded-md border border-brand/40 bg-brand/5 p-3 text-sm dark:bg-brand/10'
                    : 'flex flex-wrap items-center justify-between gap-2 rounded-md bg-slate-100 p-3 text-sm dark:bg-slate-900'
                }
              >
                <div>
                  <span className="font-medium">{t(`provider.${k.provider}`)}</span>
                  <span className="ml-2 font-mono text-slate-600 dark:text-slate-300">
                    {k.masked_key}
                  </span>
                  {k.model && (
                    <span className="ml-2 text-slate-500 dark:text-slate-400">({k.model})</span>
                  )}
                  {k.is_active && (
                    <span className="ml-2 rounded-full bg-brand/15 px-2 py-0.5 text-xs font-semibold text-brand">
                      {t('active')}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {!k.is_active && (
                    <button
                      type="button"
                      onClick={() => handleActivate(k.provider)}
                      disabled={busy}
                      className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                      {t('setActive')}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => handleDelete(k.provider)}
                    disabled={busy}
                    className="rounded-md border border-red-300 px-2.5 py-1 text-xs font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-50 dark:border-red-900 dark:text-red-300 dark:hover:bg-red-950/40"
                  >
                    {t('delete')}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Formulario de alta / reemplazo */}
      <form onSubmit={handleSave} className="mt-6 space-y-4">
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{t('formTitle')}</p>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label
              htmlFor="byok_provider"
              className="block text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              {t('providerLabel')}
            </label>
            <select
              id="byok_provider"
              value={provider}
              onChange={(e) => changeProvider(e.target.value as ByokProvider)}
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2 text-sm text-slate-900 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            >
              {PROVIDERS.map((p) => (
                <option key={p} value={p}>
                  {t(`provider.${p}`)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="byok_model"
              className="block text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              {t('modelLabel')}
            </label>
            <select
              id="byok_model"
              value={customModel ? CUSTOM_MODEL : model}
              onChange={(e) => {
                const v = e.target.value;
                if (v === CUSTOM_MODEL) {
                  setCustomModel(true);
                  setModel('');
                } else {
                  setCustomModel(false);
                  setModel(v);
                }
              }}
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2 text-sm text-slate-900 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            >
              <option value="">{t('modelDefault')}</option>
              {BYOK_MODELS_BY_PROVIDER[provider].map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
              <option value={CUSTOM_MODEL}>{t('modelCustom')}</option>
            </select>
            {customModel && (
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder={t('modelPlaceholder')}
                maxLength={64}
                aria-label={t('modelCustom')}
                className="mt-2 block w-full rounded-md border border-slate-300 bg-white p-2 font-mono text-sm text-slate-900 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
              />
            )}
          </div>
        </div>

        <div>
          <label
            htmlFor="byok_key"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            {t('keyLabel')}
          </label>
          <input
            id="byok_key"
            type="password"
            autoComplete="off"
            value={apiKey}
            onChange={(e) => {
              const v = e.target.value;
              setApiKey(v);
              // Si la clave delata su proveedor, ajusta el desplegable solo.
              const detected = detectProvider(v);
              if (detected && detected !== provider) changeProvider(detected);
            }}
            placeholder={t('keyPlaceholder')}
            minLength={8}
            maxLength={400}
            className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2.5 font-mono text-sm text-slate-900 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          />
        </div>

        <button
          type="submit"
          disabled={!canSave}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-slate-950"
        >
          {busy && (
            <span
              aria-hidden
              className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/40 border-t-white"
            />
          )}
          {t('save')}
        </button>
      </form>
    </section>
  );
}
