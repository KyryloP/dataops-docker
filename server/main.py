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

class CountDownLatch(object):
    def __init__(self, count=1):
        self.count = count
        self.lock = threading.Condition()

    def count_down(self):
        self.lock.acquire()
        self.count -= 1
        if self.count <= 0:
            self.lock.notifyAll()
        self.lock.release()

    def to_wait(self):
        self.lock.acquire()
        while self.count > 0:
            self.lock.wait()
        self.lock.release()
    
    def __dict__(self):         
        return self.count

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
                   'pending': [],
                   'retry_latch': CountDownLatch(1)}


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
                         'states': dict(zip([n for n in range(1, nodes_num+1)], [0 for n in range(1, nodes_num+1)])),
                         'replicas': CountDownLatch(message.w)}
    
    messages[counter]['replicas'].count_down() # initial decrement for master node

    def repFunc(node, host, message):

        try:
            request = requests.post(
                url=host+'/replica', json={"message_list": [message.dict()]}, timeout=2)
            result = request.json()
            if result['result'] == 'ok':
                messages[counter]['states'][node] = 1
                messages[counter]['replicas'].count_down()
            else:
                nodes[node]['pending'].append(message)
                nodes[node]['retry_latch'].count_down()  
        except:
            nodes[node]['pending'].append(message)
            nodes[node]['retry_latch'].count_down()

    
    # for each node the separate thread of replication is starting
    for node in nodes:
        th = threading.Thread(target=repFunc, args=(
            node, nodes[node]['host'], message,))
        th.start()

    # waiting for replication to w-1 node
    messages[counter]['replicas'].to_wait()

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
    
    # filter some keys for displaying
    results = {'health': {}}
    for node in nodes:
        results['health'][node] = {}
        for k in nodes[node]:
            if k not in ['host', 'retry_latch']:
                results['health'][node][k] = nodes[node][k]

    return results


def heartbeat(node):
    global nodes

    while True: # Here i think it's appropriate - heartbeats are supposed to work forever
        
        # sleep for timeuot set
        time.sleep(nodes[node]['timeout'])
        state = 0  # initial assume that node is dead

        # sending request
        try:
            result = requests.get(url=nodes[node]['host']+'/ping', timeout=2)
            state = 1 if result.json()['result'] == 'ok' else 0
        except:
            pass

        # writing results in moving pings history
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
            nodes[node]['timeout'] = 2
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

    while True: # It is NOT busy loop - CountDownLatch is used below

        # waiting for start
        nodes[node]['retry_latch'].to_wait()        

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
                        messages[m.id]['replicas'].count_down() 

                    # remove batch from list (queue)
                    del nodes[node]['pending'][:batchsize]

            except:
                pass
        
        # if we managed to resend all messages - lock to waiting
        if len(nodes[node]['pending']) == 0:
            nodes[node]['retry_latch']=CountDownLatch(1)


# Threads for heartrbeats check
for node in nodes:
    hb = threading.Thread(target=heartbeat, args=(node,))
    hb.start()

# Threards for retry process
for node in nodes:
    rt = threading.Thread(target=retry, args=(node, max_batch_size))
    rt.start()