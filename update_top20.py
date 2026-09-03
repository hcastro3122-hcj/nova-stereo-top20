import json
import re
import urllib.request
from datetime import datetime, timezone


OUTPUT_FILE = "top20.json"

SOURCES = [
    {
        "name": "Billboard Hot Latin Songs",
        "url": "https://www.billboard.com/charts/latin-songs/"
    },
    {
        "name": "Billboard Global 200",
        "url": "https://www.billboard.com/charts/billboard-global-200/"
    },
]


def download_page(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120 Safari/537.36"
            )
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def clean_text(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_songs(html):
    songs = []

    title_patterns = [
        r'class="c-title[^"]"[^>]>(.*?)</',
        r'class="o-chart-results-list__item-title[^"]"[^>]>(.*?)</',
    ]

    artist_patterns = [
        r'class="c-label[^"]"[^>]>(.*?)</',
        r'class="c-label[^"]">\s(.?)\s</',
    ]

    titles = []

    for pattern in title_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)

        for match in matches:
            value = clean_text(match)

            if value and value not in titles:
                titles.append(value)

    artists = []

    for pattern in artist_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)

        for match in matches:
            value = clean_text(match)

            if value and value not in artists:
                artists.append(value)

    for index, title in enumerate(titles[:50]):
        artist = artists[index] if index < len(artists) else "Artista"

        songs.append(
            {
                "title": title,
                "artist": artist,
            }
        )

    return songs


def normalize_song(song):
    title = song.get("title", "").strip()
    artist = song.get("artist", "").strip()

    return {
        "title": title,
        "artist": artist,
    }


def build_ranking():
    all_songs = []

    for source in SOURCES:
        try:
            html = download_page(source["url"])
            songs = extract_songs(html)

            for song in songs:
                song = normalize_song(song)

                if song["title"]:
                    song["source"] = source["name"]
                    all_songs.append(song)

        except Exception as error:
            print(
                f"No se pudo consultar {source['name']}: {error}"
            )

    ranking = []
    seen = set()

    for song in all_songs:
        key = (
            song["title"].lower(),
            song["artist"].lower(),
        )

        if key in seen:
            continue

        seen.add(key)
        ranking.append(song)

        if len(ranking) >= 20:
            break

    return ranking


def save_ranking(ranking):
    data = {
        "name": "TOP 20 NOVA",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "songs": [],
    }

    for position, song in enumerate(ranking, start=1):
        data["songs"].append(
            {
                "position": position,
                "title": song["title"],
                "artist": song["artist"],
                "source": song.get("source", ""),
            }
        )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def main():
    print("===================================")
    print("     TOP 20 NOVA - ACTUALIZACION")
    print("===================================")

    ranking = build_ranking()

    if not ranking:
        raise RuntimeError(
            "No se pudo obtener ninguna canción de los rankings."
        )

    save_ranking(ranking)

    print()
    print(f"TOP 20 NOVA generado correctamente: {len(ranking)} canciones")
    print()

    for song in ranking:
        print(
            f"{song['position']:02d}. "
            f"{song['title']} - {song['artist']}"
        )

    print()
    print(f"Archivo generado: {OUTPUT_FILE}")


if _name_ == "_main_":
    main()