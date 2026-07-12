#!/usr/bin/env bash
# =============================================================================
# Rutina semanal del sistema multiagente de inversión (jasalgad/inversiones)
#
# Ejecuta, SOLO con el contenido del repositorio inversiones, el pipeline:
#
#   1. actualizar_acciones.py        (intento de refresco vía yfinance; opcional)
#   2. scripts/analizar_tecnico.py   -> resultados/tecnico_raw.json
#   3. build_fase_tendencial.py      -> fase_tendencial.json
#   4. build_screener.py             -> screener_nivel0.html + candidatas.json   (SCREENER · Nivel 0)
#   5. build_macro.py                -> contrato_macro.json + macro.html         (SUBAGENTE MACRO)
#   6. build_fund_sent.py            -> contrato_sentimiento.json + sentimiento.html (SUBAGENTE SENTIMIENTO)
#      build_fundamental_stockanalysis.py -> contrato_fundamental.json + HTML    (SUBAGENTE FUNDAMENTAL v2)
#   7. build_tecnico.py              -> contrato_tecnico.json + tecnico.html     (SUBAGENTE TÉCNICO)
#   8. build_hub.py                  -> contrato_hub.json + hub.html             (HUB ORQUESTADOR)
#
# El resultado es determinista: mismo repo -> mismos contratos -> mismo hub.
# =============================================================================
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Localizar el clon de inversiones -----------------------------------------
REPO="${INVERSIONES_DIR:-}"
if [ -z "$REPO" ]; then
  for cand in /workspace/inversiones "$HOME/inversiones" /home/user/inversiones; do
    if [ -f "$cand/actualizar_acciones.py" ]; then REPO="$cand"; break; fi
  done
fi
if [ -z "$REPO" ] || [ ! -f "$REPO/actualizar_acciones.py" ]; then
  echo "ERROR: no se encontró el clon de jasalgad/inversiones."
  echo "Clónalo (git clone https://github.com/jasalgad/inversiones) o exporta INVERSIONES_DIR."
  exit 1
fi
echo "== Repo inversiones: $REPO"

# --- Enlaces para las rutas cableadas de los scripts del repo -----------------
# actualizar_acciones.py usa ~/acciones_claude; los build_*.py usan /Users/jsalgado/acciones_claude.
[ -d "$HOME/acciones_claude" ] && [ ! -L "$HOME/acciones_claude" ] && rm -rf "$HOME/acciones_claude"
ln -sfn "$REPO" "$HOME/acciones_claude"
if mkdir -p /Users/jsalgado 2>/dev/null; then
  [ -d /Users/jsalgado/acciones_claude ] && [ ! -L /Users/jsalgado/acciones_claude ] && rm -rf /Users/jsalgado/acciones_claude
  ln -sfn "$REPO" /Users/jsalgado/acciones_claude
else
  echo "ERROR: no se pudo crear /Users/jsalgado (los build_*.py del repo usan esa ruta cableada)."
  exit 1
fi

# --- Dependencias --------------------------------------------------------------
python3 -c "import pandas" 2>/dev/null || pip install -q pandas
python3 -c "import yfinance" 2>/dev/null || pip install -q yfinance || true

# --- Parche de degradación elegante (idempotente, solo en el clon local) ------
python3 "$AQUI/patch_degradacion.py" "$REPO"

# --- 1 · Refresco de datos (opcional: Yahoo suele estar bloqueado por el proxy) -
echo "== 1/8 actualizar_acciones.py (refresco opcional vía yfinance)"
if (cd "$REPO" && timeout 420 python3 actualizar_acciones.py --watchlist watchlist.csv); then
  echo "   refresco intentado (ver arriba cuántos tickers se descargaron)"
else
  echo "   AVISO: sin acceso a Yahoo Finance; se usan los CSV versionados en datos/"
fi

# --- 2 · Subagente técnico: indicadores sobre velas semanales cerradas ---------
echo "== 2/8 analizar_tecnico.py -> tecnico_raw.json"
TICKERS=$(tail -n +2 "$REPO/watchlist.csv" | cut -d, -f1 | tr '\n' ' ')
(cd "$REPO" && python3 scripts/analizar_tecnico.py $TICKERS --carpeta "$REPO" > resultados/tecnico_raw.json)

# --- 3-8 · Builders del pipeline (screener -> subagentes -> hub) ----------------
cd "$REPO/resultados"
echo "== 3/8 build_fase_tendencial.py";           python3 build_fase_tendencial.py | tail -1
echo "== 4/8 build_screener.py (Nivel 0)";        python3 build_screener.py | tail -2
echo "== 5/8 build_macro.py (subagente macro)";   python3 build_macro.py > /dev/null && echo "   contrato_macro.json + macro.html"
echo "== 6/8 build_fund_sent.py + build_fundamental_stockanalysis.py (fund + sent)"
python3 build_fund_sent.py > /dev/null && echo "   contrato_sentimiento.json + sentimiento.html"
python3 build_fundamental_stockanalysis.py > /dev/null && echo "   contrato_fundamental.json (v2 stockanalysis)"
echo "== 7/8 build_tecnico.py (subagente técnico)"; python3 build_tecnico.py | tail -3
echo "== 8/8 build_hub.py (HUB orquestador)";       python3 build_hub.py

echo ""
echo "== RUTINA COMPLETA. Salidas en $REPO/resultados/:"
ls -la "$REPO/resultados/"*.html "$REPO/resultados/"contrato_*.json "$REPO/resultados/"candidatas.json 2>/dev/null
