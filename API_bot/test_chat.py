from chatbot import chat


if __name__=="__main__":
    client=chat.start()
    chatbot=chat.create_chat(client)
    res=chat.run(chatbot, "Quelle sont mes cours le 11/03 et je suis en m1 classic et en filliere ilsen ?",True)