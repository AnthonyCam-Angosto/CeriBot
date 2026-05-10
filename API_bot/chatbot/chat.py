from google import genai
from google.genai import types
from api import app_Router
from chatbot.declaration_funct import declaration
from function_chat import emplacement_salle, emploi_temp, meteo, salle_dispo
import re
import time
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

#FONCTION_SECURISER = {"recherche_salle_disponnible", "visualiser_planning_formation"}
FONCTION_SECURISER = {}
MAX_RETRIES = 3
RETRY_DELAY = 2  # secondes
AVAILABLE_MODELS = [
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash"
]

MOTS_CLES_SECURISES = (
#    "planning",
#    "emploi du temps",
#    "emploi_temp",
)
SECURITY_BLOCK_MESSAGE = (
    "La carte etudiante n'est pas verifiee. "
    "Je ne peux pas utiliser les fonctions lieesc a l'ecole pour le moment."
)

_CLIENT = None
_ACTIVE_CHAT = None
_ACTIVE_MODEL_INDEX = 0
SYSTEM_INSTRUCTION = (
    "Tu es un robot d'accueil universitaire pour l'université d'Avignon dnas le departement d'informatique. "
    "Quand une des fonctions disponibles permet de répondre à la demande, "
    "utilise un function call au lieu d'inventer la réponse en texte libre. "
    "Après le résultat de fonction, réponds avec une seule phrase courte."
)


def _extract_function_call(response):
    candidates = getattr(response, "candidates", []) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", []) or []
        for part in parts:
            function_call = getattr(part, "function_call", None)
            if function_call:
                return function_call
    return None


def _extract_text(response) -> str:
    candidates = getattr(response, "candidates", []) or []
    text_parts = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", []) or []
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                text_parts.append(text)
    return "".join(text_parts).strip()


def _is_limit_error(error: Exception) -> bool:
    message = str(error).lower()
    tokens = ["429", "quota", "rate limit", "resource has been exhausted", "limit exceeded"]
    return any(token in message for token in tokens)


def _is_model_not_found_error(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "404" in message
        and "not_found" in message
        and ("model" in message or "models/" in message)
    )


def _is_model_format_error(error: Exception) -> bool:
    message = str(error).lower()
    return "unexpected model name format" in message


def _retry_delay_from_error(error: Exception) -> int:
    message = str(error).lower()
    match = re.search(r"retry in\s+(\d+(?:\.\d+)?)s", message)
    if match:
        return max(1, int(float(match.group(1))))
    match = re.search(r"retrydelay['\"]?:\s*'?([0-9]+)s", message)
    if match:
        return max(1, int(match.group(1)))
    return RETRY_DELAY


def _requires_card_context(requete: str) -> bool:
    requete_normalisee = requete.lower()
    return any(mot_cle in requete_normalisee for mot_cle in MOTS_CLES_SECURISES)


def _switch_chatbot() -> bool:
    global _CLIENT, _ACTIVE_CHAT, _ACTIVE_MODEL_INDEX

    if _CLIENT is None:
        _CLIENT = start()

    while _ACTIVE_MODEL_INDEX < len(AVAILABLE_MODELS) - 1:
        _ACTIVE_MODEL_INDEX += 1
        next_model = AVAILABLE_MODELS[_ACTIVE_MODEL_INDEX]
        try:
            _ACTIVE_CHAT = create_chat(_CLIENT, model=next_model)
            print(f"Basculement automatique vers le modèle: {next_model}")
            return True
        except Exception as switch_error:
            if _is_model_not_found_error(switch_error):
                print(f"Modele ignore car indisponible: {next_model}")
                continue
            raise

    return False

def start():
    global _CLIENT
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY non trouvée dans les variables d'environnement. Vérifiez le fichier .env")
    client = genai.Client(api_key=api_key)
    _CLIENT = client
    return client

def create_chat(client:genai.Client, model: str | None = None):
    global _ACTIVE_CHAT, _ACTIVE_MODEL_INDEX
    tool = types.Tool(function_declarations=declaration())
    config=types.GenerateContentConfig(
        tools=[tool],
        system_instruction=SYSTEM_INSTRUCTION,
    )
    selected_model = (model or AVAILABLE_MODELS[_ACTIVE_MODEL_INDEX]).strip().lower()
    if selected_model.startswith("models/"):
        selected_model = selected_model.split("/", 1)[1]

    chat=client.chats.create(model=selected_model,config=config)
    print(f"Chatbot initialisé avec le modèle: {selected_model}")

    if selected_model in AVAILABLE_MODELS:
        _ACTIVE_MODEL_INDEX = AVAILABLE_MODELS.index(selected_model)
    _ACTIVE_CHAT = chat

    return chat



def run(chat, requete, verifier_carte=False):
    global _ACTIVE_CHAT
    if _requires_card_context(requete) and not verifier_carte:
        return SECURITY_BLOCK_MESSAGE, True

    message_chat = (
        f"{requete}\n\n"
        "[Instruction tools] Si une fonction disponible permet de répondre, "
        "appelle cette fonction d'abord."
    )
    if _requires_card_context(requete):
        etat_carte = "verifiee" if verifier_carte else "non_verifiee"
        message_chat = (
            f"{message_chat}\n"
            f"[Contexte sécurité] Etat de la carte etudiante: {etat_carte}. "
            "Les fonctions liees a l'ecole (planning, salle,emploit du temps) ne sont autorisees que si la carte est verifiee."
        )
    chat_instance = _ACTIVE_CHAT or chat

    # Retry logic pour gérer les erreurs serveur
    for attempt in range(MAX_RETRIES):
        try:
            response = chat_instance.send_message(message_chat)
            response, notverify = traitement_reponse(chat_instance, response, verifier_carte)
            response_text = _extract_text(response)
            print(response_text)
            return response_text, notverify
        except Exception as e:
            print(f"Erreur tentative {attempt + 1}/{MAX_RETRIES}: {str(e)}")
            if _is_limit_error(e) or _is_model_not_found_error(e) or _is_model_format_error(e):
                switched = _switch_chatbot()
                if switched:
                    chat_instance = _ACTIVE_CHAT
                    continue
            if attempt < MAX_RETRIES - 1:
                retry_delay = _retry_delay_from_error(e)
                print(f"Nouvelle tentative dans {retry_delay} secondes...")
                time.sleep(retry_delay)
            else:
                if _is_limit_error(e):
                    retry_delay = _retry_delay_from_error(e)
                    return (
                        f"Le quota Gemini est temporairement atteint. Reessayez dans environ {retry_delay} secondes.",
                        False,
                    )
                if _is_model_not_found_error(e):
                    return (
                        "Aucun modele Gemini compatible n'a ete trouve pour cette configuration API.",
                        False,
                    )
                if _is_model_format_error(e):
                    return (
                        "Le format d'un nom de modele est invalide. Utilisez des noms du type gemini-2.5-flash.",
                        False,
                    )
                return "Désolé, le serveur est actuellement indisponible. Veuillez réessayer dans quelques instants.", False

    # Garde-fou: evite un retour None si MAX_RETRIES est invalide (ex: 0) ou modifie dynamiquement.
    return "Désolé, le serveur est actuellement indisponible. Veuillez réessayer dans quelques instants.", False


def traitement_reponse(chat,response,verifier_carte=False):
    function_call = _extract_function_call(response)
    if function_call:
        #print(f"Function to call: {function_call.name}")
        #print(f"Arguments: {function_call.args}")

        if function_call.name in FONCTION_SECURISER and not verifier_carte:
            final_response = chat.send_message(SECURITY_BLOCK_MESSAGE)
            return final_response,True
        print(f"Appel de fonction: {function_call.name} avec arguments {function_call.args}")
        match function_call.name:
            case "recherche_salle_disponnible":
                result=salle_dispo.recherche_salle_disponnible(
                    date=function_call.args.get("date",""),
                    heure_debut=function_call.args.get("heure de debut",""),
                    temps_utilisation=function_call.args.get("temps d'utilisation de la salle","")
                )
            case "visualiser_planning_formation":
                result=emploi_temp.visualiser_planning_formation(
                    date=function_call.args.get("date",""),
                    filiere=function_call.args.get("filiere",""),
                    type_formation=function_call.args.get("type_formation",""),
                    niveau_etudes=function_call.args.get("niveau_etudes",0),
                    mode_etudes=function_call.args.get("mode_etudes",""),
                    groupe_td=function_call.args.get("groupe td","")
                )
                app_Router.info_planning(
                    date=function_call.args.get("date",""),
                    filiere=function_call.args.get("filiere",""),
                    type_formation=function_call.args.get("type_formation",""),
                    niveau_etudes=function_call.args.get("niveau_etudes",0),
                    mode_etudes=function_call.args.get("mode_etudes",""),
                    groupe_td=function_call.args.get("groupe td","")
                )
            case "meteo_du_jour":
                result=meteo.meteo_jour(function_call.args.get("ville",""))
            
            case "emplacement_salle":
                result=emplacement_salle.emplacement_salle(function_call.args.get("salle",""))

            case _:
                result={"erreur": f"Fonction inconnue: {function_call.name}"}

            
        final_response=chat.send_message(result.__str__())
        return final_response,False
    else:
        return response,False
