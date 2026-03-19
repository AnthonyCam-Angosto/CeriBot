from google import genai
from google.genai import types
from chatbot.declaration_funct import declaration
from function_chat import emploi_temp, meteo

FONCTION_SECURISER = {"recherche_salle_disponnible", "visualiser_planning_formation"}

def start():
    client = genai.Client(api_key="AIzaSyBJB3W8xOQL7umAXOq61dvzJ9436rqPWHI")
    return client

def create_chat(client:genai.Client):
    tool = types.Tool(function_declarations=declaration())
    config=types.GenerateContentConfig(tools=[tool])

    chat=client.chats.create(model="gemini-2.5-flash-lite",config=config)
    return chat



def run(chat,requete,verifier_carte=False):
    #while True:
        #requete=input("ecrire votre requete: ")
    etat_carte = "verifiee" if verifier_carte else "non_verifiee"
    message_chat = (
        f"{requete}\n\n"
        f"[Contexte sécurité] Etat de la carte etudiante: {etat_carte}. "
        "Les fonctions liees a l'ecole (planning, salle) ne sont autorisees que si la carte est verifiee."
    )

    response=chat.send_message(message_chat)
    response,notverify = traitement_reponse(chat,response,verifier_carte)

    print(response.text)
    return response.text,notverify


def traitement_reponse(chat,response,verifier_carte=False):
    if response.candidates[0].content.parts[0].function_call:
        function_call = response.candidates[0].content.parts[0].function_call
        #print(f"Function to call: {function_call.name}")
        #print(f"Arguments: {function_call.args}")

        if function_call.name in FONCTION_SECURISER and not verifier_carte:
            final_response = chat.send_message(
                "La carte etudiante n'est pas verifiee. "
                "Je ne peux pas utiliser les fonctions liees a l'ecole pour le moment."
            )
            return final_response,True

        match function_call.name:
            case "recherche_salle_disponnible":
                result={
                        "result":[{
                            "libelle":"c130",
                            "capacite":"30"
                        },
                        {
                            "libelle":"c135",
                            "capacite":"26"
                        }
                        ]
                    }
            case "visualiser_planning_formation":
                result=emploi_temp.visualiser_planning_formation(
                    date=function_call.args.get("date",""),
                    filiere=function_call.args.get("filiere",""),
                    type_formation=function_call.args.get("type_formation",""),
                    niveau_etudes=function_call.args.get("niveau_etudes",0),
                    mode_etudes=function_call.args.get("mode_etudes","")
                )
            case "meteo_du_jour":
                result=meteo.meteo_jour(function_call.args.get("ville",""))

            case _:
                result={"erreur": f"Fonction inconnue: {function_call.name}"}

            
        final_response=chat.send_message(result.__str__())
        return final_response,False
    else:
        return response,False

if __name__=="__main__":
    chat=start()
    run(chat, "Bonjour")