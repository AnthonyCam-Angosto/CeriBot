import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "calendars.db"


def trie(db_path: Path = DB_PATH):
	"""
	Supprime les doublons de cours dans la table events.

	Deux lignes sont considérées doublons si elles partagent:
	summary, dtstart, dtend, location, matiere, enseignant, type_cours.
	La ligne conservée agrège les valeurs de formation et td_group.
	"""
	conn = sqlite3.connect(db_path)
	cur = conn.cursor()

	try:
		cur.execute("SELECT COUNT(*) FROM events")
		total_before = cur.fetchone()[0]

		cur.executescript(
			"""
			DROP TABLE IF EXISTS dedup_keep;

			CREATE TEMP TABLE dedup_keep AS
			SELECT
				MIN(id) AS keep_id,
				COALESCE(summary, '') AS summary,
				COALESCE(dtstart, '') AS dtstart,
				COALESCE(dtend, '') AS dtend,
				COALESCE(location, '') AS location,
				COALESCE(matiere, '') AS matiere,
				COALESCE(enseignant, '') AS enseignant,
				COALESCE(type_cours, '') AS type_cours,
				GROUP_CONCAT(DISTINCT NULLIF(TRIM(formation), '')) AS merged_formation,
				GROUP_CONCAT(DISTINCT NULLIF(TRIM(td_group), '')) AS merged_td_group,
				COUNT(*) AS grp_count
			FROM events
			GROUP BY
				COALESCE(summary, ''),
				COALESCE(dtstart, ''),
				COALESCE(dtend, ''),
				COALESCE(location, ''),
				COALESCE(matiere, ''),
				COALESCE(enseignant, ''),
				COALESCE(type_cours, '');

			UPDATE events
			SET
				formation = (
					SELECT merged_formation
					FROM dedup_keep
					WHERE dedup_keep.keep_id = events.id
				),
				td_group = (
					SELECT merged_td_group
					FROM dedup_keep
					WHERE dedup_keep.keep_id = events.id
				)
			WHERE id IN (SELECT keep_id FROM dedup_keep);

			DELETE FROM events
			WHERE id NOT IN (SELECT keep_id FROM dedup_keep);
			"""
		)

		cur.execute("SELECT COUNT(*) FROM events")
		total_after = cur.fetchone()[0]

		cur.execute("SELECT COUNT(*) FROM dedup_keep WHERE grp_count > 1")
		duplicate_groups = cur.fetchone()[0]

		conn.commit()
		deleted = total_before - total_after
		return {
			"avant": total_before,
			"apres": total_after,
			"supprimes": deleted,
			"groupes_doublons": duplicate_groups,
		}
	finally:
		conn.close()


if __name__ == "__main__":
	result = trie()
	print(result)
