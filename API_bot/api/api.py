from flask import Flask
from api.app_Router import app_Router

def start():
    app=Flask(__name__,template_folder="Template",static_folder="Static")
    app.register_blueprint(app_Router)
    app.run(host='0.0.0.0', threaded=True, debug=True)
