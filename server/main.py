import requests
import threading
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
import time
import json

app = FastAPI()


class Message(BaseModel):
    text: str
    id: Optional[int] = 0
    w: int


messages = {}       # dict to store messages
counter = 0         # initial global id

port = 8000
nodes_num = 2
nodes = {}

# nodes dict with initial nodes info
for node in range(1, nodes_num+1):
    nodes[node] = {'host': 'http://secondary'+str(node)+':'+str(port),
                   'state': 'healthy',
                   'pings_success': 12,
                   'pings_error': 0,
                   'pings': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                   'timeout': 1,
                   'pending': []}


# max batch size for retry attempts
max_batch_size = 10

# endpoint to check master node is alive
@app.get("/")
def read_root():
    return {"Node": "This is master node"}

# endpoint to append message
@app.post("/append")
def append_message(message: Message):
    global messages, nodes, counter

    # validate w-parameter
    if message.w > len(nodes) + 1:
        return {"result": "error", "details": "Write concern parameter exeeds total nodes number"}

    # check read-only
    if (sum([1 if n[1]['state'] == 'dead' else 0 for n in nodes.items()]) == len(nodes)) and (message.w > 1):
        return {"result": "error", "details": "Cluster in read-only state"}

    counter += 1
    message.id = counter

    messages[counter] = {"text": message.text,
                         "w": message.w,
                         'states': dict(zip([n for n in range(1, nodes_num+1)], [0 for n in range(1, nodes_num+1)]))}

    def repFunc(node, host, message):

        try:
            request = requests.post(
                url=host+'/replica', json={"message_list": [message.dict()]}, timeout=2)
            result = request.json()
            if result['result'] == 'ok':
                messages[counter]['states'][node] = 1
            else:
                nodes[node]['pending'].append(message)
        except:
            nodes[node]['pending'].append(message)

    # for each node the separate thread of replication is starting
    for node in nodes:
        th = threading.Thread(target=repFunc, args=(
            node, nodes[node]['host'], message,))
        th.start()

    # waiting for replication for each node
    while True: # I realize that it is awfull and I hope until defending my app I'll change it
        if sum(messages[message.id]['states'].values()) >= message.w - 1:
            break

    return {"result": "ok", "message_text": message.text, "id": message.id}

# endpoint to list messages
@app.get("/list")
def list_messages():
    global messages
    results = {"messages": [messages[m]['text'] for m in messages]}
    return results

# endpoint to check nodes health
@app.get("/health")
def health():
    global nodes
    results = {"health": nodes}
    return results


def heartbeat(node):
    global nodes

    while True: # Here i think it's appropriate, because heartbeats are supposed to work forever
        
        # sleep for timeuot set
        time.sleep(nodes[node]['timeout'])
        state = 0  # initial assume that node is dead

        # sending request
        try:
            result = requests.get(url=nodes[node]['host']+'/ping', timeout=2)
            state = 1 if result.json()['result'] == 'ok' else 0
        except:
            pass

        # writing results in moving ping history
        nodes[node]['pings'].pop(-1)
        nodes[node]['pings'].insert(0, state)

        # reading last states
        errors = nodes[node]['pings_error']
        succeed = nodes[node]['pings_success']

        # conditional state change
        if state == 1:
            succeed = 12 if succeed >= 12 else succeed + 1
            nodes[node]['pings_success'] = succeed
            nodes[node]['pings_error'] = 0
            nodes[node]['timeout'] = 2

        else:
            errors = 12 if errors >= 12 else errors + 1
            nodes[node]['pings_error'] = errors
            nodes[node]['pings_success'] = 0

        # conditional set of timeouts
        if errors <= 4:
            nodes[node]['timeout'] = 5
        elif errors <= 8:
            nodes[node]['timeout'] = 10
        else:
            nodes[node]['timeout'] = 30

        # conditional set state names
        if succeed > 4:
            nodes[node]['state'] = 'healthy'
        elif errors > 4:
            nodes[node]['state'] = 'dead'
        else:
            nodes[node]['state'] = 'unstable'


def retry(node, max_batch_size):
    global nodes, messages

    while True: # I realize that it is awfull and I hope until defending my app I'll change it

        # waiting timeouts set for node
        time.sleep(nodes[node]['timeout'])

        # in case of healt node and not empty queue of retry
        if (nodes[node]['state'] == 'healthy') and (len(nodes[node]['pending']) > 0):

            batchsize = len(nodes[node]['pending']) if len(nodes[node]['pending']) < max_batch_size else max_batch_size
            batch = nodes[node]['pending'][:batchsize]

            try:
                request = requests.post(url=nodes[node]['host'] + '/replica', json={
                                        "message_list": [m.dict() for m in batch]}, timeout=2)
                result = request.json()
                if result['result'] == 'ok':
                    # setting result for replication to message and node key
                    for m in batch:
                        messages[m.id]['states'][node] = 1

                    # remove batch from list (queue)
                    del nodes[node]['pending'][:batchsize]

            except:
                pass


# Threads for heartrbeats check
for node in nodes:
    hb = threading.Thread(target=heartbeat, args=(node,))
    hb.start()

# Threards for retry process
for node in nodes:
    rt = threading.Thread(target=retry, args=(node, max_batch_size))
    rt.start()