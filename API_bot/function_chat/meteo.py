import json
from datetime import date
from urllib.parse import quote_plus
from urllib.request import urlopen
from urllib.error import HTTPError, URLError


def _code_meteo_vers_texte(code: int) -> str:
	correspondances = {
		0: "ciel dégagé",
		1: "principalement dégagé",
		2: "partiellement nuageux",
		3: "couvert",
		45: "brouillard",
		48: "brouillard givrant",
		51: "bruine légère",
		53: "bruine modérée",
		55: "bruine forte",
		61: "pluie légère",
		63: "pluie modérée",
		65: "pluie forte",
		71: "neige légère",
		73: "neige modérée",
		75: "neige forte",
		77: "grains de neige",
		80: "averses légères",
		81: "averses modérées",
		82: "averses fortes",
		85: "averses de neige légères",
		86: "averses de neige fortes",
		95: "orage",
		96: "orage avec grêle légère",
		99: "orage avec grêle forte",
	}
	return correspondances.get(code, "condition inconnue")


def meteo_jour(ville: str):
	if not ville or not ville.strip():
		return {"erreur": "Le nom de la ville est requis."}

	ville = ville.strip()

	try:
		geocoding_url = (
			"https://geocoding-api.open-meteo.com/v1/search"
			f"?name={quote_plus(ville)}&count=5&language=fr&format=json&country=FR"
		)
		with urlopen(geocoding_url, timeout=10) as response:
			geocoding_data = json.loads(response.read().decode("utf-8"))

		results = geocoding_data.get("results", [])
		if not results:
			return {"erreur": f"Ville française introuvable: {ville}."}

		results_fr = [
			resultat
			for resultat in results
			if resultat.get("country_code", "").upper() == "FR"
		]
		if not results_fr:
			return {"erreur": f"La ville {ville} n'est pas en France."}

		premier_resultat = results_fr[0]
		latitude = premier_resultat["latitude"]
		longitude = premier_resultat["longitude"]
		nom_ville = premier_resultat.get("name", ville)
		pays = premier_resultat.get("country", "")

		meteo_url = (
			"https://api.open-meteo.com/v1/forecast"
			f"?latitude={latitude}&longitude={longitude}"
			"&daily=weather_code,temperature_2m_max,temperature_2m_min"
			"&timezone=auto"
		)
		with urlopen(meteo_url, timeout=10) as response:
			meteo_data = json.loads(response.read().decode("utf-8"))

		daily = meteo_data.get("daily", {})
		if not daily:
			return {"erreur": "Données météo indisponibles pour cette ville."}

		date_jour = date.today().isoformat()
		dates = daily.get("time", [])

		if date_jour in dates:
			index = dates.index(date_jour)
		elif dates:
			index = 0
			date_jour = dates[0]
		else:
			return {"erreur": "Aucune donnée météo journalière reçue."}

		temp_max = daily.get("temperature_2m_max", [None])[index]
		temp_min = daily.get("temperature_2m_min", [None])[index]
		code_meteo = daily.get("weather_code", [None])[index]
		description = _code_meteo_vers_texte(code_meteo) if code_meteo is not None else "condition inconnue"

		return {
			"ville": nom_ville,
			"pays": pays,
			"date": date_jour,
			"temperature_min": temp_min,
			"temperature_max": temp_max,
			"description": description,
			"message": (
				f"Météo du {date_jour} à {nom_ville}"
				f"{f', {pays}' if pays else ''} : {description}, "
				f"min {temp_min}°C / max {temp_max}°C."
			),
		}

	except HTTPError as error:
		return {"erreur": f"Erreur HTTP météo ({error.code})."}
	except URLError:
		return {"erreur": "Impossible de contacter le service météo."}
	except (KeyError, IndexError, ValueError, json.JSONDecodeError):
		return {"erreur": "Réponse météo invalide ou incomplète."}


if __name__ == "__main__":
    print(meteo_jour("avignon"))