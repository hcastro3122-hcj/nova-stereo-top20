import json
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen


SOURCES = [
    (
        "Costa Rica",
        "https://rss.applemarketingtools.com/api/v2/cr/music/most-played/100/songs.json"
    ),
    (
        "Estados Unidos",
        "https://rss.applemarketingtools.com/api/v2/us/music/most-played/100/songs.json"
    )
]


LATIN_KEYWORDS = [
    "latin",
    "reggaeton",
    "reggaetón",
    "urbano",
    "urbana",
    "bachata",
    "salsa",
    "merengue",
    "cumbia",
    "corridos",
    "regional mexicano",
    "trap latino",
    "pop latino",
    "spanish",
    "español"
]


def clean(value):
    return re.sub(
        r"\s+",
        " ",
        str(value or "")
    ).strip()


def download_json(url):

    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 NovaStereo/1.0"
        }
    )

    with urlopen(
        request,
        timeout=30
    ) as response:

        return json.loads(
            response.read().decode("utf-8")
        )


def is_latin(song):

    text = " ".join([
        clean(song.get("name")),
        clean(song.get("artistName")),
        clean(song.get("genres"))
    ]).lower()

    return any(
        keyword in text
        for keyword in LATIN_KEYWORDS
    )


def collect_songs():

    songs = []

    for country, url in SOURCES:

        try:

            data = download_json(url)

            results = (
                data
                .get("feed", {})
                .get("results", [])
            )

            for position, item in enumerate(
                results,
                start=1
            ):

                title = clean(
                    item.get("name")
                )

                artist = clean(
                    item.get("artistName")
                )

                if not title or not artist:
                    continue

                songs.append({

                    "title": title,

                    "artist": artist,

                    "artwork": item.get(
                        "artworkUrl100",
                        ""
                    ),

                    "url": item.get(
                        "url",
                        ""
                    ),

                    "country": country,

                    "position": position,

                    "latin": is_latin(item)

                })

        except Exception as error:

            print(
                f"ERROR leyendo {country}: {error}"
            )

    return songs


def remove_duplicates(songs):

    unique = {}

    for song in songs:

        key = (
            song["title"].lower(),
            song["artist"].lower()
        )

        if key not in unique:

            unique[key] = song

        else:

            current = unique[key]

            if (
                song["position"]
                <
                current["position"]
            ):

                unique[key] = song

    return list(
        unique.values()
    )


def calculate_score(song):

    position = song["position"]

    chart_score = max(
        0,
        120 - position
    )

    latin_score = (
        40
        if song["latin"]
        else 0
    )

    costa_rica_score = (
        25
        if song["country"] == "Costa Rica"
        else 0
    )

    return (
        chart_score
        +
        latin_score
        +
        costa_rica_score
    )


def create_top20(songs):

    for song in songs:

        song["score"] = calculate_score(
            song
        )

    songs.sort(
        key=lambda song: song["score"],
        reverse=True
    )

    result = []

    artist_count = {}

    for song in songs:

        artist_key = song["artist"].lower()

        count = artist_count.get(
            artist_key,
            0
        )

        # Máximo cuatro canciones
        # del mismo artista.
        if count >= 4:
            continue

        artist_count[artist_key] = count + 1

        result.append(song)

        if len(result) >= 20:
            break

    top20 = []

    for number, song in enumerate(
        result,
        start=1
    ):

        top20.append({

            "position": number,

            "title": song["title"],

            "artist": song["artist"],

            "artwork": song["artwork"],

            "url": song["url"],

            "source": song["country"]

        })

    return top20


def main():

    songs = collect_songs()

    songs = remove_duplicates(
        songs
    )

    top20 = create_top20(
        songs
    )

    output = {

        "station": "Nova Stereo",

        "title": "TOP 20 NOVA",

        "subtitle":
            "Nuevas más solicitadas · Tendencias musicales",

        "updatedAt":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "songs": top20

    }

    with open(
        "top20.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"TOP 20 NOVA generado: {len(top20)} canciones"
    )

    for song in top20:

        print(
            f'#{song["position"]} '
            f'{song["title"]} - '
            f'{song["artist"]}'
        )


if _name_ == "_main_":
    main()