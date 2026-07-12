# Rutina semanal · Sistema multiagente de inversión

Rutina **determinista** construida únicamente con el contenido del repositorio
[`jasalgad/inversiones`](https://github.com/jasalgad/inversiones): sus skills
(`.claude/skills/`), sus scripts (`scripts/`, `resultados/build_*.py`) y sus datos
versionados (`datos/*.csv`, watchlists). Mismo repo → mismos contratos → mismo hub.

> Material educativo, no recomendación de inversión (disclaimer heredado de todos los skills).

## Qué hace

Coordina el embudo completo que definen los skills del repo:

| Paso | Skill del repo | Script | Salida |
|---|---|---|---|
| 0 | — | `actualizar_acciones.py` | refresco opcional de `datos/*.csv` (yfinance) |
| 1 | `subagente-tecnico` | `scripts/analizar_tecnico.py` | `tecnico_raw.json` (velas semanales cerradas) |
| 2 | `subagente-tecnico` (método tendencial) | `build_fase_tendencial.py` | `fase_tendencial.json` |
| 3 | `screener-multiagente` (Nivel 0) | `build_screener.py` | `screener_nivel0.html` + `candidatas.json` |
| 4 | `subagente-macro` | `build_macro.py` | `contrato_macro.json` + `macro.html` |
| 5 | `subagente-sentimiento` | `build_fund_sent.py` | `contrato_sentimiento.json` + `sentimiento.html` |
| 6 | `subagente-fundamental` | `build_fundamental_stockanalysis.py` | `contrato_fundamental.json` (v2) |
| 7 | `subagente-tecnico` | `build_tecnico.py` | `contrato_tecnico.json` + `tecnico.html` |
| 8 | `hub-orquestador` | `build_hub.py` | `contrato_hub.json` + `hub.html` (radar 4 ejes) |

Todos los subagentes emiten el **contrato común** (`agente`, `score` 0-100, `signal`,
`evidence`, `datos_faltantes`) y el hub los funde **sin promediar a ciegas**: mide el
desacuerdo entre ejes (desviación estándar, umbral propuesto 18) y lo marca como bandera.

## Cómo ejecutarla

```bash
bash rutina/run_rutina.sh              # autodetecta el clon de inversiones
INVERSIONES_DIR=/ruta/al/clon bash rutina/run_rutina.sh
```

El runner se encarga de:

1. Crear los enlaces que esperan las rutas cableadas de los scripts del repo
   (`~/acciones_claude` y `/Users/jsalgado/acciones_claude` → clon).
2. Instalar `pandas` (y `yfinance` si hay red) si faltan.
3. Aplicar `patch_degradacion.py` (ver más abajo) sobre el clon local.
4. Ejecutar los 8 pasos en orden de dependencias.

## Degradación elegante (`patch_degradacion.py`)

Los skills exigen que un dato ausente se marque y degrade, **nunca se invente**.
En el entorno remoto solo están versionados los CSV del S&P 500, así que las candidatas
europeas (`AENA.MC`, `SAN.MC`, `AIR.MC`…) no tienen histórico local; además la lista de
candidatas de `build_hub.py` incluye tickers (NVDA, QCOM, REP.MC, ANDE, ADM) sin contrato
fundamental/sentimiento en los generadores versionados. Los builders originales fallan con
`KeyError` en ese caso, de modo que el parche —aplicado solo al clon local, nunca empujado
a `inversiones`— inserta el filtro que dictan los propios skills:

- `build_tecnico.py`: excluye candidatas sin `rsi14_semanal` (sin CSV local), avisando.
- `build_hub.py`: funde solo títulos con los 3 contratos por-título (fund, tec, sent), avisando.

Conjunto determinista resultante con el repo actual (2026-07): **JPM, GOOGL, AMGN, AAPL,
MU, XYZ** en el hub (CB y ADM tienen técnico pero no entran en la lista de candidatas del
hub / no tienen fund+sent completos).

## Programación (Routine de Claude Code)

Existe un *trigger* semanal que dispara esta rutina en la sesión de Claude Code:
**sábados 08:00 UTC** (`0 8 * * 6`), tras el cierre semanal del viernes — coherente con el
`subagente-tecnico`, que calcula solo sobre velas semanales **ya cerradas** (viernes a viernes).
Cada disparo ejecuta `run_rutina.sh` y presenta `hub.html` y `screener_nivel0.html`.

## Limitaciones conocidas (documentadas, no ocultas)

- **Yahoo Finance bloqueado por el proxy** del entorno remoto: el paso 0 degrada y se usan
  los CSV versionados en el repo. Para refrescar datos, ejecutar `actualizar_acciones.py`
  en local (Mac) y hacer push de `datos/`.
- **Macro / fundamental / sentimiento con datos embebidos** (consultados el 2026-07-01 según
  los propios scripts del repo): son deterministas pero envejecen. Refrescarlos = actualizar
  los `build_*.py` en `inversiones` (o pedir a los subagentes datos frescos vía web, fuera del
  modo "solo repo").
- Los pesos de fusión del hub (fund 35 / téc 25 / sent 20 / macro 20) y todos los umbrales
  son **propuestas debatibles** de los skills, no leyes.
