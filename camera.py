import ximea as xi


class Camera:

    def __init__(self):

        # xi.handle_xi_error(1)
        print(xi.get_device_count())
        print(xi.get_device_info(0, 'device_name'))

        self._cam = xi.Xi_Camera(DevID=0)
        self._cam.set_debug_level("Warning")
        self._cam.set_param('exposure', 10000.0)
        self._cam.set_param('aeag', 1)
        self._cam.set_param('exp_priority', 0)
        # cam.set_param('shutter_type',0)
        #self.cam.set_binning(4)
        #self.cam.set_param('width', 400)
        #self.cam.set_param('height', 300)
        #self.cam.set_param('offsetX', 50)
        #self.cam.set_param('offsetY', 50)
        #print(self.cam.get_param('framerate', float))

    def __del__(self):
        self._cam.close()

    def getimage(self):
        return self._cam.get_image()

    def setexposure(self,us):
        self._cam.set_param('exposure', us)
