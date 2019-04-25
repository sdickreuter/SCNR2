
import zmq
import numpy as np
import random
import sys
import time
import signal
import AndorSpectrometer

class SpectrometerServer:
    running = True

    def __init__(self):
        print("Initializing Spectrometer ...")
        self.spectrometer = AndorSpectrometer.Spectrometer(start_cooler=True,init_shutter=True,verbosity=1)
        print("Spectrometer initialized !")

        self.spectrometer.SetTemperature(-40)
        #self.spectrometer.SetTemperature(-10)

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        port = "6667"
        self.socket.bind("tcp://*:%s" % port)

        self.out_poller = zmq.Poller()
        self.out_poller.register(self.socket, zmq.POLLOUT) # POLLIN for recv, POLLOUT for send

        self.in_poller = zmq.Poller()
        self.in_poller.register(self.socket, zmq.POLLIN) # POLLIN for recv, POLLOUT for send

        print("You can now start the Graphical User Interface.")
        print("IMPORTANT:")
        print("After you have finished please close this program \nand wait for detector warmup")


    def __del__(self):
        #self.spectrometer.Shutdown()
        self.socket.close()
        self.context.term()


    def send_object(self, data):
        #if self.poller.poll(1000):
        if self.out_poller.poll(1000):
            self.socket.send_pyobj(data)
        else:
            print("lost connection to client")

    def run(self):
        while self.running:
            if self.in_poller.poll(1000):
                msg, param = self.socket.recv_pyobj()
                print('Received Message: ' + msg +' '+ str(param))
            else:
                msg = '...'
                param = None

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

            elif msg == 'getgratingoffset':
                self.send_object(self.spectrometer.GetGratingOffset())

            elif msg == 'settemperature':
                self.send_object(self.spectrometer.SetTemperature(param))
                self.send_object('ok')

            elif msg == 'setgratingoffset':
                self.spectrometer.SetGratingOffset(param)
                self.send_object('ok')

            elif msg == 'getdetectoroffset':
                self.send_object(self.spectrometer.GetDetectorOffset())

            elif msg == 'setdetectoroffset':
                self.spectrometer.SetDetectorOffset(param)
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

            elif msg == 'setminvertreadout':
                self.spectrometer.SetSingleTrackMinimumVerticalPixels(param)
                self.send_object('ok')

            elif msg == 'getwavelength':
                self.send_object(self.spectrometer.GetWavelength())

            elif msg == 'setfullimage':
                self.spectrometer.SetFullImage()
                self.send_object('ok')

            elif msg == 'takefullimage':
                #self.send_array(self.spectrometer.TakeFullImage())
                self.send_object(self.spectrometer.TakeFullImage())

            elif msg == 'setcentrewavelength':
                self.spectrometer.SetCentreWavelength(param)
                self.send_object('ok')

            elif msg == 'setimageofslit':
                self.spectrometer.SetImageofSlit()
                self.send_object('ok')

            elif msg == 'takeimageofslit':
                #self.send_array(self.spectrometer.TakeImageofSlit())
                self.send_object(self.spectrometer.TakeImageofSlit())

            elif msg == 'setsingletrack':
                hstart, hstop = param
                self.spectrometer.SetSingleTrack(hstart,hstop)
                self.send_object('ok')

            elif msg == 'takesingletrack':
                #self.send_array(self.spectrometer.TakeSingleTrack())
                #self.send_object(self.spectrometer.TakeSingleTrack())
                self.send_object(self.spectrometer.TakeSingleTrack())
            elif msg == '...':
                pass
            else:
                self.send_object('?')


if __name__ == '__main__':
    running = True
    server = SpectrometerServer()

    def stop(_signo=None, _stack_frame=None):
        print('Got termination signal, shutting down ...')
        server.spectrometer.Shutdown()
        print('Shutdown complete.')
        time.sleep(1.0)
        #raise KeyboardInterrupt()
        sys.exit(0)

    signal.signal(signal.SIGHUP, stop)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    #signal.signal(signal.SIGABRT, stop)
    #signal.signal(signal.SIGKILL, stop)
    #signal.signal(signal.SIGSTOP, stop)
    #signal.signal(signal.SIGQUIT, stop)
    #signal.signal(signal.SIGSEGV, stop)

    #import atexit
    #atexit.register(stop)

    # try:
    server.run()
    # except KeyboardInterrupt:
    #     print("Exiting ...")
    #     print("IMPORTANT:")
    #     print("Please wait until the Spectrometer warmup is finished!")
    server = None
