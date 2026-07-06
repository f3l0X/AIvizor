/**
 * Política de contraseñas del formulario de registro.
 *
 * Espejo de los defaults del backend (app/security/passwords.py + config.py),
 * igual que INDICATORS_BY_INPUT_TYPE: es una decisión de UI para dar feedback
 * en vivo. La barrera real es el backend (422 con los códigos si no cumple);
 * si cambias la política por env en el servidor, ajusta también esta lista.
 */

export type PolicyCode = 'minLength' | 'uppercase' | 'lowercase' | 'digit';

export interface PolicyCheck {
  code: PolicyCode;
  met: boolean;
}

export const PASSWORD_MIN_LENGTH = 8;

/** Evalúa la contraseña contra la política; un item por requisito. */
export function checkPassword(password: string): PolicyCheck[] {
  return [
    { code: 'minLength', met: password.length >= PASSWORD_MIN_LENGTH },
    { code: 'uppercase', met: /[A-ZÁÉÍÓÚÑÜ]/.test(password) },
    { code: 'lowercase', met: /[a-záéíóúñü]/.test(password) },
    { code: 'digit', met: /[0-9]/.test(password) },
  ];
}

/** True si todos los requisitos se cumplen. */
export function passwordMeetsPolicy(password: string): boolean {
  return checkPassword(password).every((c) => c.met);
}
