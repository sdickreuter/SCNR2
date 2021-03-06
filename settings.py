__author__ = 'sei'

import configparser
import os


class Settings(object):
    _filename = "config.ini"

    def __init__(self, filename = None):
        self.config = configparser.ConfigParser()

        if filename is not None:
            try:
                self.config.read(filename)
                self._filename = filename
            except:
                print("Error loading settings.")
                RuntimeError("Error loading settings.")
                return
        else:
            try:
                self.config.read(self._filename)

            except:
                print("Error loading settings.")
                RuntimeError("Error loading settings.")
                return

        self.correct_search = False

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
        self.coord_mapping = self.str2coordmapping(self.config['stage']['coord_mapping'])

        self.sigma = float(self.config['searchmax']['sigma'])
        self.rasterdim = int(self.config['searchmax']['rasterdim'])
        self.rasterwidth = float(self.config['searchmax']['rasterwidth'])
        self.search_integration_time = float(self.config['searchmax']['integration_time'])
        self.zmult = int(self.config['searchmax']['zmult'])

        self.cam_exposure_time = float(self.config['camera']['exposure_time'])

        self.slit_width = int(self.config['spectrometer']['slit_width'])
        self.centre_wavelength = int(self.config['spectrometer']['centre_wavelength'])


        self.cammarker_x = float(self.config['cammarker']['x'])
        self.cammarker_y = float(self.config['cammarker']['y'])

        self.slitmarker_x = float(self.config['slitmarker']['x'])
        self.slitmarker_y = float(self.config['slitmarker']['y'])

        self.min_ind_img = int(self.config['autofocus']['min_ind_img'])
        self.max_ind_img = int(self.config['autofocus']['max_ind_img'])
        self.autofocus_mode = self.config['autofocus']['mode']
        self.zscan_centre = int(self.config['autofocus']['zscan_centre'])
        self.zscan_width = int(self.config['autofocus']['zscan_width'])

        # settings not saved to file:
        self.minvertreadout = 0



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
        self.config.set('searchmax', 'zmult', str(self.zmult))

        self.config.set('camera', 'exposure_time', str(self.cam_exposure_time))

        self.config.set('spectrometer', 'slit_width', str(self.slit_width))
        self.config.set('spectrometer', 'centre_wavelength', str(self.centre_wavelength))


        self.config.set('cammarker', 'x', str(self.cammarker_x))
        self.config.set('cammarker', 'y', str(self.cammarker_y))

        self.config.set('slitmarker', 'x', str(self.slitmarker_x))
        self.config.set('slitmarker', 'y', str(self.slitmarker_y))

        self.config.set('autofocus', 'min_ind_img', str(self.min_ind_img))
        self.config.set('autofocus', 'max_ind_img', str(self.max_ind_img))

        self.config.set('autofocus','mode',self.autofocus_mode)
        self.config.set('autofocus','zscan_centre',str(self.zscan_centre))
        self.config.set('autofocus','zscan_width',str(self.zscan_width))




        try:
            with open(self._filename, 'w') as configfile:
                self.config.write(configfile)
        except:
            print("Error saving settings.")
            print(os.getcwd())

    def str2coordmapping(self, str):
        return {str[0]: str[1], str[2]: str[3], str[4]: str[5]}