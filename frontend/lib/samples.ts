/**
 * Catálogo de ejemplos pre-cargables para el Analyzer.
 *
 * Sirven de "demo" cuando alguien entra a la página por primera vez y no tiene
 * un correo sospechoso a mano. Cubren los 3 tipos × 2 idiomas con escenarios
 * reconocibles (banca, paquetería, login corporativo). El contenido es
 * **inventado**: nombres y dominios obviamente falsos.
 */

import type { InputType, Language } from './types';

export type Sample = { input_type: InputType; content: string };

const ES: Record<InputType, Sample[]> = {
  email: [
    {
      input_type: 'email',
      content:
        'De: soporte@bbva-seguridad-online.ru\n' +
        'Asunto: ¡URGENTE!!! Su cuenta sera cerrada en 24h\n\n' +
        'Estimado cliente verifike sus datos AHORA en este link ' +
        'http://bbva-verificacion.ru/login o su cuenta sera CERRADA.',
    },
  ],
  url: [
    {
      input_type: 'url',
      content: 'https://paypa1-login.com/account/verify?session=xyz123',
    },
  ],
  sms: [
    {
      input_type: 'sms',
      content:
        'Correos: Tu paquete está pendiente. Abona 1,99€ de gestión en ' +
        'https://correos-postal.com/pagar para la nueva entrega.',
    },
  ],
};

const EN: Record<InputType, Sample[]> = {
  email: [
    {
      input_type: 'email',
      content:
        'From: support@chase-security-online.ru\n' +
        'Subject: URGENT!!! Your account will be CLOSED in 24h\n\n' +
        'Dear customer pleese verfy your data NOW at ' +
        'http://chase-verify.ru/login or your account will be CLOSED.',
    },
  ],
  url: [
    {
      input_type: 'url',
      content: 'https://paypa1-login.com/account/verify?session=xyz123',
    },
  ],
  sms: [
    {
      input_type: 'sms',
      content:
        'USPS: Your package is pending. Pay $1.99 handling at ' +
        'https://usps-postal.com/pay for the new delivery.',
    },
  ],
};

export function loadSampleFor(language: Language, inputType: InputType): Sample {
  const catalog = language === 'es' ? ES : EN;
  const pool = catalog[inputType];
  return pool[Math.floor(Math.random() * pool.length)];
}
