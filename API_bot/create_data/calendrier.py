import re
import sqlite3

import requests
from ics import Calendar

DB_PATH = "calendars.db"
URLS = [
    "https://edt-api.univ-avignon.fr/api/exportAgenda/tdoption/def502005fbe64ad4610b919d8191570b6c3cc4500ac9247311377896afefdeb0abd3fafc90321830441bbd67e69bea7afad656309d296ed573d6b731ca7e405d3cc1ce29fb6afa26369a99642c1598f7dcda542a14f0806026930d1a1"
]


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

    calendar_name = cal_name or "univ_avignon"

    return {
        "calendar_name": calendar_name,
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
            calendar_name TEXT,
            source_url TEXT,
            formation TEXT,
            td_group TEXT,
            matiere TEXT,
            enseignant TEXT,
            type_cours TEXT,
            UNIQUE(uid, calendar_name)
        )
        """
    )

    cur.execute("PRAGMA table_info(events)")
    existing_columns = {row[1] for row in cur.fetchall()}
    required_columns = {
        "source_url": "TEXT",
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
    calendar = Calendar(ics_text)
    meta = extract_meta_from_ics(ics_text)
    cur = conn.cursor()

    imported_count = 0
    for event in calendar.events:
        parsed = parse_description(event.description)
        td_group = parsed["td"] or meta["td_group"]

        cur.execute(
            """
            INSERT OR REPLACE INTO events (
                uid, summary, dtstart, dtend, description, location,
                calendar_name, source_url, formation, td_group,
                matiere, enseignant, type_cours
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.uid,
                event.name,
                str(event.begin),
                str(event.end),
                event.description,
                event.location,
                meta["calendar_name"],
                url,
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


def main() -> None:
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
