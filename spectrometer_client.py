import zmq
import numpy as np
import random
import sys
import time

import subprocess
import os

class SpectrometerClient:

    context = zmq.Context()
    socket = context.socket(zmq.PAIR)
    port = "6667"
    socket.connect("tcp://localhost:%s" % port)


    in_poller = zmq.Poller()
    in_poller.register(socket, zmq.POLLIN) # POLLIN for recv, POLLOUT for send
    out_poller = zmq.Poller()
    out_poller.register(socket, zmq.POLLOUT) # POLLIN for recv, POLLOUT for send

    connected = False

    def __init__(self):
        print("Trying to connect to Server ...")
        while not self.connected:
            sent = False
            if not sent:
                if self.out_poller.poll(1000): # 10s timeout in milliseconds
                    self.socket.send_pyobj('?',zmq.NOBLOCK)
                    print('sent ?')
                    sent = True
                else:
                    sent = False

            received = False
            if sent:
                if self.in_poller.poll(1000):
                    msg = self.socket.recv_pyobj(flags=zmq.NOBLOCK)
                    print(msg)
                    if msg == '!':
                        received = True
                else:
                    received = False

            if sent and received:
                connected = True
                break
            elif not received :
                print("No connection to server, starting server")
                # p = subprocess.run(['python', 'spectrometer_server.py'])
                p = subprocess.Popen(['python', 'spectrometer_server.py'])
                # subprocess.call('python spectrometer_server.py', shell=True)
                # subprocess.call(['python', 'spectrometer_server.py'])
                #time.sleep(10)

        print('Connected to server')

    def __del__(self):
        self.socket.close()
        self.context.term()


    def make_request(self, req):
        sent = False
        received = False

        if self.out_poller.poll(1000):
            self.socket.send_pyobj(req)
            sent = True

        if self.in_poller.poll(1000):
            #msg = socket.recv()
            data = self.socket.recv_pyobj()
            received = True

        if sent and received:
            return data
        elif (not sent) and (not received):
            print("Server not answering, quitting")
            raise KeyboardInterrupt()


    def run(self):
            #while True:
            for i in range(10):
                data = self.make_request('Client to Server')
                print(data)
                time.sleep(0.5)

            data = self.make_request('singletrack')
            print(data)
            self.socket.send_pyobj('quit')
            time.sleep(2)



if __name__ == '__main__':
    client = SpectrometerClient()
    try:
        client.run()
    except KeyboardInterrupt:
        print("Exiting ...")
