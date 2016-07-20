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


class fixedCrosshair(QtGui.QGraphicsRectItem):
    def __init__(self, pos=None, size=None, *args):
        QtGui.QGraphicsRectItem.__init__(self, *args)
        self.setAcceptHoverEvents(True)
        self.setPos(pos[0], pos[1])
        self.size = size
        #self.setFlag(self.ItemIgnoresTransformations)

    def paint(self, p, *args):
        p.setPen(pg.mkPen('y'))
        # p.setPen(self.savedPen)
        p.drawLine(-self.size/2, 0, -self.size, 0)
        p.drawLine(0, -self.size/2, 0, -self.size)
        p.drawLine(self.size, 0, self.size/2, 0)
        p.drawLine(0, self.size, 0, self.size/2)

        p.setPen(pg.mkPen('b'))
        p.drawLine(-self.size, -self.size, self.size, self.size)
        p.drawLine(self.size, -self.size, -self.size, self.size)

    def boundingRect(self):
        return QtCore.QRectF(-self.size, -self.size, self.size*2, self.size*2)

class movableCrosshair(QtGui.QGraphicsRectItem):
    def __init__(self, pos=None, size=None, *args):
        QtGui.QGraphicsRectItem.__init__(self, *args)
        self.setAcceptHoverEvents(True)
        self.setPos(pos[0], pos[1])
        self.size = size
        #self.setFlag(self.ItemIgnoresTransformations)

    def paint(self, p, *args):
        p.setPen(pg.mkPen('y'))
        # p.setPen(self.savedPen)
        p.drawLine(-self.size/2, 0, -self.size, 0)
        p.drawLine(0, -self.size/2, 0, -self.size)
        p.drawLine(self.size, 0, self.size/2, 0)
        p.drawLine(0, self.size, 0, self.size/2)

        p.setPen(pg.mkPen('b'))
        p.drawLine(-self.size, -self.size, self.size, self.size)
        p.drawLine(self.size, -self.size, -self.size, self.size)

    def hoverEnterEvent(self, ev):
        self.savedPen = self.pen()
        #self.setPen(pg.mkPen(255, 255, 255))
        ev.ignore()

    def hoverLeaveEvent(self, ev):
        self.setPen(self.savedPen)
        ev.ignore()

    def mousePressEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton:
            ev.accept()
            self.pressDelta = self.mapToParent(ev.pos()) - self.pos()
        else:
            ev.ignore()

    def mouseMoveEvent(self, ev):
        self.setPos(self.mapToParent(ev.pos()) - self.pressDelta)

    def boundingRect(self):
        return QtCore.QRectF(-self.size, -self.size, self.size*2, self.size*2)

import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg

app = QtGui.QApplication([])
mw = QtGui.QMainWindow()
mw.setWindowTitle('pyqtgraph example: ViewBox')
mw.show()
mw.resize(800, 600)

gv = pg.GraphicsView()
mw.setCentralWidget(gv)
l = QtGui.QGraphicsGridLayout()
l.setHorizontalSpacing(0)
l.setVerticalSpacing(0)

vb = pg.ViewBox()

p1 = pg.PlotDataItem()
vb.addItem(p1)

rect = fixedCrosshair(pos=[1.5, 2],size=1)
rect.setPen(pg.mkPen(100, 200, 100))
vb.addItem(rect)

l.addItem(vb, 0, 1)
gv.centralWidget.setLayout(l)

xScale = pg.AxisItem(orientation='bottom', linkView=vb)
l.addItem(xScale, 1, 1)
yScale = pg.AxisItem(orientation='left', linkView=vb)
l.addItem(yScale, 0, 0)

xScale.setLabel(text="<span style='color: #ff0000; font-weight: bold'>X</span> <i>Axis</i>", units="s")
yScale.setLabel('Y Axis', units='V')


def rand(n):
    data = np.random.random(n)
    data[int(n * 0.1):int(n * 0.13)] += .5
    data[int(n * 0.18)] += 2
    data[int(n * 0.1):int(n * 0.13)] *= 5
    data[int(n * 0.18)] *= 20
    return data, np.arange(n, n + len(data)) / float(n)


def updateData():
    yd, xd = rand(10000)
    p1.setData(y=yd, x=xd)


yd, xd = rand(10000)
updateData()
vb.autoRange()

t = QtCore.QTimer()
t.timeout.connect(updateData)
t.start(50)

## Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    import sys

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
