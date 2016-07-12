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
        waiting = False
        while not self.connected:
            sent = False
            if not sent:
                if self.out_poller.poll(1000): # 10s timeout in milliseconds
                    self.socket.send_pyobj(('?',None))#,zmq.NOBLOCK)
                    print('sent ?')
                    sent = True
                else:
                    sent = False

            received = False
            if sent:
                if self.in_poller.poll(1000):
                    msg = self.socket.recv_pyobj()#flags=zmq.NOBLOCK)
                    print(msg)
                    if msg == '!':
                        received = True
                else:
                    received = False

            if sent and received:
                connected = True
                break
            elif waiting:
                print('Waiting for spectrometer to initialize ...')
                time.sleep(2)
            elif not received :
                waiting = True
                print("No connection to server, starting server")
                # p = subprocess.run(['python', 'spectrometer_server.py'])
                p = subprocess.Popen(['python', 'spectrometer_server.py'])
                # subprocess.call('python spectrometer_server.py', shell=True)
                # subprocess.call(['python', 'spectrometer_server.py'])


        self._width = self.GetWidth()
        self.mode = None
        self.wl = self._GetWavelength()
        print('Connected to server')

    def __del__(self):
        self.socket.close()
        self.context.term()


    def make_request(self, req, param):
        sent = False
        received = False

        if self.out_poller.poll(1000):
            self.socket.send_pyobj((req,param))
            sent = True

        if self.in_poller.poll(60*1000):
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
            for i in range(30):
                data = self.make_request('Client to Server',None)
                print(data)
                time.sleep(0.5)

            #data = self.make_request('singletrack',1)
            #print(data)
            self.socket.send_pyobj(('quit',None))
            time.sleep(2)

    def GetWidth(self):
        return self.make_request('getwidth', None)

    def GetTemperature(self):
        return self.make_request('gettemperature',None)

    def GetSlitWidth(self):
        return self.make_request('getslitwidth',None)

    def GetGratingInfo(self):
        return self.make_request('getgratinginfo',None)

    def GetGrating(self):
        return self.make_request('getgrating',None)

    def SetGrating(self, grating):
        ret = self.make_request('setgrating',grating)
        if not ret == 'ok':
            print('Communication Error')

    def AbortAcquisition(self):
        ret = self.make_request('abortacquisition',None)
        if not ret == 'ok':
            print('Communication Error')

    def SetNumberAccumulations(self, number):
        ret = self.make_request('setnumberaccumulations',number)
        if not ret == 'ok':
            print('Communication Error')

    def SetExposureTime(self, seconds):
        ret = self.make_request('setexposuretime',seconds)
        if not ret == 'ok':
            print('Communication Error')

    def SetSlitWidth(self, slitwidth):
        ret = self.make_request('setslitwidth',slitwidth)
        if not ret == 'ok':
            print('Communication Error')

    def _GetWavelength(self):
        return self.make_request('getwavelength',None)

    def GetWavelength(self):
        return self.wl

    def SetFullImage(self):
        self.mode = 'Image'
        ret = self.make_request('setfullimage',None)
        if not ret == 'ok':
            print('Communication Error')

    def TakeFullImage(self):
        return self.make_request('takefullimage',None)

    def SetCentreWavelength(self, wavelength):
        ret = self.make_request('setcentrewavelength',wavelength)
        self.wl = self._GetWavelength()
        if not ret == 'ok':
            print('Communication Error')

    def SetImageofSlit(self):
        self.mode = 'Image'
        ret = self.make_request('setimageofslit',None)
        if not ret == 'ok':
            print('Communication Error')

    def TakeImageofSlit(self):
        return self.make_request('takeimageofslit',None)


    def SetSingleTrack(self, hstart=None, hstop=None):
        self.mode = 'SingleTrack'
        ret = self.make_request('setsingletrack',(hstart,hstop))
        if not ret == 'ok':
            print('Communication Error')

    def TakeSingleTrack(self):
        return self.make_request('takesingletrack',None)

if __name__ == '__main__':
    client = SpectrometerClient()
    try:
        client.run()
    except KeyboardInterrupt:
        print("Exiting ...")
