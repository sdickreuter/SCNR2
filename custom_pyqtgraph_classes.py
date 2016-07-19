import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)

    ## reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            self.autoRange()

    def mouseDragEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            ev.ignore()
        else:
            pg.ViewBox.mouseDragEvent(self, ev)


class CustomCrosshairROI(pg.CrosshairROI):

     def __init__(self, pos=None, size=None, **kargs):
         pg.ROI.__init__(self, pos, size, **kargs)
         self._shape = None
         self.sigRegionChanged.connect(self.invalidate)
         self.aspectLocked = True
