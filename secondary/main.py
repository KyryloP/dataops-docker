from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
import time

app = FastAPI()


class Message(BaseModel):
    text: str
    id: int
    w: int


class Delay(BaseModel):
    delay: int


messages = []       # list to store messages
configs = {
    'delay': 0
}

# endpoint to check secondary node is alive
@app.get("/")
def read_root():
    return {"Node": "This is secondary node"}

# endpoint for message replication
@app.post("/replica")
def save_message(message: Message):
    global messages, configs

    time.sleep(configs['delay'])
    messages.append(message)
    results = {"result": "ok"}
    return results

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
    global messages
    results = {"messages": [m.text for m in sorted(messages, key=lambda x: x.id) ]}
    return results
