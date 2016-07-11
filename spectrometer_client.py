import zmq
import random
import sys
import time

import subprocess
import os

context = zmq.Context()
socket = context.socket(zmq.REQ)
port = "6667"
socket.connect("tcp://localhost:%s" % port)


poller = zmq.Poller()
poller.register(socket, zmq.POLLIN) # POLLIN for recv, POLLOUT for send
#evts = poller.poll(1000) # wait *up to* one second for a message to arrive.

connected = False

try:
    print("?")
    socket.send(b'?', flags=zmq.NOBLOCK)
    print("! ?")
    msg = None
    msg = socket.recv(flags=zmq.NOBLOCK)
    print(msg)
    if msg == b'!':
        connected = True
        print('Connected to server')
    else:
        raise zmq.ZMQError()
except zmq.ZMQError as e:
    print("No connection to server, starting server")
    #p = subprocess.run(['python', 'spectrometer_server.py'])
    p = subprocess.Popen(['python', 'spectrometer_server.py'])
    #subprocess.call('python spectrometer_server.py', shell=True)
    #subprocess.call(['python', 'spectrometer_server.py'])
    time.sleep(1)


try:
    if not connected:
        socket.send(b'?')
        msg = socket.recv()
        if msg == b'!':
            print('Connected to server')
        else:
            raise RuntimeError("Could not connect to Server")

    #while True:
    for i in range(10):
        msg = socket.recv()
        print(msg)
        socket.send(b"client message to server")
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting ...")
finally:
    # clean up
    socket.close()
    context.term()