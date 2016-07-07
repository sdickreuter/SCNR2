import zmq
import random
import sys
import time

context = zmq.Context()
socket = context.socket(zmq.PAIR)
port = "5556"
socket.connect("tcp://localhost:%s" % port)
#socket.bind("ipc://spectrometer")
try:

    socket.send(b'?')
    msg = socket.recv()
    if msg == b'!':
        print('Connected to server')
    else:
        raise RuntimeError("Could not connect to Server")

    while True:
        msg = socket.recv()
        print(msg)
        socket.send(b"client message to server1")
        socket.send(b"client message to server2")
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting ...")
finally:
    # clean up
    socket.close()
    context.term()