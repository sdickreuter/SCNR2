
import zmq
import numpy as np
import random
import sys
import time

import AndorSpectrometer


class SpectrometerServer:

    def __init__(self):
        print("Initializing Spectrometer ...")
        self.spectrometer = AndorSpectrometer.Spectrometer(start_cooler=True,init_shutter=True,verbosity=1)
        print("Spectrometer initialized !")

        self.spectrometer.SetTemperature(-40)

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        port = "6667"
        self.socket.bind("tcp://*:%s" % port)

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLOUT) # POLLIN for recv, POLLOUT for send

    def __del__(self):
        self.spectrometer.Shutdown()
        self.socket.close()
        self.context.term()

    def send_data(self,data):
        if self.poller.poll(1000):
            #print('Sending: '+str(data))
            self.socket.send_pyobj(data)
        else:
            print("lost connection to client")

    def run(self):
        while True:

            msg, param = self.socket.recv_pyobj()
            print(msg +' '+ str(param))

            if msg == '?':
                self.send_data('!')
            elif msg == 'quit':
                print('Quiting by request of client')
                running = False
                break

            elif msg == 'getwidth':
                self.send_data(self.spectrometer._width)

            elif msg == 'gettemperature':
                self.send_data(self.spectrometer.GetTemperature())

            elif msg == 'getslitwidth':
                self.send_data(self.spectrometer.GetSlitWidth())

            elif msg == 'getgratinginfo':
                self.send_data(self.spectrometer.GetGratingInfo())

            elif msg == 'getgrating':
                self.send_data(self.spectrometer.GetGrating())

            elif msg == 'setgrating':
                self.spectrometer.SetGrating(param)
                self.send_data('ok')

            elif msg == 'abortacquisition':
                self.spectrometer.AbortAcquisition()
                self.send_data('ok')

            elif msg == 'setnumberaccumulations':
                self.spectrometer.SetNumberAccumulations(param)
                self.send_data('ok')

            elif msg == 'setexposuretime':
                self.spectrometer.SetExposureTime(param)
                self.send_data('ok')

            elif msg == 'setslitwidth':
                self.spectrometer.SetSlitWidth(param)
                self.send_data('ok')

            elif msg == 'getwavelength':
                self.send_data(self.spectrometer.GetWavelength())

            elif msg == 'setfullimage':
                self.spectrometer.SetFullImage()
                self.send_data('ok')

            elif msg == 'takefullimage':
                self.send_data(self.spectrometer.TakeFullImage())

            elif msg == 'setcentrewavelength':
                self.spectrometer.SetCentreWavelength(param)
                self.send_data('ok')

            elif msg == 'setimageofslit':
                self.spectrometer.SetImageofSlit()
                self.send_data('ok')

            elif msg == 'takeimageofslit':
                self.send_data(self.spectrometer.TakeImageofSlit())

            elif msg == 'setsingletrack':
                hstart, hstop = param
                self.spectrometer.SetSingleTrack(hstart,hstop)
                self.send_data('ok')

            elif msg == 'takesingletrack':
                self.send_data(self.spectrometer.TakeSingleTrack())

            else:
                self.send_data('?')



if __name__ == '__main__':
    server = SpectrometerServer()
    try:
        server.run()
    except KeyboardInterrupt:
        print("Exiting ...")