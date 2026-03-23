from flask import Flask
from flask_socketio import SocketIO
from api.app_Router import app_Router, init_socketio

def start():
    app=Flask(__name__,template_folder="Template",static_folder="Static")
    socketio=SocketIO(app)
    app.register_blueprint(app_Router,url_prefix="/",socketio=socketio)
    init_socketio(socketio)
    app.run(host='0.0.0.0', threaded=True, debug=True)
