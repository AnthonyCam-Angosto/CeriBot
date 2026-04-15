from flask import Blueprint, jsonify, render_template, request,Response
import requests
from flask_socketio import SocketIO

from chatbot import chat as chat_service
from function_chat.emploi_temp import visualiser_planning_formation
from speech.speech import speechRecognition

app_Router = Blueprint('index',__name__)

def init_socketio(socketio_instance):
    global socketio
    socketio = socketio_instance

client=chat_service.start()
chatbot=chat_service.create_chat(client)

carte_verifier=False
path_page="index.html"


@app_Router.route("/")
def page():
    global path_page
    return render_template(path_page)


def change_page(path):
    global path_page
    path_page=path
    socketio.emit("change_page", "reload", to=None, skip_sid=None)

def info_planning(date, filiere, type_formation, niveau_etudes, mode_etudes, groupe_td):
    path_page="planning.html"
    socketio.emit("info_planning", {"date": date, "filiere": filiere, "type_formation": type_formation, "niveau_etudes": niveau_etudes, "mode_etudes": mode_etudes, "groupe_td": groupe_td}, to=None, skip_sid=None)


@app_Router.route("/test_planning", methods=['GET'])
def test_planning():
    info_planning("11-03", "ilsen", "Master", "1", "classic", "Gr1")
    return Response(status=200)


@app_Router.route("/chat", methods=['POST'])
def chat_route():
    '''
    Route pour gérer les requêtes du chatbot. Elle reçoit une requête JSON contenant une "requete" de l'utilisateur, 
    traite cette requête en utilisant le module chatbot, et retourne une réponse JSON contenant la réponse du chatbot.
    Si la requête contient "au revoir", la conversation est terminée et la carte est réinitialisée.
    '''
    global carte_verifier
    values=request.get_json()
    if(values.__contains__("requete")):
        requete=values["requete"]

        reponse,notverify=chat_service.run(chatbot,requete,carte_verifier)

        #si l'utilisateur dit au revoir, on met fin à la conversation
        if requete.lower().find('au revoir') != -1:
            carte_verifier=False
            change_page("evaluation.html")
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
    reply = {"sentence": result_from_google}
    print(f"Transcription obtenue: {result_from_google}")
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



@app_Router.route("/planning", methods=["GET"])
def planning():
    date = request.args.get("date", "")
    filiere = request.args.get("filiere", "")
    type_formation = request.args.get("type_formation", "")
    niveau_etudes = request.args.get("niveau_etudes", "")
    mode_etudes = request.args.get("mode_etudes", "")
    groupe_td = request.args.get("groupe_td", request.args.get("groupe td", ""))

    result = visualiser_planning_formation(
        date,
        filiere,
        type_formation,
        niveau_etudes,
        mode_etudes,
        groupe_td,
    )
    return jsonify(result)