import requests
import threading
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Message(BaseModel):
    text: str
    id: Optional[int] = 0


messages = []       # list to store messages
counter = 0         # initial lobal id for first message
nodes = ['http://secondary1:8000', 'http://secondary2:8000']

# endpoint to check master node is alive
@app.get("/")
def read_root():
    return {"Node": "This is master node"}

# endpoint to append message
@app.post("/append")
def append_message(message: Message):
    global messages, counter
    counter += 1
    message.id = counter

    rep_results = []    # list to save replication results

    def repFunc(node, message):

        request = requests.post(url=node+'/replica', data=message.json())
        try:
            result = request.json()
            if result['result'] == 'ok':
                rep_results.append(1)
            else:
                return False
        except:
            return False
        return True

    # for each node the separate thread of replication is starting
    for node in nodes:
        th = threading.Thread(target=repFunc, args=(node, message,))
        th.start()

    # waiting for replication for each node. Here we can implement Iteration 2 check for "w" parameter
    while True:
        if len(rep_results) == len(nodes):
            break

    messages.append(message)
    results = {"result": "ok", "message_text": message.text, "id": message.id}

    return results

# endpoint to list messages
@app.get("/list")
def list_messages():
    global messages
    results = {"messages": [m.text for m in sorted(messages, key=lambda x: x.id)]}
    return results
