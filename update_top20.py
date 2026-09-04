import json
import re
import time
import html
import urllib.parse
import urllib.request
from datetime import datetime, timezone

OUTPUT_FILE = "top20.json"

# ============================================================
# FUENTES PRINCIPALES
# ============================================================

KWORB_SOURCES = {
    "cr": "https://kworb.net/spotify/country/cr_daily.html",
    "pr": "https://kworb.net/spotify/country/pr_daily.html",
    "mx": "https://kworb.net/spotify/country/mx_daily.html",
    "co": "https://kworb.net/spotify/country/co_daily.html",
    "us": "https://kworb.net/spotify/country/us_daily.html",
}

APPLE_SOURCES = {
    "cr": "https://rss.applemarketingtools.com/api/v2/cr/music/most-played/100/songs.json",
    "mx": "https://rss.applemarketingtools.com/api/v2/mx/music/most-played/100/songs.json",
    "us": "https://rss.applemarketingtools.com/api/v2/us/music/most-played/100/songs.json",
}

# ============================================================
# PALABRAS CLAVE
# ============================================================

LATIN_KEYWORDS = [
    "reggaeton",
    "urbano",
    "latin",
    "latino",
    "latina",
    "salsa",
    "bachata",
    "merengue",
    "cumbia",
    "vallenato",
    "tropical",
    "corridos",
    "regional mexicano",
    "mariachi",
    "banda",
    "norteño",
    "trap latino",
    "dembow",
    "guaracha",
    "electrolatino",
    "plena",
    "soca",
    "afrobeat latino",
]

LATIN_ARTISTS = [
    "bad bunny",
    "karol g",
    "feid",
    "j balvin",
    "ozuna",
    "anuel aa",
    "farruko",
    "myke towers",
    "eladio carrion",
    "omar courtz",
    "jay wheeler",
    "young miko",
    "rauw alejandro",
    "mora",
    "de la rose",
    "xavi",
    "peso pluma",
    "junior h",
    "natanael cano",
    "fuerza regida",
    "grupo frontera",
    "romeo santos",
    "prince royce",
    "maluma",
    "shakira",
    "manuel turizo",
    "beele",
    "wisin",
    "yandel",
    "tito double p",
    "gabito ballesteros",
    "jhayco",
    "quevedo",
    "saiko",
    "morad",
    "daddy yankee",
    "don omar",
    "greeicy",
    "camilo",
    "sebastian yatra",
    "carin leon",
    "grupo firme",
    "carolina daian",
]

TROPICAL_ARTISTS = [
    "romeo santos",
    "prince royce",
    "marc anthony",
    "victor manuelle",
    "gilberto santa rosa",
    "luis enrique",
    "frankie ruiz",
    "tito nieves",
    "el gran combo",
    "la india",
    "oscar de leon",
    "grupo niche",
    "sonora ponceña",
    "ray barreto",
]

EXCLUDE_WORDS = [
    "podcast",
    "audiobook",
    "christmas",
    "navidad",
    "holiday",
    "soundtrack",
    "karaoke",
    "instrumental",
    "classical",
    "meditation",
    "sleep",
    "lofi",
]

# ============================================================
# HTTP
# ============================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Nova Stereo TOP20)",
    "Accept": "/",
}


def fetch(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print("ERROR:", url, e)
        return ""


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalize(text):
    text = html.unescape(str(text or "")).lower().strip()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def clean_title(title):
    title = html.unescape(title or "")
    title = re.sub(r"\s*\([^)](remix|version|edit|live|acoustic)[^)]\)", "", title, flags=re.I)
    title = re.sub(r"\s*\[[^\]](remix|version|edit|live|acoustic)[^\]]\]", "", title, flags=re.I)
    return title.strip()


# ============================================================
# DETECCIÓN LATINA
# ============================================================

def is_latin(title, artist, genre=""):
    text = normalize(f"{title} {artist} {genre}")

    if any(word in text for word in LATIN_KEYWORDS):
        return True

    if any(artist_name in text for artist_name in LATIN_ARTISTS):
        return True

    return False


def is_tropical(title, artist, genre=""):
    text = normalize(f"{title} {artist} {genre}")

    if any(word in text for word in ["salsa", "bachata", "merengue", "cumbia", "tropical", "plena", "vallenato"]):
        return True

    if any(artist_name in text for artist_name in TROPICAL_ARTISTS):
        return True

    return False


def is_excluded(title, artist):
    text = normalize(f"{title} {artist}")
    return any(word in text for word in EXCLUDE_WORDS)


# ============================================================
# KWORB
# ============================================================

def parse_kworb(html_text, country):
    songs = []

    if not html_text:
        return songs

    # Intenta encontrar filas de tablas.
    rows = re.findall(
        r"<tr[^>]>(.?)</tr>",
        html_text,
        flags=re.I | re.S
    )

    for row in rows:
        cells = re.findall(
            r"<td[^>]>(.?)</td>",
            row,
            flags=re.I | re.S
        )

        if len(cells) < 3:
            continue

        clean_cells = []

        for cell in cells:
            cell = re.sub(r"<[^>]+>", " ", cell)
            cell = html.unescape(cell)
            cell = re.sub(r"\s+", " ", cell).strip()
            clean_cells.append(cell)

        position = None

        for value in clean_cells[:3]:
            match = re.search(r"\b(\d{1,3})\b", value)
            if match:
                position = int(match.group(1))
                break

        if not position:
            continue

        if position > 100:
            continue

        artist = ""
        title = ""

        # Busca enlaces, normalmente artist/title aparecen como links.
        links = re.findall(
            r"<a[^>]>(.?)</a>",
            row,
            flags=re.I | re.S
        )

        link_texts = []

        for link in links:
            text = re.sub(r"<[^>]+>", " ", link)
            text = html.unescape(text)
            text = re.sub(r"\s+", " ", text).strip()

            if text:
                link_texts.append(text)

        if len(link_texts) >= 2:
            artist = link_texts[-2]
            title = link_texts[-1]

        if not title:
            if len(clean_cells) >= 2:
                title = clean_cells[1]

        if not artist:
            if len(clean_cells) >= 3:
                artist = clean_cells[2]

        if not title or not artist:
            continue

        if is_excluded(title, artist):
            continue

        songs.append({
            "title": clean_title(title),
            "artist": artist,
            "country": country,
            "source": "spotify_kworb",
            "position": position,
        })

    return songs


# ============================================================
# APPLE MUSIC
# ============================================================

def parse_apple(url, country):
    songs = []

    text = fetch(url)

    if not text:
        return songs

    try:
        data = json.loads(text)
    except Exception as e:
        print("Apple JSON ERROR:", e)
        return songs

    results = data.get("feed", {}).get("results", [])

    for index, item in enumerate(results, start=1):

        title = item.get("name", "")
        artist = item.get("artistName", "")
        artwork = item.get("artworkUrl100", "")
        release_date = item.get("releaseDate", "")

        if not title or not artist:
            continue

        if is_excluded(title, artist):
            continue

        songs.append({
            "title": clean_title(title),
            "artist": artist,
            "country": country,
            "source": "apple",
            "position": index,
            "cover": artwork,
            "release_date": release_date,
        })

    return songs


# ============================================================
# ITUNES — DATOS + PORTADA
# ============================================================

def itunes_search(title, artist):
    query = urllib.parse.quote(f"{artist} {title}")

    url = (
        "https://itunes.apple.com/search"
        f"?term={query}"
        "&media=music"
        "&entity=song"
        "&limit=5"
    )

    text = fetch(url)

    if not text:
        return None

    try:
        data = json.loads(text)
    except Exception:
        return None

    results = data.get("results", [])

    if not results:
        return None

    target_title = normalize(title)
    target_artist = normalize(artist)

    best = None
    best_score = -1

    for item in results:

        item_title = normalize(item.get("trackName", ""))
        item_artist = normalize(item.get("artistName", ""))

        score = 0

        if target_title and target_title in item_title:
            score += 50

        if item_title and item_title in target_title:
            score += 30

        if target_artist and target_artist in item_artist:
            score += 50

        if item_artist and item_artist in target_artist:
            score += 20

        if score > best_score:
            best_score = score
            best = item

    return best


# ============================================================
# DEEZER — SEGUNDA FUENTE DE PORTADAS
# ============================================================

def deezer_search(title, artist):
    query = urllib.parse.quote(f"{artist} {title}")

    url = (
        "https://api.deezer.com/search/track"
        f"?q={query}&limit=5"
    )

    text = fetch(url)

    if not text:
        return None

    try:
        data = json.loads(text)
    except Exception:
        return None

    results = data.get("data", [])

    if not results:
        return None

    target_title = normalize(title)
    target_artist = normalize(artist)

    best = None
    best_score = -1

    for item in results:

        item_title = normalize(item.get("title", ""))
        item_artist = normalize(
            item.get("artist", {}).get("name", "")
        )

        score = 0

        if target_title and target_title in item_title:
            score += 50

        if target_artist and target_artist in item_artist:
            score += 50

        if score > best_score:
            best_score = score
            best = item

    return best


# ============================================================
# PORTADA
# ============================================================

def get_cover(song):

    # 1. Apple Music ya proporcionó portada.
    if song.get("cover"):
        cover = song["cover"]

        if "100x100" in cover:
            cover = cover.replace("100x100", "600x600")

        return cover

    # 2. iTunes
    result = itunes_search(song["title"], song["artist"])

    if result:
        artwork = result.get("artworkUrl600") or result.get("artworkUrl100")

        if artwork:
            return artwork.replace("100x100", "600x600")

    # 3. Deezer
    result = deezer_search(song["title"], song["artist"])

    if result:
        album = result.get("album", {})

        cover = (
            album.get("cover_xl")
            or album.get("cover_big")
            or album.get("cover_medium")
        )

        if cover:
            return cover

    return ""


# ============================================================
# ANTIGÜEDAD
# ============================================================

def get_release_date(song):

    if song.get("release_date"):
        try:
            return datetime.fromisoformat(
                song["release_date"].replace("Z", "+00:00")
            )
        except Exception:
            pass

    result = itunes_search(song["title"], song["artist"])

    if result:
        date_text = result.get("releaseDate", "")

        try:
            return datetime.fromisoformat(
                date_text.replace("Z", "+00:00")
            )
        except Exception:
            pass

    return None


def age_score(song):

    release = get_release_date(song)

    if not release:
        return 0

    now = datetime.now(timezone.utc)

    if release.tzinfo is None:
        release = release.replace(tzinfo=timezone.utc)

    days = max(0, (now - release).days)

    # Música MUY reciente
    if days <= 14:
        return 100

    if days <= 30:
        return 80

    if days <= 60:
        return 60

    if days <= 90:
        return 40

    if days <= 180:
        return 15

    # Desde aquí empieza a penalizarse fuerte.
    if days <= 365:
        return -30

    if days <= 730:
        return -100

    if days <= 1460:
        return -180

    return -300


# ============================================================
# NORMALIZACIÓN DE ARTISTAS
# ============================================================

def song_key(title, artist):

    title = normalize(title)
    artist = normalize(artist)

    title = re.sub(
        r"\s+(feat\.?|ft\.?|with)\s+.*$",
        "",
        title
    )

    return f"{title}|{artist}"


# ============================================================
# RANKING
# ============================================================

def make_ranking(all_songs):

    grouped = {}

    for song in all_songs:

        key = song_key(
            song["title"],
            song["artist"]
        )

        if key not in grouped:
            grouped[key] = {
                "title": song["title"],
                "artist": song["artist"],
                "countries": set(),
                "sources": set(),
                "positions": [],
                "covers": [],
                "release_date": song.get("release_date", ""),
            }

        item = grouped[key]

        item["countries"].add(song["country"])
        item["sources"].add(song["source"])

        if song.get("position"):
            item["positions"].append(song["position"])

        if song.get("cover"):
            item["covers"].append(song["cover"])

        if song.get("release_date"):
            item["release_date"] = song["release_date"]

    candidates = []

    for item in grouped.values():

        title = item["title"]
        artist = item["artist"]

        if is_excluded(title, artist):
            continue

        countries = item["countries"]

        is_latin_song = is_latin(title, artist)
        is_tropical_song = is_tropical(title, artist)

        # Promedio de posiciones.
        if item["positions"]:
            avg_position = sum(item["positions"]) / len(item["positions"])
        else:
            avg_position = 100

        # Presencia en varios países.
        country_score = len(countries) * 28

        # Posición actual.
        chart_score = max(0, 110 - avg_position)

        # Fuente.
        source_score = 0

        if "spotify_kworb" in item["sources"]:
            source_score += 35

        if "apple" in item["sources"]:
            source_score += 20

        # PRIORIDAD LATINA MUY FUERTE.
        latin_score = 125 if is_latin_song else 0

        # Salsa, bachata, merengue, cumbia, etc.
        tropical_score = 55 if is_tropical_song else 0

        # Popularidad multi-país.
        multi_country_bonus = 0

        if len(countries) >= 2:
            multi_country_bonus += 35

        if len(countries) >= 3:
            multi_country_bonus += 45

        if len(countries) >= 4:
            multi_country_bonus += 55

        # Edad.
        age = age_score(item)

        score = (
            chart_score
            + country_score
            + source_score
            + latin_score
            + tropical_score
            + multi_country_bonus
            + age
        )

        # Una canción vieja solamente puede sobrevivir
        # si realmente aparece actualmente en varios países.
        if age <= -100 and len(countries) < 3:
            score -= 250

        # Canciones antiguas con fuerte presencia actual:
        # permitimos que compitan si están realmente resurgiendo.
        if age <= -100 and len(countries) >= 4:
            score += 60

        candidates.append({
            "title": title,
            "artist": artist,
            "score": score,
            "countries": sorted(list(countries)),
            "latin": is_latin_song,
            "tropical": is_tropical_song,
            "release_date": item.get("release_date", ""),
            "cover": item["covers"][0] if item["covers"] else "",
        })

    # Orden general.
    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # ========================================================
    # SELECCIÓN FINAL
    # ========================================================

    latin = [
        x for x in candidates
        if x["latin"]
    ]

    non_latin = [
        x for x in candidates
        if not x["latin"]
    ]

    final = []

    # Hasta 16 canciones latinas.
    for song in latin:
        if len(final) >= 16:
            break

        final.append(song)

    # Hasta 4 canciones internacionales/anglo.
    for song in non_latin:
        if len(final) >= 20:
            break

        final.append(song)

    # Si faltaran canciones, completar.
    if len(final) < 20:

        used = {
            song_key(x["title"], x["artist"])
            for x in final
        }

        for song in candidates:

            key = song_key(
                song["title"],
                song["artist"]
            )

            if key in used:
                continue

            final.append(song)
            used.add(key)

            if len(final) >= 20:
                break

    # ========================================================
    # PORTADAS
    # ========================================================

    print("")
    print("BUSCANDO PORTADAS...")
    print("")

    for index, song in enumerate(final, start=1):

        if not song.get("cover"):

            print(
                f"[{index}/20] "
                f"{song['title']} - {song['artist']}"
            )

            song["cover"] = get_cover(song)

            time.sleep(0.25)

    return final[:20]


# ============================================================
# GENERAR JSON
# ============================================================

def generar_top20():

    print("")
    print("========================================")
    print("       NOVA STEREO — TOP 20")
    print("========================================")
    print("")

    all_songs = []

    # --------------------------------------------------------
    # KWORB
    # --------------------------------------------------------

    for country, url in KWORB_SOURCES.items():

        print("Descargando Spotify:", country)

        page = fetch(url)

        songs = parse_kworb(
            page,
            country
        )

        print(
            "Encontradas:",
            len(songs)
        )

        all_songs.extend(songs)

    # --------------------------------------------------------
    # APPLE
    # --------------------------------------------------------

    for country, url in APPLE_SOURCES.items():

        print("Descargando Apple Music:", country)

        songs = parse_apple(
            url,
            country
        )

        print(
            "Encontradas:",
            len(songs)
        )

        all_songs.extend(songs)

    print("")
    print(
        "Total de registros:",
        len(all_songs)
    )

    # --------------------------------------------------------
    # RANKING
    # --------------------------------------------------------

    ranking = make_ranking(all_songs)

    output = []

    for position, song in enumerate(
        ranking,
        start=1
    ):

        genre = "Latina"

        if song["tropical"]:
            genre = "Tropical"

        elif not song["latin"]:
            genre = "Global"

        output.append({
            "position": position,
            "title": song["title"],
            "artist": song["artist"],
            "cover": song.get("cover", ""),
            "genre": genre,
            "countries": song.get("countries", []),
            "score": round(song.get("score", 0), 2),
            "release_date": song.get(
                "release_date",
                ""
            ),
        })

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("")
    print("========================================")
    print(" TOP 20 NOVA GENERADO CORRECTAMENTE")
    print("========================================")
    print("")

    for song in output:

        print(
            f"{song['position']:02d}. "
            f"{song['title']} — "
            f"{song['artist']} "
            f"[{song['genre']}]"
        )

    print("")
    print(
        "Total:",
        len(output)
    )


# ============================================================
# EJECUTAR
# ============================================================

generar_top20()
