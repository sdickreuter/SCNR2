import zmq
import numpy as np
import random
import sys
import time

import subprocess
import os

context = zmq.Context()
socket = context.socket(zmq.PAIR)
port = "6667"
socket.connect("tcp://localhost:%s" % port)


in_poller = zmq.Poller()
in_poller.register(socket, zmq.POLLIN) # POLLIN for recv, POLLOUT for send
out_poller = zmq.Poller()
out_poller.register(socket, zmq.POLLOUT) # POLLIN for recv, POLLOUT for send

#evts = poller.poll(1000) # wait *up to* one second for a message to arrive.

connected = False

print("Trying to connect to Server")
while not connected:
    #print(i)
    sent = False
    if not sent:
        if out_poller.poll(1000): # 10s timeout in milliseconds
            socket.send_pyobj('?',zmq.NOBLOCK)
            print('sent ?')
            sent = True
        else:
            sent = False

    received = False
    if sent:
        if in_poller.poll(1000):
            msg = socket.recv_pyobj(flags=zmq.NOBLOCK)
            print(msg)
            if msg == '!':
                received = True
        else:
            received = False

    print(sent)
    print(received)

    if sent and received:
        connected = True
        break
    elif not received :
        print("No connection to server, starting server")
        # p = subprocess.run(['python', 'spectrometer_server.py'])
        p = subprocess.Popen(['python', 'spectrometer_server.py'])
        # subprocess.call('python spectrometer_server.py', shell=True)
        # subprocess.call(['python', 'spectrometer_server.py'])
        time.sleep(1)

print('Connected to server')


def make_request(req):
    sent = False
    received = False

    if out_poller.poll(1000):
        socket.send_pyobj(req)
        sent = True

    if in_poller.poll(1000):
        #msg = socket.recv()
        data = socket.recv_pyobj()
        received = True

    if sent and received:
        return data
    elif (not sent) and (not received):
        print("Server not answering, quitting")
        raise KeyboardInterrupt()


try:
    #while True:
    for i in range(10):
        sent = False
        received = False

        if out_poller.poll(1000):
            socket.send_pyobj("client message to server")
            sent = True

        if in_poller.poll(1000):
            msg = socket.recv_pyobj()
            received = True

        if sent and received:
            print(msg)
            time.sleep(1)
        elif (not sent) and (not received):
            print("Server not answering, quitting")
            raise KeyboardInterrupt()


    data = make_request('data')
    print(data)
    socket.send_pyobj('quit')



except KeyboardInterrupt:
    print("Exiting ...")
finally:
    # clean up
    socket.close()
    context.term()