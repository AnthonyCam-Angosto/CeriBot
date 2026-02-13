from flask import Blueprint, jsonify, render_template, request

from chatbot import chat
from speech.speech import speechRecognition

app_Router = Blueprint('index',__name__)

client=chat.start()
chatbot=chat.create_chat(client)


@app_Router.route("/")
def page():
    return render_template("index.html")

@app_Router.route("/chat", methods=['POST'])
def json():
    values=request.get_json()
    if(values.__contains__("requete")):
        requete=values["requete"]

        reponse=chat.run(chatbot,requete)

        if requete=='au revoir':
            return jsonify({"reponse":reponse,"fin":True})
    
        return jsonify({"reponse":reponse,"fin":False})
    else:
        return "error"

@app_Router.route("/speech", methods=["POST"])
def transcribe():
    req_data = request.get_json(force=True)

    # collect the transcription
    result_from_google = speechRecognition(req_data['data'], req_data['params'])

    print(result_from_google)
    # send back the predicted keyword in json format
    reply = {"sentence": result_from_google}

    return jsonify(reply)