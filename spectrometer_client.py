import zmq
import numpy as np
import random
import sys
import time

import subprocess
import os

from matplotlib import pyplot as plt

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
        count = 0
        while not self.connected:
            sent = False
            if not sent:
                if self.out_poller.poll(1000): # 1s timeout in milliseconds
                    self.socket.send_pyobj(('?',None))#,zmq.NOBLOCK)
                    print('sent ?')
                    sent = True
                else:
                    sent = False

            received = False
            if sent:
                if self.in_poller.poll(1000):
                    msg = self.socket.recv_pyobj()#flags=zmq.NOBLOCK)
                    #print(msg)
                    if msg == '!':
                        received = True
                else:
                    received = False

            if sent and received:
                connected = True
                break
            elif not received :
                count += 1
                if count < 10:
                    print('Connecting failed trying again')
                else:
                    print('Too many tries, exciting ...')
                    raise KeyboardInterrupt()

        print('Connected to server')

        self._width = self.GetWidth()
        self.mode = None
        time.sleep(0.2)
        self.wl = self._GetWavelength()
        self.exposure_time = 0.1

    def __del__(self):
        self.socket.close()
        self.context.term()


    def make_request(self, req, param):
        sent = False
        received = False

        if self.out_poller.poll(1000):
            self.socket.send_pyobj((req,param))
            sent = True

        if self.in_poller.poll(320*1000):
            data = self.socket.recv_pyobj()
            received = True

        if sent and received:
            return data
        elif (not sent) and (not received):
            print("Server not answering, quitting")
            self.lock.release()
            raise KeyboardInterrupt()

    def _return_value_is_ok(self, ret):
        if type(ret) is str:
            if not ret == 'ok':
                print('Communication Error')
                print(ret)
                return False
        else:
            print('Communication out of sync, please retry')
            print(ret)
            return False
        return True

    def _return_value_is_data(self, ret):
        if type(ret) is not np.ndarray:
            print('Communication out of sync, please retry')
            print(ret)
            return False
        return True

    def run(self):
            #while True:
            # for i in range(5):
            #     data = self.make_request('Client to Server',None)
            #     print(data)
            #     time.sleep(0.5)

            self.SetExposureTime(0.1)
            self.SetCentreWavelength(0)
            self.SetSlitWidth(2500)
            self.SetImageofSlit()
            start = time.time()
            data = self.TakeImageofSlit()
            print(time.time()-start)
            print(data)
            #self.socket.send_pyobj(('quit',None))
            #time.sleep(2)

    def Shutdown(self):
        #print("Send Request: shutdown")
        return self.make_request('shutdown', None)

    def GetWidth(self):
        #print("Send Request: getwidth")
        return self.make_request('getwidth', None)

    def GetTemperature(self):
        #print("Send Request: gettemperature")
        return self.make_request('gettemperature',None)

    def GetSlitWidth(self):
        #print("Send Request: getslitwidth")
        return self.make_request('getslitwidth',None)

    def GetGratingInfo(self):
        #print("Send Request: getgratinginfo")
        return self.make_request('getgratinginfo',None)

    def GetGrating(self):
        #print("Send Request: getgrating")
        return self.make_request('getgrating',None)

    def SetGrating(self, grating):
        #print("Send Request: setgrating")
        ret = self.make_request('setgrating',grating)
        self._return_value_is_ok(ret)

    def GetGratingOffset(self):
        # print("Send Request: getgrating")
        return self.make_request('getgratingoffset', None)

    def SetGratingOffset(self, offset):
        # print("Send Request: setgrating")
        ret = self.make_request('setgratingoffset', offset)
        self._return_value_is_ok(ret)

    def GetDetectorOffset(self):
        # print("Send Request: getgrating")
        return self.make_request('getdetectoroffset', None)

    def SetDetectorOffset(self, offset):
        # print("Send Request: setgrating")
        ret = self.make_request('setdetectoroffset', offset)
        self._return_value_is_ok(ret)

    def AbortAcquisition(self):
        #print("Send Request: abortacquisition")
        ret = self.make_request('abortacquisition',None)
        self._return_value_is_ok(ret)

    def SetNumberAccumulations(self, number):
        #print("Send Request: setnumberaccumulations")
        ret = self.make_request('setnumberaccumulations',number)
        self._return_value_is_ok(ret)

    def SetExposureTime(self, seconds):
        self.exposure_time = seconds
        #print("Send Request: setexposuretime")
        ret = self.make_request('setexposuretime',seconds)
        self._return_value_is_ok(ret)

    def SetSlitWidth(self, slitwidth):
        #print("Send Request: setslitwidth")
        ret = self.make_request('setslitwidth',slitwidth)
        self._return_value_is_ok(ret)

    def SetMinVertReadout(self, pixels):
        ret = self.make_request('setminvertreadout', pixels)
        self._return_value_is_ok(ret)

    def SetTemperature(self, temp):
        ret = self.make_request('settemperature', temp)
        self._return_value_is_ok(ret)

    def _GetWavelength(self):
        #print("Send Request: getwavelength")
        ret = self.make_request('getwavelength',None)
        if self._return_value_is_data(ret):
            return ret
        else:
            return None

    def GetWavelength(self):
        return self.wl

    def SetCentreWavelength(self, wavelength):
        #print("Send Request: setcentrewavelength")
        ret = self.make_request('setcentrewavelength',wavelength)
        wl = self._GetWavelength()
        if wl is not None:
            self.wl = wl
        else:
            raise RuntimeError("Communication out of Sync, cannot get wavelength. Quitting ...")
        self._return_value_is_ok(ret)

    def SetImageofSlit(self):
        #print("Send Request: setimageofslit")
        self.mode = 'imageofslit'
        ret = self.make_request('setimageofslit',None)
        self._return_value_is_ok(ret)

    def TakeImageofSlit(self):
        #print("Send Request: takeimageofslit")
        ret = self.make_request('takeimageofslit',None)
        if self._return_value_is_data(ret):
            return ret
        else:
            return None

    def SetFullImage(self):
        #print("Send Request: setimageofslit")
        self.mode = 'fullimage'
        ret = self.make_request('setfullimage',None)
        self._return_value_is_ok(ret)

    def TakeFullImage(self):
        # print("Send Request: takeimageofslit")
        ret = self.make_request('takefullimage', None)
        if self._return_value_is_data(ret):
            return ret
        else:
            return None

    def SetSingleTrack(self, hstart=None, hstop=None):
        #print("Send Request: setsingletrack")
        self.mode = 'singletrack'
        ret = self.make_request('setsingletrack',(hstart,hstop))
        self._return_value_is_ok(ret)

    def TakeSingleTrack(self, raw = False):
        #print("Send Request: takesingletrack")
        #return np.mean(self.make_request('takesingletrack',None),axis=1)
        spec = self.make_request('takesingletrack',None)
        # for debuggin purposes
        # f = plt.figure()
        # for i in range(spec.shape[1]):
        #     plt.plot(spec[:,i])
        #
        # plt.savefig('singletrack.png')
        # plt.close()
        if self._return_value_is_data(spec):
            spec = np.flipud(spec)  # After changing Calibration with Andor Solis, data is now flipped, has to be flipped back
            if raw:
                return spec
            else:
                return np.mean(spec, axis=1)
        else:
            return None
        #return np.mean(spec[:, 1:(spec.shape[1] - 1)], axis=1)
        #return spec[:,1]

if __name__ == '__main__':
    client = SpectrometerClient()
    try:
        client.run()
    except KeyboardInterrupt:
        print("Exiting ...")
