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

export function getCurrentTheme(): Theme {
  if (typeof document === 'undefined') return 'light';
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // localStorage no disponible (modo privado, etc.) — el toggle aún funciona en memoria.
  }
}
