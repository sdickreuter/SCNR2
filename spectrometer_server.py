
import zmq
import random
import sys
import time

context = zmq.Context()
socket = context.socket(zmq.PAIR)
port = "5556"
socket.bind("tcp://*:%s" % port)
#socket.bind("ipc://spectrometer")
try:

    connected = False
    while not connected:
        msg = socket.recv()
        if msg == b'?':
            socket.send(b'!')
            print("Client has connected")
            connected = True

    while True:
        socket.send(b"Server message to client3")
        msg = socket.recv()
        print(msg)
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting ...")
finally:
    # clean up
    socket.close()
    context.term()