from flask import Blueprint, jsonify, render_template, request
import requests

from chatbot import chat
from speech.speech import speechRecognition

app_Router = Blueprint('index',__name__)

client=chat.start()
chatbot=chat.create_chat(client)

carte_verifier=False


@app_Router.route("/")
def page():
    return render_template("evaluation.html")

@app_Router.route("/chat", methods=['POST'])
def chat():
    '''
    Route pour gérer les requêtes du chatbot. Elle reçoit une requête JSON contenant une "requete" de l'utilisateur, 
    traite cette requête en utilisant le module chatbot, et retourne une réponse JSON contenant la réponse du chatbot.
    Si la requête contient "au revoir", la conversation est terminée et la carte est réinitialisée.
    '''
    global carte_verifier
    values=request.get_json()
    if(values.__contains__("requete")):
        requete=values["requete"]

        reponse,notverify=chat.run(chatbot,requete,carte_verifier)

        #si l'utilisateur dit au revoir, on met fin à la conversation
        if requete=='au revoir':
            carte_verifier=False
            return jsonify({"reponse":reponse,"fin":True,"notverify":False})
    
        return jsonify({"reponse":reponse,"fin":False,"notverify":notverify})
    else:
        return jsonify({"reponse":"error","fin":False,"notverify":False})

@app_Router.route("/speech", methods=["POST"])
def transcribe():
    '''Route pour gérer les requêtes de transcription vocale. Elle reçoit une requête JSON contenant des données audio et des paramètres,
    utilise le module de reconnaissance vocale pour transcrire l'audio, et retourne une réponse JSON contenant la transcription.
    '''
    req_data = request.get_json(force=True)

    #recupere la transcription de google speech recognition
    result_from_google = speechRecognition(req_data['data'], req_data['params'])
    print(result_from_google)
    reply = {"sentence": result_from_google}
    return jsonify(reply)


@app_Router.route("/verify", methods=["POST"])
def verify():
    '''Route pour gérer les requêtes de vérification de carte étudiante. Elle reçoit une requête JSON contenant une URL de carte étudiante,
    vérifie la validité de la carte en interrogeant un service de vérification externe, et retourne une réponse JSON indiquant si la carte est valide ou non.
    '''
    global carte_verifier
    url = request.get_json(force=True)["url"]
    if url.startswith("http://esc.gg/") or url.startswith("https://esc.gg/"):
        uuid=url.split("/")[-1]

        verification_url=f"https://router.europeanstudentcard.eu/esc-verifier-service/api/v1/cards/verify/{uuid}"
        request_result = requests.get(verification_url)
        if(request_result.status_code == 200):
            status = request_result.json().get("cardStatusType").get("key")
            if(status == "ACTIVE"):
                carte_verifier=True
                return jsonify({"valid": True})
    carte_verifier=False
    return jsonify({"valid": False})