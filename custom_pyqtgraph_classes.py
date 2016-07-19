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

class Crosshair(pg.ROI):
    def __init__(self,pos,**kargs):
        super(Crosshair, self).__init__(pos,**kargs)
        #QtGui.QGraphicsItem.__init__(self)
        self.setFlag(self.ItemIgnoresTransformations)

    def paint(self, p, *args):
        p.setPen(pg.mkPen('y'))
        p.drawLine(-2, 0, -10, 0)
        p.drawLine(0, -2, 0, -10)
        p.drawLine(10, 0, 2, 0)
        p.drawLine(0, 10, 0, 2)

        p.setPen(pg.mkPen('b'))
        p.drawLine(-10, 0, 10, 0)
        p.drawLine(0, -10, 0, 10)


    def boundingRect(self):
        return QtCore.QRectF(-10, -10, 20, 2)