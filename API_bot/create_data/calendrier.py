import re
import sqlite3
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import requests
from icalendar import Calendar

DB_PATH = "calendars.db"
LOCAL_TIMEZONE = ZoneInfo("Europe/Paris")


def unfold_ics_lines(ics_text: str) -> str:
    lines = ics_text.splitlines()
    unfolded = []
    for line in lines:
        if (line.startswith(" ") or line.startswith("\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return "\n".join(unfolded)


def extract_meta_from_ics(ics_text: str) -> dict:
    content = unfold_ics_lines(ics_text)
    cal_name_match = re.search(r"^X-WR-CALNAME(?:;[^:]+)?:\s*(.+)$", content, flags=re.MULTILINE)
    cal_name = cal_name_match.group(1).strip() if cal_name_match else ""

    formation_match = re.search(r"<([^>]+)>", cal_name)
    formation = formation_match.group(1).strip() if formation_match else ""

    group_match = re.search(r"\b(?:[A-Z0-9]+-){1,}[A-Za-z0-9]+-Gr\d+\b", cal_name)
    td_group = group_match.group(0).strip() if group_match else ""


    return {
        "formation": formation,
        "td_group": td_group,
    }


def parse_description(description: str | None) -> dict:
    fields = {
        "matiere": "",
        "enseignant": "",
        "td": "",
        "salle": "",
        "type_cours": "",
    }
    if not description:
        return fields

    for line in description.splitlines():
        cleaned = line.strip()
        if cleaned.startswith("Matière :"):
            fields["matiere"] = cleaned.replace("Matière :", "", 1).strip()
        elif cleaned.startswith("Enseignant :"):
            fields["enseignant"] = cleaned.replace("Enseignant :", "", 1).strip()
        elif cleaned.startswith("Enseignants :"):
            fields["enseignant"] = cleaned.replace("Enseignants :", "", 1).strip()
        elif cleaned.startswith("TD :"):
            fields["td"] = cleaned.replace("TD :", "", 1).strip()
        elif cleaned.startswith("Salle :"):
            fields["salle"] = cleaned.replace("Salle :", "", 1).strip()
        elif cleaned.startswith("Type :"):
            fields["type_cours"] = cleaned.replace("Type :", "", 1).strip()

    return fields


def to_local_datetime_text(value) -> str:
    """Convertit une date ICS en heure locale Europe/Paris (sans timezone dans le texte stocké)."""
    if value is None:
        return ""

    if hasattr(value, "to") and hasattr(value, "datetime"):
        dt = value.to("Europe/Paris").datetime
    elif hasattr(value, "datetime"):
        dt = value.datetime
    elif isinstance(value, date) and not isinstance(value, datetime):
        dt = datetime.combine(value, time.min)
    elif isinstance(value, datetime):
        dt = value
    else:
        return str(value)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TIMEZONE)
    else:
        dt = dt.astimezone(LOCAL_TIMEZONE)

    return dt.replace(tzinfo=None).isoformat(sep=" ")


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL,
            summary TEXT,
            dtstart TEXT,
            dtend TEXT,
            description TEXT,
            location TEXT,
            formation TEXT,
            td_group TEXT,
            matiere TEXT,
            enseignant TEXT,
            type_cours TEXT,
            UNIQUE(uid)
        )
        """
    )

    cur.execute("PRAGMA table_info(events)")
    existing_columns = {row[1] for row in cur.fetchall()}
    required_columns = {
        "formation": "TEXT",
        "td_group": "TEXT",
        "matiere": "TEXT",
        "enseignant": "TEXT",
        "type_cours": "TEXT",
    }

    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            cur.execute(f"ALTER TABLE events ADD COLUMN {column_name} {column_type}")

    conn.commit()


def import_ics_url(conn: sqlite3.Connection, url: str) -> int:
    response = requests.get(url, timeout=20)
    response.raise_for_status()

    ics_text = response.text
    calendar = Calendar.from_ical(ics_text)
    meta = extract_meta_from_ics(ics_text)
    cur = conn.cursor()

    imported_count = 0
    for event in calendar.walk("VEVENT"):
        description = str(event.get("DESCRIPTION", ""))
        parsed = parse_description(description)
        td_group = parsed["td"] or meta["td_group"]
        dtstart_value = event.get("DTSTART").dt if event.get("DTSTART") else None
        dtend_value = event.get("DTEND").dt if event.get("DTEND") else None

        cur.execute(
            """
            INSERT OR REPLACE INTO events (
                uid, summary, dtstart, dtend, description, location,
                formation, td_group,
                matiere, enseignant, type_cours
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(event.get("UID", "")),
                str(event.get("SUMMARY", "")),
                to_local_datetime_text(dtstart_value),
                to_local_datetime_text(dtend_value),
                description,
                str(event.get("LOCATION", "")),
                meta["formation"],
                td_group,
                parsed["matiere"],
                parsed["enseignant"],
                parsed["type_cours"],
            ),
        )
        imported_count += 1

    conn.commit()
    return imported_count


def recup_urls():
    with open("liens.txt", "r", encoding="utf-8") as reader:
        raw_lines = [line.strip() for line in reader if line.strip()]

    urls = []
    for line in raw_lines:
        if line.startswith("http://") or line.startswith("https://"):
            urls.append(line)

    urls = list(dict.fromkeys(urls))
    print(f"URLs récupérées: {len(urls)} URL(s) valides")
    return urls

def main() -> None:
    URLS = recup_urls()
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(conn)
        total_imported = 0
        for url in URLS:
            total_imported += import_ics_url(conn, url)
        print(f"Import terminé. {total_imported} événements traités.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
