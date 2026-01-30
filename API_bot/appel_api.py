import requests
import json

url = 'http://127.0.0.1:5000/chat'


content={"requete":"salut"}
x = requests.post(url,json=content)
print(x.text)