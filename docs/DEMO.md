# Guion de grabación del GIF de demo

> Objetivo: un GIF corto (20-35 s) que muestre los dos módulos con **salida real
> de IA**. Se enlaza desde el README (`docs/demo.gif`).

## 0. Entorno listo para grabar

Ya configurado en esta sesión (si reinicias la máquina, repite estos pasos):

```bash
# Backend con Gemini real (salida de verdad, no mock)
#   .env -> LLM_PROVIDER=gemini ; GEMINI_MODEL=gemini-2.5-flash ; GEMINI_API_KEY=...
docker compose up -d backend
docker compose exec backend alembic upgrade head   # solo la 1ª vez

# Frontend en build de PRODUCCIÓN (sin el banner/overlay de dev, más limpio para el GIF)
cd frontend
NEXT_PUBLIC_API_URL=http://localhost:8000 npx next build
NEXT_PUBLIC_API_URL=http://localhost:8000 npx next start -p 3001
```

- Grabar sobre **http://localhost:3001** (producción, limpio).
- Alternativa rápida sin build: el dev de Docker en http://localhost:3000 (sale el
  indicador de Next dev en una esquina; menos pulcro pero válido).

## 1. Herramienta de captura

**ScreenToGif** (Windows, gratis): https://www.screentogif.com/
- Recorder → encuadra **solo la ventana del navegador** (no toda la pantalla).
- 15-20 FPS basta. Recorta el ratón parado al final.
- Exporta optimizando colores; objetivo < 8 MB para que GitHub lo muestre inline.

Pon el navegador a ~1280×860 y zoom 100 %. Tema claro u oscuro, a gusto (la app
soporta ambos por `prefers-color-scheme`).

## 2. Storyboard

### Toma A — Analizador (≈12 s)

1. Abre **http://localhost:3001/es/analyze**.
2. Pulsa **"Cargar ejemplo"** (rellena un phishing de muestra) — o pega este texto:

   ```
   De: soporte@bbva-seguridad.ru
   Asunto: Verifique su cuenta YA

   Estimado cliente, detectamos actividad sospechosa. Verifique sus datos en
   http://bbva-verificacion.ru/login antes de 24h o su cuenta sera bloqueada.
   ```

3. Pulsa **"Analizar"**. Espera la respuesta (spinner → resultado).
4. Deja ver el **RiskMeter** (score alto + "phishing" en rojo) y baja despacio por
   los **IndicatorCard** (dominio look-alike, urgencia, link mismatch...).

> Punch line visual: score ~95/100, varios indicadores con evidencia y explicación.

### Toma B — cambio de idioma (≈4 s, opcional)

5. Cambia la URL a **/en/analyze** (o el selector de idioma del formulario a English)
   y repite un análisis rápido para enseñar el bilingüe.

### Toma C — Entrenador (≈14 s)

6. Abre **http://localhost:3001/es/train**.
7. Deja ver el *empty state*, elige **dificultad 2-3** y **Correo**, pulsa **Empezar**.
8. Lee el ejemplo generado, marca un **veredicto** y un par de **indicadores**,
   pulsa **Comprobar respuesta**.
9. Muestra el **feedback**: ✓ aciertos en verde, ✗ falsos positivos en rojo,
   ⚠ los que se escaparon, score y explicación.
10. Pulsa **"Siguiente (nivel N)"** una vez para enseñar la dificultad adaptativa.

## 3. Después de grabar

```bash
# guardar el gif aquí:
docs/demo.gif

# enlazarlo en el README (la sección ya existe, ver abajo)
git add docs/demo.gif && git commit -m "docs: añadir GIF de demo" && git push
```

Para parar el entorno de grabación y volver a coste cero:

```bash
# parar el server de producción (Ctrl+C en su terminal, o)
#   busca el proceso de next start -p 3001 y ciérralo
# devolver el backend a mock:
#   .env -> LLM_PROVIDER=mock
docker compose up -d backend
```
