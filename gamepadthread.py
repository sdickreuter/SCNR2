import sys

from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, QObject
import os, struct, array
from fcntl import ioctl

# These constants were borrowed from linux/input.h
axis_names = {
    0x00: 'x',
    0x01: 'y',
    0x02: 'z',
    0x03: 'rx',
    0x04: 'ry',
    0x05: 'rz',
    0x06: 'trottle',
    0x07: 'rudder',
    0x08: 'wheel',
    0x09: 'gas',
    0x0a: 'brake',
    0x10: 'hat0x',
    0x11: 'hat0y',
    0x12: 'hat1x',
    0x13: 'hat1y',
    0x14: 'hat2x',
    0x15: 'hat2y',
    0x16: 'hat3x',
    0x17: 'hat3y',
    0x18: 'pressure',
    0x19: 'distance',
    0x1a: 'tilt_x',
    0x1b: 'tilt_y',
    0x1c: 'tool_width',
    0x20: 'volume',
    0x28: 'misc',
}

button_names = {
    0x120: 'X',
    0x121: 'A',
    0x122: 'B',
    0x123: 'Y',
    0x124: 'LB',
    0x125: 'RB',
    0x126: 'LT',
    0x127: 'RT',
    0x128: 'BACK',
    0x129: 'START',
    0x12a: 'base5',
    0x12b: 'base6',
    0x12f: 'dead',
    0x130: 'a',
    0x131: 'b',
    0x132: 'c',
    0x133: 'x',
    0x134: 'y',
    0x135: 'z',
    0x136: 'tl',
    0x137: 'tr',
    0x138: 'tl2',
    0x139: 'tr2',
    0x13a: 'select',
    0x13b: 'start',
    0x13c: 'mode',
    0x13d: 'thumbl',
    0x13e: 'thumbr',

    0x220: 'dpad_up',
    0x221: 'dpad_down',
    0x222: 'dpad_left',
    0x223: 'dpad_right',

    # XBox 360 controller uses these codes.
    0x2c0: 'dpad_left',
    0x2c1: 'dpad_right',
    0x2c2: 'dpad_up',
    0x2c3: 'dpad_down',
}

class GamepadThread(QObject):
    ASignal = pyqtSignal()
    BSignal = pyqtSignal()
    XSignal = pyqtSignal()
    YSignal = pyqtSignal()
    xaxisSignal = pyqtSignal(float)
    yaxisSignal = pyqtSignal(float)

    axis_map = []
    button_map = []

    axis_states = {}
    button_states = {}

    def __init__(self, parent=None):
        if getattr(self.__class__, '_has_instance', False):
            RuntimeError('Cannot create another instance')
        self.__class__._has_instance = True
        self.isinitialized = False
        super(GamepadThread, self).__init__(parent)
        try:
            self._initialize()
            self.isinitialized = True
        except:
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)

        if self.isinitialized:
            self.abort = False
            self.thread = QThread()
            self.thread.started.connect(self.process)
            self.thread.finished.connect(self.stop)
            self.moveToThread(self.thread)

    def _initialize(self):
        # Open the joystick device.
        fn = '/dev/input/js0'
        print('Opening %s...' % fn)
        self.jsdev = open(fn, 'rb')

        # Get the device name.
        # buf = bytearray(63)
        buf = array.array('b', [0] * 64)
        ioctl(self.jsdev, 0x80006a13 + (0x10000 * len(buf)), buf)  # JSIOCGNAME(len)
        buf = bytes(buf)
        js_name = buf.decode()
        js_name = js_name.strip(b'\x00'.decode())
        print('Device name: %s initialized' % js_name)

        # Get number of axes and buttons.
        buf = array.array('B', [0])
        ioctl(self.jsdev, 0x80016a11, buf)  # JSIOCGAXES
        self.num_axes = buf[0]

        buf = array.array('B', [0])
        ioctl(self.jsdev, 0x80016a12, buf)  # JSIOCGBUTTONS
        self.num_buttons = buf[0]

        # Get the axis map.
        buf = array.array('B', [0] * 0x40)
        ioctl(self.jsdev, 0x80406a32, buf)  # JSIOCGAXMAP

        for axis in buf[:self.num_axes]:
            axis_name = axis_names.get(axis, 'unknown(0x%02x)' % axis)
            self.axis_map.append(axis_name)
            self.axis_states[axis_name] = 0.0

        # Get the button map.
        buf = array.array('H', [0] * 200)
        ioctl(self.jsdev, 0x80406a34, buf)  # JSIOCGBTNMAP

        for btn in buf[:self.num_buttons]:
            btn_name = button_names.get(btn, 'unknown(0x%03x)' % btn)
            self.button_map.append(btn_name)
            self.button_states[btn_name] = 0


    def start(self):
        self.thread.start(QThread.HighPriority)

    @pyqtSlot()
    def stop(self):
        self.abort = True

    def work(self):
        evbuf = self.jsdev.read(8)
        if evbuf:
            time, value, type, number = struct.unpack('IhBB', evbuf)

            if not type & 0x80:
                if type & 0x01:
                    button = self.button_map[number]
                    if button:
                        self.button_states[button] = value
                        if value == 0:
                            if button is 'A':
                                self.ASignal.emit()
                            if button is 'B':
                                self.BSignal.emit()
                            if button is 'X':
                                self.XSignal.emit()
                            if button is 'Y':
                                self.YSignal.emit()

                if type & 0x02:
                    axis = self.axis_map[number]
                    if axis:
                        self.axis_states[axis] = value
                        fvalue = value / 32767.0
                        if axis is 'x':
                            self.xaxisSignal.emit(fvalue)
                        if axis is 'y':
                            self.yaxisSignal.emit(fvalue)

    @pyqtSlot()
    def process(self):
        while not self.abort:
            try:
                self.work()
            except:
                (type, value, traceback) = sys.exc_info()
                sys.excepthook(type, value, traceback)

    def __del__(self):
        self.__class__.has_instance = False
        try:
            self.ASignal.disconnect()
            self.BSignal.disconnect()
            self.XSignal.disconnect()
            self.YSignal.disconnect()
        except TypeError:
            pass
        self.abort = True

# TODO: Test doesn't work, albeit Gamepadthread works in actual application
# Unit test code
if __name__ == '__main__':

    class Test(QObject):

        def __init__(self,parent=None):
            super(Test, self).__init__(parent)
            self.pad = GamepadThread()
            self.pad.ASignal.connect(self.on_A)
            self.pad.XSignal.connect(self.on_B)
            self.pad.YSignal.connect(self.on_Y)
            self.pad.XSignal.connect(self.on_X)
            self.pad.xaxisSignal.connect(self.on_x)
            self.pad.yaxisSignal.connect(self.on_y)
            #self.pad.start()

        @pyqtSlot()
        def on_A(self):
            print("A was released")

        @pyqtSlot()
        def on_B(self):
            print("B was released")

        @pyqtSlot()
        def on_X(self):
            print("X was released")

        @pyqtSlot()
        def on_Y(self):
            print("Y was released")
            self.pad.stop()

        @pyqtSlot(float)
        def on_x(self, x):
            print(x)

        @pyqtSlot(float)
        def on_y(self, y):
            print(y)

    t = Test()
    t.pad.start()

    while not t.pad.abort:
        pass

    sys.exit(1)

