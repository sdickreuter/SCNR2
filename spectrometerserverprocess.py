
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

    def __init__(self, queue):
        #super(SpectrometerServerProcess, self).__init__()
        mp.Process.__init__(self)
        self.queue = queue
        #self.init()

    def init(self):
        print('Initializing Spectrometer')
        time.sleep(0.5)
        try:
            #pass
            self.spectrometer = AndorSpectrometer.Spectrometer(start_cooler=False, init_shutter=True, verbosity=1)
        except Exception as e:
            print(e)
            raise RuntimeError()
        time.sleep(1)
        print('Spectrometer initialized')
        # self.spectrometer.SetTemperature(-10)


    #def __del__(self):
    #    self.spectrometer.Shutdown()
    #    self.socket.close()
    #    self.context.term()



    def run(self):
        self.init()

        while self.running:
                msg, param = self.queue.get()
                #print(msg +' '+ str(param))

                if msg == '?':
                    self.queue.put('!')

                elif msg == 'shutdown':
                    self.queue.put('ok')
                    self.running = False
                    break

                elif msg == 'getwidth':
                    self.queue.put(self.spectrometer._width)

                elif msg == 'gettemperature':
                    self.queue.put(self.spectrometer.GetTemperature())

                elif msg == 'getslitwidth':
                    self.queue.put(self.spectrometer.GetSlitWidth())

                elif msg == 'getgratinginfo':
                    self.queue.put(self.spectrometer.GetGratingInfo())

                elif msg == 'getgrating':
                    self.queue.put(self.spectrometer.GetGrating())

                elif msg == 'setgrating':
                    self.spectrometer.SetGrating(param)
                    self.queue.put('ok')

                elif msg == 'abortacquisition':
                    self.spectrometer.AbortAcquisition()
                    self.queue.put('ok')

                elif msg == 'setnumberaccumulations':
                    self.spectrometer.SetNumberAccumulations(param)
                    self.queue.put('ok')

                elif msg == 'setexposuretime':
                    self.spectrometer.SetExposureTime(param)
                    self.queue.put('ok')

                elif msg == 'setslitwidth':
                    self.spectrometer.SetSlitWidth(param)
                    self.queue.put('ok')

                elif msg == 'getwavelength':
                    self.queue.put(self.spectrometer.GetWavelength())

                elif msg == 'setfullimage':
                    self.spectrometer.SetFullImage()
                    self.queue.put('ok')

                elif msg == 'takefullimage':
                    self.queue.put(self.spectrometer.TakeFullImage())

                elif msg == 'setcentrewavelength':
                    self.spectrometer.SetCentreWavelength(param)
                    self.queue.put('ok')

                elif msg == 'setimageofslit':
                    self.spectrometer.SetImageofSlit()
                    self.queue.put('ok')

                elif msg == 'takeimageofslit':
                    self.queue.put(self.spectrometer.TakeImageofSlit())

                elif msg == 'setsingletrack':
                    hstart, hstop = param
                    self.spectrometer.SetSingleTrack(hstart,hstop)
                    self.queue.put('ok')

                elif msg == 'takesingletrack':
                    self.queue.put(self.spectrometer.TakeSingleTrack())

                else:
                    self.queue.put('?')

        return
