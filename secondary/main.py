import uvicorn
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
import time

app = FastAPI()


class Message(BaseModel):
    text: str
    id: int

class Delay(BaseModel):
    delay: int

messages = []
configs = {
    'delay': 0
}

# Just to check availibility
@app.get("/")
def read_root():
    return {"Node": "This is secondary node"}

# Endpoint
@app.post("/replica")
def save_message(message: Message):
    global messages, counter, configs

    time.sleep(configs['delay'])
    messages.append(message)
    results = {"result": "ok"}
    return results

@app.post("/setdelay")
def set_delay(delay: Delay):
    global configs
    configs['delay']= delay.delay
    results = {"result": "ok"}
    return results


@app.get("/list")
def list_messages():
    global messages
    results = {"messages": [m.text for m in messages]}
    return results