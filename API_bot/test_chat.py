import os
import requests


BASE_URL = os.getenv("FLASK_API_URL", "http://127.0.0.1:5000")
CHAT_URL = f"{BASE_URL}/chat"


def test_chat_api() -> None:
    payload = {
        #"requete": "Quelle est mon planning aujourd'hui? je suis en master 1 classic, filiere ilsen, groupe td 1"
        "requete": "quelle sont les salles disponibles aujourd'hui a partir de 14h pour 1h30?"
    }

    response = requests.post(CHAT_URL, json=payload, timeout=30)
    response.raise_for_status()

    data = response.json()
    print("Status:", response.status_code)
    print("Reponse API:", data)


if __name__ == "__main__":
    try:
        test_chat_api()
    except requests.RequestException as error:
        print("Impossible de joindre l'API Flask.")
        print(f"URL testee: {CHAT_URL}")
        print(f"Erreur: {error}")