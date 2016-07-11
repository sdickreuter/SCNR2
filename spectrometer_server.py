
import zmq
import random
import sys
import time

context = zmq.Context()
socket = context.socket(zmq.PAIR)
port = "6667"
socket.bind("tcp://*:%s" % port)

poller = zmq.Poller()
poller.register(socket, zmq.POLLOUT) # POLLIN for recv, POLLOUT for send

running = True
msg = None

while running:
    try:


        while True:

            msg = socket.recv()
            print(msg)

            if msg == b'?':
                out = b'!'
            else:
                out = b'Server message to client'

            if poller.poll(1000):
                print('Sending: '+out.decode())
                socket.send(out)
            else:
                print("lost connection to client")


    except KeyboardInterrupt:
        print("Exiting ...")
        break

socket.close()
context.term()