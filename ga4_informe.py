"""Informe de Google Analytics 4 (últimos 28 días) por origen/medio.

Saca sesiones, usuarios activos, tiempo de interacción y eventos clave
desglosados por origen/medio de la sesión y los guarda en un CSV.

Variables de entorno:
    GA4_CREDENTIALS_PATH  Ruta al JSON de la cuenta de servicio
                          (si no está, se usa GOOGLE_APPLICATION_CREDENTIALS).
    GA4_PROPERTY_ID       ID numérico de la propiedad de GA4 (p. ej. 123456789).

Uso:
    pip install -r requirements.txt
    export GA4_CREDENTIALS_PATH=/ruta/a/clave.json
    export GA4_PROPERTY_ID=123456789
    python ga4_informe.py [--salida informe.csv]

La cuenta de servicio debe tener acceso (rol Lector) a la propiedad de GA4.
"""

import argparse
import csv
import os
import sys
from datetime import date

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    RunReportRequest,
)
from google.oauth2 import service_account

DIMENSION = "sessionSourceMedium"
METRICAS = ["sessions", "activeUsers", "userEngagementDuration", "keyEvents"]
CABECERA = [
    "origen_medio",
    "sesiones",
    "usuarios_activos",
    "tiempo_interaccion_seg",
    "tiempo_interaccion_medio_por_usuario_seg",
    "eventos_clave",
]
TAMANO_PAGINA = 10000
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def leer_config():
    ruta_clave = os.environ.get("GA4_CREDENTIALS_PATH") or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )
    property_id = os.environ.get("GA4_PROPERTY_ID")

    faltan = []
    if not ruta_clave:
        faltan.append("GA4_CREDENTIALS_PATH (o GOOGLE_APPLICATION_CREDENTIALS)")
    if not property_id:
        faltan.append("GA4_PROPERTY_ID")
    if faltan:
        sys.exit("Faltan variables de entorno: " + ", ".join(faltan))
    if not os.path.isfile(ruta_clave):
        sys.exit(f"No se encuentra el archivo de credenciales: {ruta_clave}")

    # Admite tanto "123456789" como "properties/123456789".
    property_id = property_id.strip().removeprefix("properties/")
    return ruta_clave, property_id


def obtener_filas(cliente, property_id):
    """Ejecuta el informe paginando hasta recoger todas las filas."""
    filas = []
    offset = 0
    while True:
        peticion = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name=DIMENSION)],
            metrics=[Metric(name=m) for m in METRICAS],
            date_ranges=[DateRange(start_date="28daysAgo", end_date="yesterday")],
            order_bys=[
                OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)
            ],
            limit=TAMANO_PAGINA,
            offset=offset,
        )
        respuesta = cliente.run_report(peticion)
        for fila in respuesta.rows:
            origen_medio = fila.dimension_values[0].value
            sesiones, usuarios, duracion, eventos = (
                float(v.value or 0) for v in fila.metric_values
            )
            filas.append(
                [
                    origen_medio,
                    int(sesiones),
                    int(usuarios),
                    round(duracion, 1),
                    round(duracion / usuarios, 1) if usuarios else 0,
                    round(eventos, 2),
                ]
            )
        offset += len(respuesta.rows)
        if not respuesta.rows or offset >= respuesta.row_count:
            return filas


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--salida",
        default=f"ga4_origen_medio_{date.today():%Y%m%d}.csv",
        help="Ruta del CSV de salida (por defecto ga4_origen_medio_AAAAMMDD.csv)",
    )
    args = parser.parse_args()

    ruta_clave, property_id = leer_config()
    credenciales = service_account.Credentials.from_service_account_file(
        ruta_clave, scopes=SCOPES
    )
    cliente = BetaAnalyticsDataClient(credentials=credenciales)

    filas = obtener_filas(cliente, property_id)

    with open(args.salida, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(CABECERA)
        escritor.writerows(filas)

    print(f"{len(filas)} filas guardadas en {args.salida}")


if __name__ == "__main__":
    main()
