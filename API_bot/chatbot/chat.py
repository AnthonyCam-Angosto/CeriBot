from google import genai
from google.genai import types
from chatbot.declaration_funct import declaration

def start():
    client = genai.Client(api_key="AIzaSyBJB3W8xOQL7umAXOq61dvzJ9436rqPWHI")
    return client

def create_chat(client:genai.Client):
    tool = types.Tool(function_declarations=declaration())
    config=types.GenerateContentConfig(tools=[tool])

    chat=client.chats.create(model="gemini-2.5-flash-lite",config=config)
    return chat



def run(chat,requete):
    #while True:
        #requete=input("ecrire votre requete: ")
    response=chat.send_message(requete)
    print(response)
    #traitement_reponse(chat,response)
    return response.text


def traitement_reponse(chat,response):
    if response.candidates[0].content.parts[0].function_call:
        function_call = response.candidates[0].content.parts[0].function_call
        #print(f"Function to call: {function_call.name}")
        #print(f"Arguments: {function_call.args}")
        if function_call.name=="recherche_salle_disponnible":
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
        else :
            result={
                "results": [
                    {
                    "code": "2-M2EN",
                    "start": "2025-09-30T08:00:00+00:00",
                    "end": "2025-09-30T09:30:00+00:00",
                    "title": "Matière : Rentree specifique\nEnseignants : REDACTED Name, REDACTED Name, REDACTED Name\nPromotions : M1 INGE DU LOGICIEL DE LA SOCIETE NUM (ILSEN), M1 INTELLIGENCE ARTIFICIELLE (IA), M1 SYSTEMES INFORMATIQUES COMMUNICANTS (SICOM), M2 INGE DU LOGICIEL DE LA SOCIETE NUM (ILSEN), M2 INTELLIGENCE ARTIFICIELLE (IA), M2 SYSTEMES INFORMATIQUES COMMUNICANTS (SICOM)\nTD : 2, PRE-RENTREES SPECIFIQUES 3\nSalles : Amphi Ada, Amphi Blaise\nMémo : \"CERI\"\n",
                    "type": "",
                    "memo": None
                    }
                ]
            }
        final_response=chat.send_message(result.__str__())
        print(final_response.text)
    else:
        print(response.text)


if __name__=="__main__":
    chat=start()
    run(chat)