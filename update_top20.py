import json
import re
import time
import urllib.request
import urllib.parse
from html import unescape


# ============================================================
# TOP 20 NOVA
# Tendencias actuales - prioridad Latinoamérica
# ============================================================

OUTPUT_FILE = "top20.json"


SOURCES = [

    # Costa Rica - máxima prioridad
    (
        "spotify_cr",
        "https://open.spotify.com/embed/playlist/37i9dQZEVXbMZAjGMynsQX"
    ),

    # México
    (
        "spotify_mx",
        "https://open.spotify.com/embed/playlist/37i9dQZEVXbO3qyFxbkOE1"
    ),

    # Global
    (
        "spotify_global",
        "https://open.spotify.com/embed/playlist/37i9dQZEVXbMDoHDwVN2tF"
    ),

    # Apple Music - Costa Rica
    (
        "apple_cr",
        "https://rss.applemarketingtools.com/api/v2/cr/music/most-played/100/songs.json"
    ),

    # Apple Music - México
    (
        "apple_mx",
        "https://rss.applemarketingtools.com/api/v2/mx/music/most-played/100/songs.json"
    ),

    # Apple Music - Estados Unidos / referencia global
    (
        "apple_us",
        "https://rss.applemarketingtools.com/api/v2/us/music/most-played/100/songs.json"
    )
]


# ============================================================
# PALABRAS / GENEROS QUE QUEREMOS
# ============================================================

LATIN_KEYWORDS = [
    "latin",
    "latino",
    "latina",
    "latin pop",
    "latin urban",
    "reggaeton",
    "bachata",
    "salsa",
    "merengue",
    "cumbia",
    "tropical",
    "música latina",
    "musica latina",
    "regional",
    "urbano latino"
]

POP_KEYWORDS = [
    "pop",
    "dance pop",
    "electropop",
    "indie pop",
    "synth pop",
    "pop latino",
    "latin pop"
]


# ============================================================
# ARTISTAS / CONTENIDO QUE NO QUEREMOS PRIORIZAR
# ============================================================

EXCLUDE_KEYWORDS = [
    "podcast",
    "christmas",
    "holiday",
    "audiobook",
    "soundtrack",
    "classical"
]


# ============================================================
# DESCARGAR URL
# ============================================================

def descargar(url):

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/131 Safari/537.36"
        }
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalizar(texto):

    texto = unescape(str(texto or ""))

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


# ============================================================
# SPOTIFY EMBED
# ============================================================

def obtener_spotify(url, fuente):

    canciones = []

    try:

        html = descargar(url)

        # Estructura utilizada por Spotify Embed
        patron = re.findall(
            r'<h3[^>]>(.?)</h3>\s*<h4[^>]>(.?)</h4>',
            html,
            flags=re.IGNORECASE | re.DOTALL
        )

        for posicion, item in enumerate(patron, start=1):

            titulo = re.sub("<.*?>", "", item[0])
            artista = re.sub("<.*?>", "", item[1])

            titulo = normalizar(titulo)
            artista = normalizar(artista)

            if not titulo or not artista:
                continue

            canciones.append({
                "title": titulo,
                "artist": artista,
                "position": posicion,
                "source": fuente,
                "genre": ""
            })

    except Exception as error:

        print(
            "Error Spotify:",
            fuente,
            error
        )

    return canciones


# ============================================================
# APPLE MUSIC RSS
# ============================================================

def obtener_apple(url, fuente):

    canciones = []

    try:

        texto = descargar(url)

        data = json.loads(texto)

        resultados = (
            data.get("feed", {})
                .get("results", [])
        )

        for posicion, item in enumerate(
            resultados,
            start=1
        ):

            titulo = normalizar(
                item.get("name", "")
            )

            artista = normalizar(
                item.get("artistName", "")
            )

            genero = normalizar(
                item.get("genres", [{}])[0].get(
                    "name",
                    ""
                )
                if item.get("genres")
                else ""
            )

            imagen = item.get(
                "artworkUrl100",
                ""
            )

            if not titulo or not artista:
                continue

            canciones.append({
                "title": titulo,
                "artist": artista,
                "position": posicion,
                "source": fuente,
                "genre": genero,
                "cover": imagen
            })

    except Exception as error:

        print(
            "Error Apple:",
            fuente,
            error
        )

    return canciones


# ============================================================
# CLASIFICACION MUSICAL
# ============================================================

def es_latina(cancion):

    texto = (
        cancion["title"] + " " +
        cancion["artist"] + " " +
        cancion.get("genre", "")
    ).lower()

    return any(
        palabra in texto
        for palabra in LATIN_KEYWORDS
    )


def es_pop(cancion):

    texto = (
        cancion["title"] + " " +
        cancion["artist"] + " " +
        cancion.get("genre", "")
    ).lower()

    return any(
        palabra in texto
        for palabra in POP_KEYWORDS
    )


def esta_excluida(cancion):

    texto = (
        cancion["title"] + " " +
        cancion["artist"] + " " +
        cancion.get("genre", "")
    ).lower()

    return any(
        palabra in texto
        for palabra in EXCLUDE_KEYWORDS
    )


# ============================================================
# BUSCAR CARATULA
# ============================================================

def buscar_caratula(titulo, artista):

    try:

        termino = urllib.parse.quote(
            titulo + " " + artista
        )

        url = (
            "https://itunes.apple.com/search"
            "?term=" + termino +
            "&entity=song"
            "&limit=5"
        )

        texto = descargar(url)

        data = json.loads(texto)

        resultados = data.get(
            "results",
            []
        )

        if not resultados:
            return ""

        # Intentar encontrar coincidencia de artista
        titulo_l = titulo.lower()
        artista_l = artista.lower()

        mejor = resultados[0]

        for resultado in resultados:

            nombre = str(
                resultado.get(
                    "trackName",
                    ""
                )
            ).lower()

            artista_resultado = str(
                resultado.get(
                    "artistName",
                    ""
                )
            ).lower()

            if (
                titulo_l in nombre
                and artista_l in artista_resultado
            ):

                mejor = resultado
                break

        imagen = mejor.get(
            "artworkUrl100",
            ""
        )

        if imagen:

            imagen = imagen.replace(
                "100x100bb",
                "600x600bb"
            )

        return imagen

    except Exception as error:

        print(
            "Error buscando caratula:",
            titulo,
            artista,
            error
        )

        return ""


# ============================================================
# PUNTUACION
# ============================================================

def calcular_puntos(cancion):

    posicion = cancion["position"]
    fuente = cancion["source"]

    puntos = max(
        1,
        101 - posicion
    )

    # ========================================================
    # COSTA RICA = máxima prioridad
    # ========================================================

    if "cr" in fuente:
        puntos += 90

    # ========================================================
    # MEXICO = segunda prioridad
    # ========================================================

    if "mx" in fuente:
        puntos += 65

    # ========================================================
    # GLOBAL
    # ========================================================

    if "global" in fuente:
        puntos += 35

    # ========================================================
    # APPLE / SPOTIFY
    # ========================================================

    if fuente.startswith("apple"):
        puntos += 20

    if fuente.startswith("spotify"):
        puntos += 25

    # ========================================================
    # LATINO
    # ========================================================

    if es_latina(cancion):
        puntos += 100

    # ========================================================
    # POP
    # ========================================================

    if es_pop(cancion):
        puntos += 70

    # ========================================================
    # EXCLUSION
    # ========================================================

    if esta_excluida(cancion):
        puntos -= 500

    return puntos


# ============================================================
# GENERAR TOP 20
# ============================================================

def generar_top20():

    todas = []

    for fuente, url in SOURCES:

        print(
            "Consultando:",
            fuente
        )

        if fuente.startswith("spotify"):

            canciones = obtener_spotify(
                url,
                fuente
            )

        else:

            canciones = obtener_apple(
                url,
                fuente
            )

        todas.extend(canciones)

    print(
        "Canciones encontradas:",
        len(todas)
    )

    # ========================================================
    # AGRUPAR CANCIONES REPETIDAS
    # ========================================================

    agrupadas = {}

    for cancion in todas:

        clave = (
            normalizar(
                cancion["title"]
            ).lower()
            + "|||"
            +
            normalizar(
                cancion["artist"]
            ).lower()
        )

        if clave not in agrupadas:

            agrupadas[clave] = {
                "title": cancion["title"],
                "artist": cancion["artist"],
                "genre": cancion.get(
                    "genre",
                    ""
                ),
                "cover": cancion.get(
                    "cover",
                    ""
                ),
                "sources": [],
                "score": 0
            }

        registro = agrupadas[clave]

        registro["sources"].append(
            cancion["source"]
        )

        registro["score"] += calcular_puntos(
            cancion
        )

        # Conservar carátula si ya apareció
        if (
            not registro["cover"]
            and cancion.get("cover")
        ):

            registro["cover"] = cancion[
                "cover"
            ]

        if (
            not registro["genre"]
            and cancion.get("genre")
        ):

            registro["genre"] = cancion[
                "genre"
            ]

    # ========================================================
    # ORDENAR
    # ========================================================

    ranking = sorted(
        agrupadas.values(),
        key=lambda x: x["score"],
        reverse=True
    )

    # ========================================================
    # PRIMERA SELECCION
    # ========================================================

    seleccion = []

    for cancion in ranking:

        if len(seleccion) >= 20:
            break

        # Evitar contenido claramente no musical
        if esta_excluida(cancion):
            continue

        seleccion.append(cancion)

    # ========================================================
    # CONSEGUIR CARATULAS FALTANTES
    # ========================================================

    for cancion in seleccion:

        if not cancion.get("cover"):

            print(
                "Buscando caratula:",
                cancion["title"]
            )

            cancion["cover"] = buscar_caratula(
                cancion["title"],
                cancion["artist"]
            )

            # Evitar demasiadas consultas seguidas
            time.sleep(0.25)

    # ========================================================
    # CREAR JSON FINAL
    # ========================================================

    resultado = []

    for posicion, cancion in enumerate(
        seleccion,
        start=1
    ):

        resultado.append({
            "position": posicion,
            "title": cancion["title"],
            "artist": cancion["artist"],
            "cover": cancion.get(
                "cover",
                ""
            ),
            "genre": cancion.get(
                "genre",
                ""
            )
        })

    if len(resultado) != 20:

        raise Exception(
            "No se pudieron obtener "
            "20 canciones."
        )

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

    print(
        "TOP 20 NOVA generado correctamente."
    )

    print(
        "Canciones:",
        len(resultado)
    )


generar_top20()
