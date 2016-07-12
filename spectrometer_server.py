
import zmq
import numpy as np
import random
import sys
import time

import AndorSpectrometer


print("Initializing Spectrometer ...")
spectrometer = AndorSpectrometer.Spectrometer(start_cooler=False,init_shutter=True,verbosity=1)
print("Spectrometer initialized !")

context = zmq.Context()
socket = context.socket(zmq.PAIR)
port = "6667"
socket.bind("tcp://*:%s" % port)

poller = zmq.Poller()
poller.register(socket, zmq.POLLOUT) # POLLIN for recv, POLLOUT for send

data = np.ones(10)

def send_data(data):
    if poller.poll(1000):
        #print('Sending: '+str(data))
        socket.send_pyobj(data)
    else:
        print("lost connection to client")

msg = None

try:

    while True:

        msg, param = socket.recv_pyobj()
        print(msg +' '+ str(param))

        if msg == '?':
            send_data('!')
        elif msg == 'quit':
            print('Quiting by request of client')
            running = False
            break

        elif msg == 'getwidth':
            send_data(spectrometer._width)

        elif msg == 'gettemperature':
            send_data(spectrometer.GetTemperature())

        elif msg == 'getslitwidth':
            send_data(spectrometer.GetSlitWidth())

        elif msg == 'getgratinginfo':
            send_data(spectrometer.GetGratingInfo())

        elif msg == 'getgrating':
            send_data(spectrometer.GetGrating())

        elif msg == 'setgrating':
            spectrometer.SetGrating(param)
            send_data('ok')

        elif msg == 'abortacquisition':
            spectrometer.AbortAcquisition()
            send_data('ok')

        elif msg == 'setnumberaccumulations':
            spectrometer.SetNumberAccumulations(param)
            send_data('ok')

        elif msg == 'setexposuretime':
            spectrometer.SetExposureTime(param)
            send_data('ok')

        elif msg == 'setslitwidth':
            spectrometer.SetSlitWidth(param)
            send_data('ok')

        elif msg == 'getwavelength':
            send_data(spectrometer.GetWavelength())

        elif msg == 'setfullimage':
            spectrometer.SetFullImage()
            send_data('ok')

        elif msg == 'takefullimage':
            send_data(spectrometer.TakeFullImage())

        elif msg == 'setcentrewavelength':
            spectrometer.SetCentreWavelength(param)
            send_data('ok')

        elif msg == 'setimageofslit':
            spectrometer.SetImageofSlit()
            send_data('ok')

        elif msg == 'takeimageofslit':
            send_data(spectrometer.TakeImageofSlit())

        elif msg == 'setsingletrack':
            hstart, hstop = param
            spectrometer.SetSingleTrack(hstart,hstop)
            send_data('ok')

        elif msg == 'takesingletrack':
            send_data(spectrometer.TakeSingleTrack())

        else:
            send_data('?')

except KeyboardInterrupt:
    print("Exiting ...")
finally:
    spectrometer.Shutdown()
    socket.close()
    context.term()