from ast import literal_eval
import base64
import wave
import speech_recognition as sr

def speechRecognition(data, params):
    r = sr.Recognizer()

    audioFileName = 'test.wav'
    data = base64.b64decode(data)
    params = base64.b64decode(params)
    params = literal_eval(params.decode("utf-8"))

    wave_write = wave.open(audioFileName, "wb")
    wave_write.setparams(params)
    wave_write.writeframes(data)
    wave_write.close()

    audioFile = None
    with sr.AudioFile(audioFileName) as source:
        audioFile = r.record(source)

    try:
        text = r.recognize_google(audioFile, language="fr-FR")
        return text
    except Exception as e:
        print (e)