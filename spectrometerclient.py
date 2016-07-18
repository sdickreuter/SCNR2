import zmq
import time

from serialsocket import SerializingContext

class SpectrometerClient:

    context = SerializingContext()
    socket = context.socket(zmq.PAIR)
    port = "6667"
    socket.connect("tcp://localhost:%s" % port)

    in_poller = zmq.Poller()
    in_poller.register(socket, zmq.POLLIN) # POLLIN for recv, POLLOUT for send
    out_poller = zmq.Poller()
    out_poller.register(socket, zmq.POLLOUT) # POLLIN for recv, POLLOUT for send

    connected = False


    def __init__(self, queue):
        self.queue = queue

        self.queue.put(('?',None))
        print(self.queue.get())

        #self._width = self.GetWidth()
        self.mode = None
        #self.wl = self._GetWavelength()
        print('Connected to server')

    def __del__(self):
        self.socket.close()
        self.context.term()


    def make_request(self, req, param):
        self.queue.put((req,param))
        return self.queue.get()

    def run(self):
            #while True:
            for i in range(5):
                data = self.make_request('Client to Server',None)
                print(data)
                time.sleep(0.5)

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

    def test(self):
        return self.make_request('?', None)

    def Shutdown(self):
        return self.make_request('shutdown', None)

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
