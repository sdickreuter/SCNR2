import time
import numpy as np
import multiprocessing as mp
import ctypes

import AndorSpectrometer
from queueprocess import QueueProcess

init_spectrometer = True

class SpectrometerProcess(QueueProcess):
    spectrometer = None
    spec_shared = None
    detector_img_shared = None
    running = True

    def __init__(self, queue, spec_shared, detector_img_shared):
        super(SpectrometerProcess, self).__init__(queue)
        self.spec_shared = spec_shared
        self.detector_img_shared = detector_img_shared
        #self.spectrometer = spectrometer
        #min_width, max_width = self.spectrometer.CalcImageofSlitDim()
        #width = max_width - min_width
        #height = self.spectrometer._height
        #pixels = self.spectrometer._width
        #self.spec_shared = mp.Array(ctypes.c_int32, pixels)
        #self.detector_img_shared = mp.Array(ctypes.c_int32, width * height)
        #self.init()

    def init(self):
        if init_spectrometer:
            print('Initializing Spectrometer')
            time.sleep(0.5)
            try:
                self.spectrometer = AndorSpectrometer.Spectrometer(start_cooler=False, init_shutter=True, verbosity=1)
            except Exception as e:
                print(e)
                raise KeyboardInterrupt()
            time.sleep(1)
            print('Spectrometer initialized')
            min_width, max_width = self.spectrometer.CalcImageofSlitDim()
            self.width = max_width-min_width
            self.height = self.spectrometer._height
            self.spectrometer.SetExposureTime(0.33)
            self.spectrometer.SetSingleTrack()
        else:
            width = 300
            height = 256
            pixels = 2000


    def getspec(self):
        return self.spec_shared

    def saferun(self):
        self.init()
        while self.running:
            msg, param = self.queue.get()
            #print(msg + ' ' + str(param))

            if msg == '?':
                self.send_status('!')
            elif msg == 'shutdown':
                self.running = False
                self.send_status('ok')
                #raise KeyboardInterrupt()
                break

            elif msg == 'test':
                self.spec_shared[0] += param
                self.send_status('ok')

            elif msg == 'getwidth':
                self.send_status(self.spectrometer._width)

            elif msg == 'gettemperature':
                self.send_status(self.spectrometer.GetTemperature())

            elif msg == 'getslitwidth':
                self.send_status(self.spectrometer.GetSlitWidth())

            elif msg == 'getgratinginfo':
                self.send_status(self.spectrometer.GetGratingInfo())

            elif msg == 'getgrating':
                self.send_status(self.spectrometer.GetGrating())

            elif msg == 'setgrating':
                self.spectrometer.SetGrating(param)
                self.send_status('ok')

            elif msg == 'abortacquisition':
                self.spectrometer.AbortAcquisition()
                self.send_status('ok')

            elif msg == 'setnumberaccumulations':
                self.spectrometer.SetNumberAccumulations(param)
                self.send_status('ok')

            elif msg == 'setexposuretime':
                self.spectrometer.SetExposureTime(param)
                self.send_status('ok')

            elif msg == 'setslitwidth':
                self.spectrometer.SetSlitWidth(param)
                self.send_status('ok')

            elif msg == 'getwavelength':
                self.send_status(self.spectrometer.GetWavelength())

            elif msg == 'setfullimage':
                self.spectrometer.SetFullImage()
                self.send_status('ok')

            elif msg == 'takefullimage':
                print("takefullimage not supported at the moment")
                #self.send_status(self.spectrometer.TakeFullImage())

            elif msg == 'setcentrewavelength':
                self.spectrometer.SetCentreWavelength(param)
                self.send_status('ok')

            elif msg == 'setimageofslit':
                self.spectrometer.SetImageofSlit()
                self.send_status('ok')

            elif msg == 'takeimageofslit':
                data = self.spectrometer.TakeImageofSlit().ravel()
                self.detector_img_shared[:len(data)] = data
                self.send_status((self.width+1,self.height))

            elif msg == 'setsingletrack':
                hstart, hstop = param
                self.spectrometer.SetSingleTrack(hstart, hstop)
                self.send_status('ok')

            elif msg == 'takesingletrack':
                print('TakeSingleTrack:')
                #data = self.spectrometer.TakeSingleTrack()
                #print(data)
                data = self.spectrometer.TakeSingleTrack()
                print(data)
                self.spec_shared = data
                self.send_status('ok')

            else:
                self.send_status('?')



class SpectrometerController:

    def __init__(self, queue, spec_shared, detector_img_shared):
        self.spec_shared = spec_shared
        self.detector_img_shared = detector_img_shared
        self.queue = queue

    def make_request(self, req, param):
        self.queue.put((req,param))
        pid, status = self.queue.get()
        return status

    def test(self):
        return self.make_request('test',1)

    def Shutdown(self):
        return self.make_request('shutdown',0)

    def GetWidth(self):
        return self.make_request('getwidth', 0)

    def GetTemperature(self):
        return self.make_request('gettemperature',0)

    def GetSlitWidth(self):
        return self.make_request('getslitwidth',0)

    def GetGratingInfo(self):
        return self.make_request('getgratinginfo',0)

    def GetGrating(self):
        return self.make_request('getgrating',0)

    def SetGrating(self, grating):
        return self.make_request('setgrating',grating)

    def AbortAcquisition(self):
        return self.make_request('abortacquisition',0)

    def SetNumberAccumulations(self, number):
        return self.make_request('setnumberaccumulations',number)

    def SetExposureTime(self, seconds):
        return self.make_request('setexposuretime',seconds)

    def SetSlitWidth(self, slitwidth):
        return self.make_request('setslitwidth',slitwidth)

    def _GetWavelength(self):
        return self.make_request('getwavelength',0)

    def GetWavelength(self):
        return self.wl

    def SetFullImage(self):
        self.mode = 'Image'
        return self.make_request('setfullimage',0)

    def TakeFullImage(self):
        return self.make_request('takefullimage',0)

    def SetCentreWavelength(self, wavelength):
        ret = self.make_request('setcentrewavelength',wavelength)
        self.wl = self._GetWavelength()
        return ret

    def SetImageofSlit(self):
        self.mode = 'Image'
        return self.make_request('setimageofslit',0)

    def TakeImageofSlit(self):
        width, height = self.make_request('takeimageofslit',0)
        data = np.array(self.detector_img_shared[:(width*height)])
        return data.reshape(width,height)

    def SetSingleTrack(self, hstart=None, hstop=None):
        self.mode = 'SingleTrack'
        return self.make_request('setsingletrack',(hstart,hstop))

    def TakeSingleTrack(self):
        status = self.make_request('takesingletrack',0)
        return np.array(self.spec_shared)

