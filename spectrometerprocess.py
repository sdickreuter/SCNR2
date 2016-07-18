import time
import multiprocessing as mp
import ctypes

import AndorSpectrometer
from statusprocess import StatusProcess

init_spectrometer = False

class SpectrometerProcess(StatusProcess):
    spectrometer = None

    def __init__(self, status_queue, command_queue):
        super(SpectrometerProcess, self).__init__(status_queue,command_queue)
        if init_spectrometer:
            print('Initializing Spectrometer')
            time.sleep(0.5)
            self.spectrometer = AndorSpectrometer.Spectrometer(start_cooler=False, init_shutter=True, verbosity=1)
            time.sleep(1)
            print('Spectrometer initialized')
            min_width, max_width = self.spectrometer.CalcImageofSlitDim()
            width = max_width-min_width
            height = self.spectrometer._height
            pixels = self.spectrometer._width
            self.spectrometer.SetExposureTime(0.33)
        else:
            width = 300
            height = 256
            pixels = 2000

        self.spec_shared = mp.Array(ctypes.c_int32, pixels)
        self.detector_img_shared = mp.Array(ctypes.c_int32, width * height)

    def saferun(self):
        while True:
            msg, param = self.command_queue.get()
            print(msg + ' ' + str(param))

            if msg == '?':
                self.send_status('!')
            elif msg == 'quit':
                print('Quiting by request of client')
                # self.running = False
                raise KeyboardInterrupt()

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
                self.detector_img_shared = self.spectrometer.TakeImageofSlit()
                self.send_status('ok')

            elif msg == 'setsingletrack':
                hstart, hstop = param
                self.spectrometer.SetSingleTrack(hstart, hstop)
                self.send_status('ok')

            elif msg == 'takesingletrack':
                self.spec_shared = self.spectrometer.TakeSingleTrack()
                self.send_status('ok')

            else:
                self.send_status('?')



class SpectrometerController:

    def __init__(self, status_queue, command_queue):
        self.status = status_queue
        self.com = command_queue

    def make_request(self, req, param):
        self.com.put((req,param))
        pid, status = self.status.get()
        return status

    def test(self):
        return self.make_request('test',1)

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


