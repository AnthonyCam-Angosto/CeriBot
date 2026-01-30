from flask import Blueprint, jsonify, render_template, request

from chatbot import chat

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

        
        return jsonify({"reponse":reponse})
    else:
        return "error"