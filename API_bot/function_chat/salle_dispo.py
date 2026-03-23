import re
import sqlite3
from datetime import datetime, timedelta
import json

with open("salles.json", "r") as f:
    salles = json.load(f)

DB_PATH = "calendars.db"

def format_salle(salle:str):
    salle = salle.replace(" ", "")
    temps=salle.split("=")
    if len(temps)==2:
        temps2=temps[1].split("-")
        if(len(temps2)==2):
            return temps2[1]
        else:
            return temps[1]
    return salle


def _parse_duration(temps_utilisation):
    durations = {
        "1h30": timedelta(hours=1, minutes=30),
        "3h": timedelta(hours=3),
        "4h30": timedelta(hours=4, minutes=30),
        "6h": timedelta(hours=6),
    }
    return durations.get(temps_utilisation)


def _parse_start_time(heure_debut):
    if not heure_debut:
        return None

    value = heure_debut.strip().lower().replace(" ", "")
    value = value.replace("h", ":")

    if re.fullmatch(r"\d{1,2}", value):
        value = f"{value}:00"
    if re.fullmatch(r"\d{1,2}:\d{1,2}", value):
        hour, minute = value.split(":")
        return int(hour), int(minute)
    return None


def _parse_event_datetime(value):
    if not value:
        return None

    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        match = re.search(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})", text)
        if not match:
            return None
        return datetime.fromisoformat(f"{match.group(1)} {match.group(2)}")


def _to_month_day(date):
    value = (date or "").strip()
    if not value:
        return None

    if re.fullmatch(r"\d{2}-\d{2}", value):
        day, month = value.split("-")
        return f"{month}-{day}"

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        _, month, day = value.split("-")
        return f"{month}-{day}"

    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        day, month, _ = value.split("/")
        return f"{month}-{day}"

    return None


def recherche_salle_disponnible(date, heure_debut, temps_utilisation):
    month_day = _to_month_day(date)
    hour_minute = _parse_start_time(heure_debut)
    duration = _parse_duration(temps_utilisation)
    all_rooms = sorted({room for room in salles if room})

    if month_day is None:
        return {"erreur": "Format de date invalide. Utilisez DD-MM ou YYYY-MM-DD."}
    if hour_minute is None:
        return {"erreur": "Format d'heure invalide. Utilisez HH:MM ou HHhMM."}
    if duration is None:
        return {"erreur": "Durée invalide. Valeurs attendues: 1h30, 3h, 4h30, 6h."}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute(
            """
            SELECT location, dtstart, dtend
            FROM events
            WHERE location IS NOT NULL
              AND dtstart LIKE ?
            """,
            (f"%____-{month_day}%",),
        ).fetchall()
    except sqlite3.Error:
        conn.close()
        return {"erreur": "Erreur lors de la lecture de la base planning."}

    conn.close()

    event_reference = _parse_event_datetime(rows[0]["dtstart"])
    if not event_reference:
        return {"erreur": "Impossible de lire la date des cours pour ce jour."}

    date_prefix = event_reference.strftime("%Y-%m-%d")
    requested_start = datetime.fromisoformat(f"{date_prefix} {hour_minute[0]:02d}:{hour_minute[1]:02d}:00")
    requested_end = requested_start + duration

    occupied = set()
    for row in rows:
        event_start = _parse_event_datetime(row["dtstart"])
        event_end = _parse_event_datetime(row["dtend"])
        location = row["location"]


        if not event_start or not event_end or not location:
            continue

        overlap = requested_start < event_end and requested_end > event_start
        location = format_salle(location)

        if overlap and location in all_rooms:
            occupied.add(location)

    available = sorted([room for room in all_rooms if room not in occupied])

    return {
        "salles_disponibles": available,
        "salles_occupees": list(occupied),
    }

if __name__ == "__main__":
    result = recherche_salle_disponnible("24-03", "10h00", "3h")
    print(result)