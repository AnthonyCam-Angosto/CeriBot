import sqlite3
from datetime import datetime
from pathlib import Path


def _normaliser_date(date_utilisateur: str) -> str:
    valeur = (date_utilisateur or "").strip()
    if not valeur:
        raise ValueError("Date manquante")

    for date_format in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(valeur, date_format).date().isoformat()
        except ValueError:
            continue

    for date_format in ("%d-%m", "%d/%m"):
        try:
            date_partielle = datetime.strptime(valeur, date_format).date()
            annee_courante = datetime.now().year
            return date_partielle.replace(year=annee_courante).isoformat()
        except ValueError:
            continue

    raise ValueError("Format de date invalide")


def _candidats_dates(date_utilisateur: str) -> list[str]:
    valeur = (date_utilisateur or "").strip()
    try:
        base = _normaliser_date(valeur)
    except ValueError:
        raise

    if "/" in valeur or "-" in valeur:
        morceaux = valeur.replace("/", "-").split("-")
        if len(morceaux) == 2:
            jour = int(morceaux[0])
            mois = int(morceaux[1])
            annee = datetime.now().year
            candidats = []
            for delta in (0, -1, 1):
                try:
                    candidats.append(datetime(annee + delta, mois, jour).date().isoformat())
                except ValueError:
                    continue
            return list(dict.fromkeys(candidats))

    return [base]


def _filtre_filiere(filiere: str) -> list[str]:
    correspondances = {
        "informatique": ["informatique"],
        "ilsen": ["ilsen", "inge du logiciel"],
        "ia": ["intelligence artificielle", " ia"],
        "syrius": ["syrius", "systemes informatiques", "sicom"],
    }
    return correspondances.get((filiere or "").lower(), [])


def visualiser_planning_formation(date, filiere, type_formation, niveau_etudes, mode_etudes, groupe_td):
    db_path = Path(__file__).resolve().parents[1] / "calendars.db"
    if not db_path.exists():
        return {"erreur": "Base de planning introuvable (calendars.db)."}

    try:
        dates_candidates = _candidats_dates(date)
    except ValueError:
        return {"erreur": "Date invalide. Utilise YYYY-MM-DD ou DD-MM."}

    date_affichee = dates_candidates[0] if dates_candidates else (date or "")

    formation_prefix = ""
    if type_formation and niveau_etudes:
        type_norm = type_formation.strip().lower()
        if type_norm == "master":
            formation_prefix = f"M{niveau_etudes}"
        elif type_norm == "licence":
            formation_prefix = f"L{niveau_etudes}"

    placeholders = ", ".join(["?"] * len(dates_candidates))
    where_clauses = [f"substr(dtstart, 1, 10) IN ({placeholders})"]
    params = dates_candidates.copy()

    mots_cles_filiere = _filtre_filiere(filiere)
    if mots_cles_filiere:
        or_parts = []
        for mot_cle in mots_cles_filiere:
            or_parts.append("formation LIKE ?")
            params.append(f"%{mot_cle.lower()}%")
        where_clauses.append("(" + " OR ".join(or_parts) + ")")

    if formation_prefix:
        where_clauses.append("formation LIKE ?")
        params.append(f"%{formation_prefix.lower()}%")

    mode_norm = (mode_etudes or "").strip().lower()
    if mode_norm == "classic":
        where_clauses.append("td_group LIKE ?")
        params.append("%cla%")
    elif mode_norm == "alternance":
        where_clauses.append("td_group LIKE ?")
        params.append("%alt%")
    
    if groupe_td:
        where_clauses.append("td_group LIKE ?")
        params.append(f"%{groupe_td.strip().lower()}%")

    requete = f"""
        SELECT
            uid,
            summary,
            dtstart,
            dtend,
            description,
            location,
            formation,
            td_group,
            matiere,
            enseignant,
            type_cours
        FROM events
        WHERE {' AND '.join(where_clauses)}
        ORDER BY dtstart ASC
    """

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(requete, params).fetchall()
    except sqlite3.Error:
        return {"erreur": "Erreur lors de la lecture du planning."}
    finally:
        conn.close()

    if not rows:
        return {
            "date": date_affichee,
            "formation": f"{type_formation} {niveau_etudes} - {filiere} ({mode_etudes})",
            "groupe_td": groupe_td,
            "results": [],
            "message": "Aucun cours trouvé pour ces critères.",
        }

    results = []
    for row in rows:
        results.append(
            {
                "uid": row["uid"],
                "start": row["dtstart"],
                "end": row["dtend"],
                "title": row["summary"],
                "type": row["type_cours"] or "",
                "memo": row["description"],
                "salle": row["location"] or "",
                "matiere": row["matiere"] or "",
                "enseignant": row["enseignant"] or "",
                "td_group": row["td_group"] or "",
                "formation": row["formation"] or "",
            }
        )

    return {
        "date": date_affichee,
        "formation": f"{type_formation} {niveau_etudes} - {filiere} ({mode_etudes})",
        "groupe_td": groupe_td,
        "results": results,
        "message": f"{len(results)} cours trouvé(s).",
    }

if __name__ == "__main__":
    print(visualiser_planning_formation("10-04", "ia", "Master", "1", "classic", "Gr1"))