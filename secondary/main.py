from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel
import time

app = FastAPI()


class Message(BaseModel):
    text: str
    id: int
    w: int


class MessageList(BaseModel):
    message_list: List[Message]


class Delay(BaseModel):
    delay: int


messages = {}       # dict to store messages
configs = {
    'delay': 0
}

last_id = 0  # variable to keep last ordered message id

# endpoint to check secondary node is alive
@app.get("/")
def read_root():
    return {"Node": "This is secondary node"}

# endpoint for message replication
@app.post("/replica")
def save_message(message_list: MessageList):
    global messages, configs, last_id

    time.sleep(configs['delay'])

    for m in message_list.message_list:
        if not (m.id in messages):
            messages[m.id] = {"text": m.text,
                              "w": m.w}

            # looking for continious ids
            if m.id > last_id:
                for id in range(last_id + 1, m.id + 1):
                    if id in messages:
                        last_id = id
                    else:
                        break
            else:
                pass  # it will be wierd

    return {"result": "ok"}

# service endpoint to set delay
@app.post("/setdelay")
def set_delay(delay: Delay):
    global configs
    configs['delay'] = delay.delay
    results = {"result": "ok", "delay": configs['delay']}
    return results

# endpoint to list messages
@app.get("/list")
def list_messages():
    global messages, last_id

    if last_id == 0:
        return {"messages": []}
    else:
        return {"messages": [messages[m]['text'] for m in range(1, last_id+1)]}

# endpoint for heartbeats
@app.get("/ping")
def ping():
    return {"result": "ok"}
