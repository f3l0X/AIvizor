# Manual de uso de AIvizor

Guía práctica para usar AIvizor. Para el diseño técnico, ver
[docs/architecture/](architecture/).

AIvizor es una herramienta **educativa** anti-phishing con dos módulos:
**Analizador** (disecciona un mensaje sospechoso) y **Entrenador** (te pone a
practicar). Funciona **sin registrarse**; las cuentas y la clave propia de IA
(BYOK) son opcionales.

---

## 1. Acceso

|               |                                                       |
| ------------- | ----------------------------------------------------- |
| Interfaz      | `http://localhost:3000/es` (español) · `/en` (inglés) |
| API / OpenAPI | `http://localhost:8000/docs`                          |

En la cabecera, en todo momento:

- **Analizador / Entrenador** — los dos módulos.
- **ES / EN** — cambia el idioma de la interfaz sin perder lo que estás haciendo.
- **🌙 / ☀️** — alterna tema claro/oscuro (se recuerda entre visitas).
- **Entrar / Crear cuenta** — o, si has iniciado sesión, tu correo y **Salir**.

---

## 2. Analizador

Pega un mensaje sospechoso y AIvizor te devuelve un análisis explicado.

**Pasos**

1. Entra en **Analizador**.
2. Pega el contenido en el área de texto (o pulsa **Cargar ejemplo** para probar).
3. Elige el **tipo de contenido**: Correo, URL o SMS.
4. Elige el **idioma del análisis** (independiente del idioma de la interfaz).
5. Pulsa **Analizar**.

**Cómo leer el resultado**

- **Riesgo (0–100)** — barra de score. Cuanto más alto, más sospechoso.
- **Veredicto** — `Legítimo`, `Sospechoso` o `Phishing`.
- **Resumen** — una frase con la conclusión.
- **Indicadores** — cada señal detectada, con:
  - *Tipo* (ver tabla abajo),
  - *Evidencia* (el fragmento concreto del mensaje),
  - *Explicación* (por qué es señal de engaño).

**Tipos de indicador**

| Tipo | Qué señala |
|---|---|
| Suplantación de remitente | El remitente finge ser otro. |
| Dominio parecido al legítimo | Dominio *look-alike* (p. ej. `bbva-seguro.ru`). |
| Enlace que no apunta a lo que dice | El texto del enlace y su destino real no coinciden. |
| Lenguaje de urgencia | Presión temporal o miedo ("actúa ya o..."). |
| Solicitud de credenciales | Pide usuario/contraseña/código. |
| Solicitud de pago | Pide un pago, tasa o datos bancarios. |
| Errores de marca o gramática | Logos/textos mal hechos, faltas. |
| Adjunto sospechoso | Adjunto peligroso o inesperado. |
| Otro | Señal que no encaja en las anteriores. |

> Los tipos disponibles dependen del formato: una **URL** casi solo admite
> "dominio parecido"; un **SMS** no tiene cabeceras ni adjuntos.

Si algo falla aparece un aviso explicando si fue un problema de conexión, del
contenido enviado o del motor de IA. El input no se borra: corrige y reintenta.

---

## 3. Entrenador

Practica detectando tú mismo, con dificultad que se adapta a tus aciertos.

**Pasos**

1. Entra en **Entrenador**.
2. Elige el **tipo de contenido** y el **nivel inicial** (1–5).
3. Pulsa **Empezar**: la IA genera un ejemplo (puede ser phishing… o legítimo).
4. Lee el ejemplo y responde:
   - **¿Cuál es tu veredicto?** Legítimo / Sospechoso / Phishing.
   - **¿Qué indicadores ves?** Marca todos los que apliquen.
5. Pulsa **Comprobar respuesta**.

**El feedback te dice**

- Si acertaste el veredicto (**✓ Correcto** / **✗ Incorrecto**) y tu **puntuación**.
- Los indicadores que **se te escaparon**.
- Los que **marcaste de más** (falsos positivos: desconfiar de lo legítimo también
  es un error).
- El **siguiente nivel**: sube si aciertas, baja si fallas.

Pulsa **Siguiente** para otro ejemplo al nivel ajustado.

> La "respuesta correcta" nunca se envía a tu navegador: la corrección la hace el
> servidor. No hay forma de hacer trampa mirando el código de la página.

---

## 4. Cuentas (opcional)

Registrarte **no es necesario** para analizar o entrenar. Sirve para aportar tu
propia clave de IA (siguiente apartado).

- **Crear cuenta** — correo + contraseña. La contraseña debe tener al menos
  8 caracteres, una mayúscula, una minúscula y un número (el formulario muestra
  un checklist que se va marcando al teclear); las contraseñas muy comunes
  (tipo `Password123`) se rechazan. Al registrarte inicias sesión automáticamente.
- **Iniciar sesión** — con tu correo y contraseña.
- **Salir** — cierra la sesión (botón junto a tu correo en la cabecera).

La sesión se guarda en una cookie segura; no tienes que copiar ni pegar ningún
token.

---

## 5. BYOK — usa tu propia clave de IA

Por defecto, los análisis usan la cuenta de IA del servidor. Con **BYOK** (*Bring
Your Own Key*) aportas tus propias claves de **Gemini** y/o **Claude**, y el
análisis y el entrenamiento consumen **tu** cuota. Puedes guardar **una clave por
proveedor** y elegir cuál está **activa**.

**Añadir una clave**

1. Inicia sesión y abre **Ajustes** (haz clic en tu correo en la cabecera).
2. En **Tu clave de IA (BYOK)**, pega tu **API key** — el proveedor se detecta
   solo por el prefijo (`AIza…` → Gemini, `sk-ant-…` → Claude).
3. (Opcional) elige un **modelo** del desplegable; "Por defecto del proveedor" si
   no estás seguro, o "Personalizado…" para escribir otro ID.
4. Pulsa **Guardar clave**. Antes de guardarla se **valida contra el proveedor**:
   si la clave o el modelo no valen, te avisa al momento y no se guarda nada.

Dónde obtener una clave:
- **Gemini** → Google AI Studio.
- **Claude** → consola de Anthropic.

**Gestionar tus claves**

- La lista muestra cada clave guardada con su máscara y un distintivo **Activa**
  en la que se está usando. La primera que guardas queda activa automáticamente.
- **Usar esta** — cambia qué clave está activa (Gemini ↔ Claude).
- **Reemplazar** — guarda otra clave del mismo proveedor y sustituye la anterior.
- **Eliminar** — borra esa clave; si era la activa y tienes otra, la otra pasa a
  activa. Sin claves, vuelves al proveedor del servidor.

**Importante**

- Las claves se **cifran** y solo verás una **máscara** (`••••wxyz`, los últimos 4
  caracteres). No se puede volver a mostrar entera: si la pierdes, genera otra y
  vuelve a guardarla.
- Si tu clave deja de ser válida más adelante, el análisis fallará de forma
  visible (no se usa en silencio la cuenta del servidor).

---

## 6. Panel de administración (solo administradores)

Si tu cuenta es **admin**, verás un distintivo **Admin** en la cabecera que enlaza
al panel (`/es/admin`).

Desde la tabla de usuarios puedes, por cada cuenta:

- **Hacer admin / Hacer usuario** — cambiar el rol.
- **Activar / Desactivar** — una cuenta desactivada no puede iniciar sesión.
- **Eliminar** — borra la cuenta (y su clave BYOK). Pide confirmación.

> **Tu propia fila** aparece marcada como *(tú)* con las acciones deshabilitadas:
> no puedes desactivarte, degradarte ni borrarte a ti mismo (evita quedarte sin
> acceso). Para cambiar tu cuenta, que lo haga otro administrador.

El primer administrador lo siembra el sistema al arrancar (variables
`ADMIN_EMAIL` / `ADMIN_PASSWORD`); a partir de ahí, un admin puede promover a otros.

---

## 7. Problemas frecuentes

| Síntoma | Probable causa / solución |
|---|---|
| "No se pudo conectar con el backend" | El backend no está corriendo o no es accesible en `localhost:8000`. |
| El análisis tarda o devuelve error 5xx | El proveedor de IA falló; reintenta en unos segundos. |
| Con BYOK, el análisis falla siempre | La clave guardada ya no es válida; vuelve a **Ajustes** y guárdala de nuevo. |
| No veo el panel admin | Tu cuenta no es admin; pídeselo a un administrador. |
| El idioma del análisis no es el de la interfaz | Son ajustes separados: revisa el selector "Idioma del análisis" en el formulario. |

---

¿Cómo se montó por dentro? Empieza por el [README](../README.md) y
[docs/architecture/](architecture/).
