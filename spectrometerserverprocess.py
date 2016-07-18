
import zmq
import time
import multiprocessing as mp
from serialsocket import SerializingContext

import AndorSpectrometer

class SpectrometerServerProcess(mp.Process):
    spectrometer = None
    running = True
    socket = None
    context = None

    def __init__(self):
        #super(SpectrometerServerProcess, self).__init__()
        mp.Process.__init__(self)
        #self.init()

    def init(self):
        #self.spectrometer.SetTemperature(-10)
        self.context = SerializingContext()
        self.socket = self.context.socket(zmq.PAIR)
        port = "6667"
        #self.socket.bind("tcp://localhost:%s" % port)
        self.socket.bind("tcp://*:%s" % port)

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLOUT) # POLLIN for recv, POLLOUT for send

        print('Initializing Spectrometer')
        time.sleep(0.5)
        try:
            pass
            #self.spectrometer = AndorSpectrometer.Spectrometer(start_cooler=False, init_shutter=True, verbosity=1)
        except Exception as e:
            print(e)
            raise RuntimeError()
        time.sleep(1)
        print('Spectrometer initialized')


    #def __del__(self):
    #    self.spectrometer.Shutdown()
    #    self.socket.close()
    #    self.context.term()

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
        self.init()

        while self.running:
                msg, param = self.socket.recv_pyobj()
                print(msg +' '+ str(param))

                if msg == '?':
                    self.send_object('!')

                elif msg == 'shutdown':
                    self.send_object('ok')
                    self.running = False
                    break

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

        return
