
import zmq
import numpy as np
import random
import sys
import time
import signal
import AndorSpectrometer

from serialsocket import SerializingContext

class SpectrometerServer:
    running = True

    def __init__(self):
        print("Initializing Spectrometer ...")
        #self.spectrometer = AndorSpectrometer.Spectrometer(start_cooler=True,init_shutter=True,verbosity=1)
        print("Spectrometer initialized !")

        #self.spectrometer.SetTemperature(-15)

        self.context = SerializingContext()
        self.socket = self.context.socket(zmq.PAIR)
        port = "6667"
        self.socket.bind("tcp://*:%s" % port)

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLOUT) # POLLIN for recv, POLLOUT for send

        print("You can now start the Graphical User Interface.")
        print("IMPORTANT:")
        print("After you have finished please close this program by pressing CTRL+C")


    def __del__(self):
        #self.spectrometer.Shutdown()
        self.socket.close()
        self.context.term()

    def send_array(self,A):
        if self.poller.poll(1000):
            self.socket.send_array(A,copy=False)
            #self.socket.send_zipped_pickle(A)
        else:
            print("lost connection to client")

    def send_object(self, data):
        if self.poller.poll(1000):
            self.socket.send_pyobj(data)
        else:
            print("lost connection to client")

    def run(self):
        while self.running:
            msg, param = self.socket.recv_pyobj()
            #print(msg +' '+ str(param))

            if msg == '?':
                self.send_object('!')
            elif msg == 'quit':
                print('Quiting by request of client')
                self.send_object('ok')
                self.running = False
                break
                #raise KeyboardInterrupt()

            elif msg == 'shutdown':
                self.send_object(self.spectrometer._width)

            elif msg == 'getwidth':
                self.send_object(self.spectrometer._width)

            elif msg == 'gettemperature':
                self.send_object(self.spectrometer.GetTemperature())

            elif msg == 'getslitwidth':
                self.send_object(self.spectrometer.GetSlitWidth())

            elif msg == 'getgratinginfo':
                self.send_object(self.spectrometer.GetGratingInfo())

            elif msg == 'getgrating':
                self.send_object(self.spectrometer.GetGrating())

            elif msg == 'setgrating':
                self.spectrometer.SetGrating(param)
                self.send_object('ok')

            elif msg == 'abortacquisition':
                self.spectrometer.AbortAcquisition()
                self.send_object('ok')

            elif msg == 'setnumberaccumulations':
                self.spectrometer.SetNumberAccumulations(param)
                self.send_object('ok')

            elif msg == 'setexposuretime':
                self.spectrometer.SetExposureTime(param)
                self.send_object('ok')

            elif msg == 'setslitwidth':
                self.spectrometer.SetSlitWidth(param)
                self.send_object('ok')

            elif msg == 'getwavelength':
                self.send_object(self.spectrometer.GetWavelength())

            elif msg == 'setfullimage':
                self.spectrometer.SetFullImage()
                self.send_object('ok')

            elif msg == 'takefullimage':
                self.send_array(self.spectrometer.TakeFullImage())

            elif msg == 'setcentrewavelength':
                self.spectrometer.SetCentreWavelength(param)
                self.send_object('ok')

            elif msg == 'setimageofslit':
                self.spectrometer.SetImageofSlit()
                self.send_object('ok')

            elif msg == 'takeimageofslit':
                self.send_array(self.spectrometer.TakeImageofSlit())

            elif msg == 'setsingletrack':
                hstart, hstop = param
                self.spectrometer.SetSingleTrack(hstart,hstop)
                self.send_object('ok')

            elif msg == 'takesingletrack':
                self.send_array(self.spectrometer.TakeSingleTrack())

            else:
                self.send_object('?')


if __name__ == '__main__':
    running = True

    def stop(*params):
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    server = SpectrometerServer()
    try:
        server.run()
    except KeyboardInterrupt:
        print("Exiting ...")
        print("IMPORTANT:")
        print("Please wait until the Spectrometer warmup is finished!")
