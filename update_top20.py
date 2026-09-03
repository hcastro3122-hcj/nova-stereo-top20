import json
import urllib.request
import re
from datetime import datetime, timezone

OUTPUT_FILE = "top20.json"

URLS = [
    "https://www.billboard.com/charts/latin-songs/",
    "https://www.billboard.com/charts/billboard-global-200/"
]


def obtener_pagina(url):
    solicitud = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(solicitud, timeout=30) as respuesta:
        return respuesta.read().decode("utf-8", errors="ignore")


def limpiar(texto):
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def obtener_canciones(html):
    canciones = []

    patrones = [
        r'<h2[^>]class="[^"]*c-title[^"]"[^>]>(.?)</h2>',
        r'<h2[^>]>(.?)</h2>'
    ]

    titulos = []

    for patron in patrones:
        encontrados = re.findall(
            patron,
            html,
            re.IGNORECASE | re.DOTALL
        )

        for elemento in encontrados:
            titulo = limpiar(elemento)

            if (
                titulo
                and len(titulo) > 1
                and titulo not in titulos
            ):
                titulos.append(titulo)

    for titulo in titulos:
        canciones.append({
            "title": titulo,
            "artist": "Artista"
        })

        if len(canciones) >= 20:
            break

    return canciones


def generar_top20():
    canciones = []
    utilizadas = set()

    for url in URLS:
        try:
            print("Consultando:", url)

            html = obtener_pagina(url)
            resultados = obtener_canciones(html)

            for cancion in resultados:
                clave = cancion["title"].lower()

                if clave in utilizadas:
                    continue

                utilizadas.add(clave)
                canciones.append(cancion)

                if len(canciones) >= 20:
                    break

        except Exception as error:
            print("Error consultando fuente:", error)

        if len(canciones) >= 20:
            break

    if len(canciones) == 0:
        raise RuntimeError(
            "No se pudieron obtener canciones de Internet."
        )

    canciones = canciones[:20]

    resultado = {
        "name": "TOP 20 NOVA",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "songs": []
    }

    numero = 1

    for cancion in canciones:
        resultado["songs"].append({
            "position": numero,
            "title": cancion["title"],
            "artist": cancion["artist"]
        })

        numero += 1

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as archivo:
        json.dump(
            resultado,
            archivo,
            ensure_ascii=False,
            indent=2
        )

    print("TOP 20 NOVA generado correctamente.")
    print("Canciones:", len(canciones))


generar_top20()