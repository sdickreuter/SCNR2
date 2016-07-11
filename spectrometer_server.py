
import zmq
import numpy as np
import random
import sys
import time

context = zmq.Context()
socket = context.socket(zmq.PAIR)
port = "6667"
socket.bind("tcp://*:%s" % port)

poller = zmq.Poller()
poller.register(socket, zmq.POLLOUT) # POLLIN for recv, POLLOUT for send

data = np.ones(10)


def send_data(data):
    if poller.poll(1000):
        print('Sending: '+str(data))
        socket.send_pyobj(data)
    else:
        print("lost connection to client")


running = True
msg = None

while running:
    try:


        while True:

            msg = socket.recv_pyobj()
            print(msg)

            if msg == '?':
                send_data('!')
            elif msg == 'quit':
                print('Quiting by request of client')
                running = False
                break
            elif msg == 'data':
                print('Client requested data')
                send_data(data)
            else:
                send_data('Server message to client')


    except KeyboardInterrupt:
        print("Exiting ...")
        break

socket.close()
context.term()