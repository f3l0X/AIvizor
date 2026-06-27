/**
 * Utilidades de tema (claro/oscuro) compartidas entre el script anti-FOUC y el
 * componente ThemeToggle.
 *
 * Fuente de verdad: la clase `dark` en <html>. La preferencia explícita se
 * guarda en localStorage['theme'] ∈ {"light","dark"}. Si no hay preferencia
 * guardada, se respeta `prefers-color-scheme` del SO.
 */

export type Theme = 'light' | 'dark';

export const THEME_STORAGE_KEY = 'theme';

/** Snippet que corre ANTES del primer render para evitar el flash de tema.
 * Se inyecta como <script> inline en el <head> del layout. */
export const themeInitScript = `(function(){try{
  var t = localStorage.getItem('${THEME_STORAGE_KEY}');
  var dark = t ? t === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.classList.toggle('dark', dark);
}catch(e){}})();`;

/** Preferencia efectiva: lo guardado en localStorage o, si no hay, el SO.
 * Esta es la FUENTE DE VERDAD para reimponer el tema tras una navegación —
 * no leemos la clase del <html> porque puede haberse perdido en el re-render
 * del layout al cambiar de locale. */
export function getStoredPreference(): Theme {
  try {
    const t = localStorage.getItem(THEME_STORAGE_KEY);
    if (t === 'dark' || t === 'light') return t;
  } catch {
    // localStorage no disponible
  }
  if (
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches
  ) {
    return 'dark';
  }
  return 'light';
}

/** Aplica el tema a la clase del <html> SIN persistir. Para sincronizar tras
 * navegar (no queremos "fijar" la preferencia del SO como elección explícita). */
export function applyThemeClass(theme: Theme): void {
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

/** Elección explícita del usuario (click en el toggle): aplica y persiste. */
export function applyTheme(theme: Theme): void {
  applyThemeClass(theme);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // localStorage no disponible (modo privado, etc.) — el toggle aún funciona en memoria.
  }
}
