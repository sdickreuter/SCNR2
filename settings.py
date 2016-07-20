__author__ = 'sei'

import configparser
import os


class Settings(object):
    _filename = "config.ini"

    def __init__(self):
        self.config = configparser.ConfigParser()
        try:
            self.config.read(self._filename)

        except:
            print("Error loading settings.")
            RuntimeError("Error loading settings.")
            return

        self.integration_time = float(self.config['spectrum']['integration_time'])
        self.number_of_samples = int(self.config['spectrum']['number_of_samples'])

        self.direction_x = float(self.config['direction']['x'])
        self.direction_y = float(self.config['direction']['y'])
        self.direction_z = float(self.config['direction']['z'])
        self.amplitude = float(self.config['direction']['amplitude'])
        self.f = float(self.config['direction']['f'])

        self.stepsize = float(self.config['stage']['stepsize'])
        self.stage_ip = self.config['stage']['ip']
        self.stage_port = int(self.config['stage']['port'])

        self.sigma = float(self.config['searchmax']['sigma'])
        self.rasterdim = int(self.config['searchmax']['rasterdim'])
        self.rasterwidth = float(self.config['searchmax']['rasterwidth'])
        self.search_integration_time = float(self.config['searchmax']['integration_time'])

        self.cam_exposure_time = float(self.config['camera']['exposure_time'])

        self.slit_width = int(self.config['spectrometer']['slit_width'])

        self.cammarker_x = float(self.config['cammarker']['x'])
        self.cammarker_y = float(self.config['cammarker']['y'])

        self.slitmarker_x = float(self.config['slitmarker']['x'])
        self.slitmarker_y = float(self.config['slitmarker']['y'])


    def save(self):
        self.config.set('spectrum', 'integration_time', str(self.integration_time))
        self.config.set('spectrum', 'number_of_samples', str(self.number_of_samples))

        self.config.set('direction', 'x', str(self.direction_x))
        self.config.set('direction', 'y', str(self.direction_y))
        self.config.set('direction', 'z', str(self.direction_z))
        self.config.set('direction', 'amplitude', str(self.amplitude))
        self.config.set('direction', 'f', str(self.f))

        self.config.set('stage', 'stepsize', str(self.stepsize))

        self.config.set('searchmax', 'sigma', str(self.sigma))
        self.config.set('searchmax', 'rasterdim', str(self.rasterdim))
        self.config.set('searchmax', 'rasterwidth', str(self.rasterwidth))
        self.config.set('searchmax', 'integration_time', str(self.search_integration_time))

        self.config.set('camera', 'exposure_time', str(self.cam_exposure_time))

        self.config.set('spectrometer', 'slit_width', str(self.slit_width))

        self.config.set('cammarker', 'x', str(self.cammarker_x))
        self.config.set('cammarker', 'y', str(self.cammarker_y))

        self.config.set('slitmarker', 'x', str(self.slitmarker_x))
        self.config.set('slitmarker', 'y', str(self.slitmarker_y))

        try:
            with open(self._filename, 'w') as configfile:
                self.config.write(configfile)
        except:
            print("Error saving settings.")
            print(os.getcwd())
