import json
import re
import urllib.request
from datetime import datetime, timezone
from collections import defaultdict


OUTPUT_FILE = "top20.json"


SPOTIFY_SOURCES = [
    {
        "name": "Spotify Costa Rica",
        "url": "https://open.spotify.com/embed/playlist/37i9dQZEVXbMZAjGMynsQX"
    },
    {
        "name": "Spotify Global",
        "url": "https://open.spotify.com/embed/playlist/37i9dQZEVXbMDoHDwVN2tF"
    },
    {
        "name": "Spotify Mexico",
        "url": "https://open.spotify.com/embed/playlist/37i9dQZEVXbO3qyFxbkOE1"
    }
]


APPLE_SOURCES = [
    {
        "name": "Apple Music USA",
        "url": "https://rss.applemarketingtools.com/api/v2/us/music/most-played/100/songs.json"
    },
    {
        "name": "Apple Music Mexico",
        "url": "https://rss.applemarketingtools.com/api/v2/mx/music/most-played/100/songs.json"
    },
    {
        "name": "Apple Music Costa Rica",
        "url": "https://rss.applemarketingtools.com/api/v2/cr/music/most-played/100/songs.json"
    }
]


def descargar(url):
    solicitud = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/128.0 Safari/537.36"
            ),
            "Accept": "application/json,text/html,/"
        }
    )

    with urllib.request.urlopen(solicitud, timeout=30) as respuesta:
        return respuesta.read().decode("utf-8", errors="ignore")


def limpiar(texto):
    texto = re.sub(r"<[^>]*>", " ", texto)
    texto = texto.replace("&amp;", "&")
    texto = texto.replace("&quot;", '"')
    texto = texto.replace("&#x27;", "'")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def agregar_cancion(
    canciones,
    titulo,
    artista,
    posicion,
    fuente
):
    titulo = limpiar(titulo)
    artista = limpiar(artista)

    if not titulo:
        return

    if titulo.lower() in {
        "",
        "title",
        "album",
        "list",
        "image"
    }:
        return

    clave = (
        titulo.lower(),
        artista.lower()
    )

    canciones[clave]["title"] = titulo
    canciones[clave]["artist"] = artista
    canciones[clave]["sources"].add(fuente)

    puntos = max(1, 101 - posicion)

    canciones[clave]["score"] += puntos


def obtener_spotify(html, fuente, canciones):
    patron = re.compile(
        r"<h3[^>]>(.?)</h3>\s*"
        r"<h4[^>]>(.?)</h4>",
        re.IGNORECASE | re.DOTALL
    )

    resultados = patron.findall(html)

    posicion = 1

    for titulo, artista in resultados:
        agregar_cancion(
            canciones,
            titulo,
            artista,
            posicion,
            fuente
        )

        posicion += 1

        if posicion > 50:
            break

    if resultados:
        return

    patrones_titulo = [
        r"<h3[^>]>(.?)</h3>",
        r'<div[^>]data-testid="tracklist-row"[^>]>'
    ]

    titulos = []

    for patron_titulo in patrones_titulo:
        encontrados = re.findall(
            patron_titulo,
            html,
            re.IGNORECASE | re.DOTALL
        )

        for elemento in encontrados:
            texto = limpiar(elemento)

            if texto and texto not in titulos:
                titulos.append(texto)

    for posicion, titulo in enumerate(
        titulos[:50],
        start=1
    ):
        agregar_cancion(
            canciones,
            titulo,
            "Artista",
            posicion,
            fuente
        )


def obtener_apple(datos, fuente, canciones):
    contenido = json.loads(datos)

    resultados = (
        contenido
        .get("feed", {})
        .get("results", [])
    )

    for posicion, cancion in enumerate(
        resultados,
        start=1
    ):
        titulo = cancion.get("name", "")
        artista = cancion.get(
            "artistName",
            "Artista"
        )

        agregar_cancion(
            canciones,
            titulo,
            artista,
            posicion,
            fuente
        )


def construir_ranking():
    canciones = defaultdict(
        lambda: {
            "title": "",
            "artist": "",
            "score": 0,
            "sources": set()
        }
    )

    fuentes_exitosas = 0

    print()
    print("FUENTES DE NOVA STEREO")
    print("----------------------")

    for fuente in SPOTIFY_SOURCES:
        try:
            print(
                "Consultando:",
                fuente["name"]
            )

            html = descargar(
                fuente["url"]
            )

            antes = len(canciones)

            obtener_spotify(
                html,
                fuente["name"],
                canciones
            )

            if len(canciones) > antes:
                fuentes_exitosas += 1
                print("OK:", fuente["name"])
            else:
                print(
                    "Sin canciones:",
                    fuente["name"]
                )

        except Exception as error:
            print(
                "Error en",
                fuente["name"],
                ":",
                error
            )

    for fuente in APPLE_SOURCES:
        try:
            print(
                "Consultando:",
                fuente["name"]
            )

            datos = descargar(
                fuente["url"]
            )

            antes = len(canciones)

            obtener_apple(
                datos,
                fuente["name"],
                canciones
            )

            if len(canciones) > antes:
                fuentes_exitosas += 1
                print("OK:", fuente["name"])
            else:
                print(
                    "Sin canciones:",
                    fuente["name"]
                )

        except Exception as error:
            print(
                "Error en",
                fuente["name"],
                ":",
                error
            )

    if fuentes_exitosas == 0:
        raise RuntimeError(
            "No se pudo obtener información "
            "de ninguna fuente musical."
        )

    lista = []

    for cancion in canciones.values():

        cantidad_fuentes = len(
            cancion["sources"]
        )

        # Premio por aparecer en varias fuentes.
        bonificacion = cantidad_fuentes * 35

        # Premio especial por presencia en Costa Rica.
        presencia_cr = any(
            "Costa Rica" in fuente
            for fuente in cancion["sources"]
        )

        if presencia_cr:
            bonificacion += 80

        puntaje_final = (
            cancion["score"]
            + bonificacion
        )

        lista.append({
            "title": cancion["title"],
            "artist": cancion["artist"],
            "score": puntaje_final,
            "sources": sorted(
                cancion["sources"]
            )
        })

    lista.sort(
        key=lambda elemento: (
            elemento["score"],
            len(elemento["sources"])
        ),
        reverse=True
    )

    return lista[:20]


def guardar(ranking):
    resultado = {
        "name": "TOP 20 NOVA",
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "sources": [
            "Spotify Costa Rica",
            "Spotify Global",
            "Spotify Mexico",
            "Apple Music USA",
            "Apple Music Mexico",
            "Apple Music Costa Rica"
        ],
        "songs": []
    }

    for posicion, cancion in enumerate(
        ranking,
        start=1
    ):
        resultado["songs"].append({
            "position": posicion,
            "title": cancion["title"],
            "artist": cancion["artist"],
            "score": cancion["score"],
            "sources": cancion["sources"]
        })

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


def iniciar():
    print()
    print("========================================")
    print("       TOP 20 NOVA")
    print("       RANKING MUSICAL AUTOMATICO")
    print("========================================")

    ranking = construir_ranking()

    if len(ranking) < 20:
        print(
            "Advertencia: solamente se encontraron",
            len(ranking),
            "canciones."
        )

    guardar(ranking)

    print()
    print("TOP 20 NOVA ACTUALIZADO")
    print("------------------------")

    for cancion in ranking:
        print(
            f"{ranking.index(cancion) + 1:02d}. "
            f"{cancion['title']} - "
            f"{cancion['artist']}"
        )

    print()
    print(
        "Archivo generado:",
        OUTPUT_FILE
    )
    print()


iniciar()