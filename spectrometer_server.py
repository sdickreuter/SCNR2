
import zmq
import random
import sys
import time

context = zmq.Context()
socket = context.socket(zmq.REP)
port = "6667"
socket.bind("tcp://*:%s" % port)
#socket.bind("ipc://spectrometer")
connected = False
running = True
while running:
    try:

        while not connected:
            msg = socket.recv()
            if msg == b'?':
                socket.send(b'!')
                print("Client has connected")
                connected = True

        while True:
            socket.send(b"Server message to client",zmq.NOBLOCK)

            try:
                msg = socket.recv(zmq.NOBLOCK)
                print(msg)
                #time.sleep(1)
            except zmq.ZMQError as e:
                print("lost connection to client")
                connected = False

    except KeyboardInterrupt:
        print("Exiting ...")
        break

socket.close()
context.term()