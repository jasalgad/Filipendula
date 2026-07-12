#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parche idempotente de "degradación elegante" para el clon de jasalgad/inversiones.

Los skills del sistema multiagente (subagente-tecnico, hub-orquestador) exigen que,
si falta un dato o un contrato, se degrade marcándolo — nunca inventar el eje ausente.
En el entorno remoto solo están versionados los CSV del S&P 500, así que las candidatas
europeas (AENA.MC, SAN.MC...) no tienen histórico local y los builders originales
(build_tecnico.py, build_hub.py) fallan con KeyError.

Este script inserta el filtro de degradación en el clon local ANTES de ejecutar el
pipeline. No modifica el repositorio remoto: el parche vive aquí, en Filipendula.

Uso: python3 patch_degradacion.py /ruta/al/clon/de/inversiones
"""
import sys

BLOQUE_TECNICO = '''

# [rutina Filipendula] Degradación elegante (regla del skill): si una candidata no tiene
# histórico local (sin CSV en datos/ -> sin rsi14_semanal), se excluye en vez de inventar el eje.
SIN_DATOS = [t for t in CANDIDATAS if "rsi14_semanal" not in raw_by_t.get(t, {})]
if SIN_DATOS:
    print(f"AVISO · candidatas sin datos locales, excluidas del contrato: {SIN_DATOS}")
CANDIDATAS = [t for t in CANDIDATAS if t not in SIN_DATOS]
'''

BLOQUE_HUB = '''

# [rutina Filipendula] Degradación elegante (regla del skill): el hub solo funde títulos con
# los 3 contratos por-título disponibles (fund, tec, sent); los ausentes se marcan, no se inventan.
EXCLUIDAS = [t for t in CANDIDATAS if t not in tecnico or t not in fund or t not in sent]
if EXCLUIDAS:
    print(f"AVISO · candidatas sin los 4 ejes completos, excluidas de la fusión: {EXCLUIDAS}")
CANDIDATAS = [t for t in CANDIDATAS if t not in EXCLUIDAS]
'''


def parchear(ruta, ancla, bloque, guarda):
    with open(ruta, encoding="utf-8") as f:
        src = f.read()
    if guarda in src:
        return f"{ruta}: ya parcheado"
    if ancla not in src:
        raise SystemExit(f"ERROR: ancla no encontrada en {ruta} (¿cambió el script upstream?)")
    src = src.replace(ancla, ancla + bloque, 1)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(src)
    return f"{ruta}: parcheado"


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Uso: patch_degradacion.py /ruta/al/clon/de/inversiones")
    repo = sys.argv[1].rstrip("/")

    print(parchear(
        f"{repo}/resultados/build_tecnico.py",
        'fase = json.load(open("/Users/jsalgado/acciones_claude/resultados/fase_tendencial.json", encoding="utf-8"))',
        BLOQUE_TECNICO,
        "SIN_DATOS",
    ))
    print(parchear(
        f"{repo}/resultados/build_hub.py",
        'CANDIDATAS = ["JPM","GOOGL","AMGN","AAPL","AENA.MC","SAN.MC","TSM","MU","NVDA","QCOM","AIR.MC","REP.MC","XYZ","ADM","ANDE"]',
        BLOQUE_HUB,
        "EXCLUIDAS",
    ))


if __name__ == "__main__":
    main()
