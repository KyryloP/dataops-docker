import uvicorn
import requests
import threading

from typing import Optional
from fastapi import FastAPI

from pydantic import BaseModel

app = FastAPI()


class Message(BaseModel):
    text: str
    id: Optional[int] = 0


messages = []
counter = 1
nodes = ['http://secondary1:8000', 'http://secondary2:8000']

@app.get("/")
def read_root():
    return {"Node": "This is master node"}


# replication function
def repFunc(node, message):
    request = requests.post(url=node+'/replica', data=message.json())
    try:
        result = request.json()
        if result['result'] == 'ok':
            pass
        else:
            return False
    except: 
        return False
    return True


@app.post("/append")
def append_message(message: Message):
    global messages, counter
    message.id = counter

    rep_results = []

    def repFunc(node, message):
                
        request = requests.post(url=node+'/replica', data=message.json())
        try:
            result = request.json()
            if result['result'] == 'ok':
                print(f'Replication to {node} finished' )
                rep_results.append(1)
                pass
            else:
                return False
        except: 
            return False
        return True

    for node in nodes:
            th = threading.Thread(target=repFunc, args=(node, message,))
            th.start()
            print(f'Replication to {node} started' )
    
    print ('Waiting for replication ...')
    while True:
        if len(rep_results) == len(nodes):
            break

    messages.append(message)
    counter += 1

    results = {"result": "ok", "message_text": message.text}

    return results


@app.get("/list")
def list_messages():
    global messages
    results = {"messages": [m.text for m in messages]}
    return results