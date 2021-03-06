from ..PyQt.QtGui import QLabel, QApplication, QColor, QActionGroup
from ..PyQt.QtCore import pyqtSignal, pyqtSlot, pyqtProperty
from pyqtgraph import ImageView
from pyqtgraph import ImageItem
from pyqtgraph import ColorMap
import numpy as np
from .channel import PyDMChannel
from .colormaps import cmaps
import epics

class PyDMADGEImageView(ImageView):
  color_maps = cmaps  
  def __init__(self, parent=None, image_channel=None, width_channel=None, height_channel=None, mon_channel = None):
    super(PyDMADGEImageView, self).__init__(parent)
    self._imagechannel = image_channel
    self._widthchannel = width_channel
    self._heightchannel = height_channel
    self._monchannel = mon_channel
    self.image_waveform = np.zeros(0)
    self.image_width = 0
    self.ui.histogram.hide()
    del self.ui.histogram
    self.ui.roiBtn.hide()
    self.ui.menuBtn.hide()
    self.cm_min = 0.0
    self.cm_max = 255.0
    self.data_max_int = 255 #This is the max value for the image waveform's data type.  It gets set when the waveform updates.
    self._colormapname = "inferno"
    self._cm_colors = None
    self._needs_reshape = False
    self.setColorMapToPreset(self._colormapname)
    cm_menu = self.getView().getMenu(None).addMenu("Color Map")
    cm_group = QActionGroup(self)
    for map_name in self.color_maps:
      action = cm_group.addAction(map_name)
      action.setCheckable(True)
      cm_menu.addAction(action)
      if map_name == self._colormapname:
        action.setChecked(True)
    cm_menu.triggered.connect(self.changeColorMap)
    

  def changeColorMap(self, action):
    self.setColorMapToPreset(str(action.text()))

  @pyqtSlot(int)
  def setColorMapMin(self, new_min):
    if self.cm_min != new_min:
      self.cm_min = new_min
      if self.cm_min > self.cm_max:
        self.cm_max = self.cm_min
      self.setColorMap()

  @pyqtSlot(int)
  def setColorMapMax(self, new_max):
    if self.cm_max != new_max:
      if new_max >= self.data_max_int:
        new_max = self.data_max_int
      self.cm_max = new_max
      if self.cm_max < self.cm_min:
        self.cm_min = self.cm_max
      self.setColorMap()
  
  def setColorMapLimits(self, min, max):
    self.cm_max = max
    self.cm_min = min
    self.setColorMap()
    
  def setColorMapToPreset(self, name):
    self._colormapname = str(name)
    self._cm_colors = self.color_maps[str(name)]
    self.setColorMap()

  def setColorMap(self, map=None):
    if not map:
      if not self._cm_colors.any():
        return
      pos = np.linspace(self.cm_min/float(self.data_max_int), self.cm_max/float(self.data_max_int), num=len(self._cm_colors))
      map = ColorMap(pos, self._cm_colors)
    self.getView().setBackgroundColor(map.map(0))
    lut = map.getLookupTable(0.0,1.0,self.data_max_int, alpha=False)
    self.getImageItem().setLookupTable(lut)
    self.getImageItem().setLevels([self.cm_min/float(self.data_max_int),float(self.data_max_int)])
#
#  @pyqtSlot(np.ndarray)
#  def receiveImageWaveform(self, new_waveform):
#    if new_waveform is None:
#      return
#    if self.image_width == 0:
#      self.image_waveform = new_waveform
#      self._needs_reshape = True
#      #We'll wait to draw the image until we get the width.
#      return
#    if len(new_waveform.shape) == 1:
#      self.image_waveform = new_waveform.reshape((int(self.image_width),-1), order='F')
#    elif len(new_waveform.shape) == 2:
#      self.image_waveform = new_waveform
#    self.data_max_int = np.iinfo(self.image_waveform.dtype).max
#    self.redrawImage()
  
  @pyqtSlot(int)
  @pyqtSlot(float)
  @pyqtSlot(str)
  def receiveImageWidth(self, new_width):
    if new_width is None:
      return
      
    self.image_width = int(new_width)
    #print "receiveImageWidth %i"%self.image_width

    if self._needs_reshape:
      self.image_waveform = self.image_waveform.reshape((int(self.image_width),-1), order='F')
      self._needs_reshape = False
    self.redrawImage()
  
  
   
  @pyqtSlot(int)
  @pyqtSlot(float)
  @pyqtSlot(str)
  def receiveImageHeight(self, new_height):
    if new_height is None:
      return
    self.image_height = int(new_height)
    #print "receiveImageHeight %i"%self.image_height

    #if self._needs_reshape:
    #  self.image_waveform = self.image_waveform.reshape((int(self.image_width),-1), order='F')
    #  self._needs_reshape = False
    #self.redrawImage()
  
  
  
  @pyqtSlot(int)
  @pyqtSlot(float)
  @pyqtSlot(str)
  def receiveImageCounter(self, new_counter):
    if new_counter is None:
      return
    self.image_counter = int(new_counter)
    
    #print "receiveImageCounter %d"%self.image_counter
    
    #print "receiveImageCounter, to get image data %s"%self._imagechannel[5:]
    
    datalen = self.image_width * self.image_height
    
    self.image_waveform = epics.caget(self._imagechannel[5:], count = int(datalen))
    #print "%s"%self.image_waveform[0:32]
    self._needs_reshape=True
    
    if self._needs_reshape:
      self.image_waveform = self.image_waveform.reshape((int(self.image_width),int(self.image_height)), order='F')
      self._needs_reshape = False
    self.redrawImage()
  
  
 
 
  def redrawImage(self):
    if len(self.image_waveform) > 0 and self.image_width > 0:
      self.getImageItem().setImage(self.image_waveform, autoLevels=False)
  
  # -2 to +2, -2 is LOLO, -1 is LOW, 0 is OK, etc.  
  @pyqtSlot(int)
  def alarmStatusChanged(self, new_alarm_state):
    pass
  
  #0 = NO_ALARM, 1 = MINOR, 2 = MAJOR, 3 = INVALID  
  @pyqtSlot(int)
  def alarmSeverityChanged(self, new_alarm_severity):
    pass
    
  #false = disconnected, true = connected
  @pyqtSlot(bool)
  def connectionStateChanged(self, connected):
    pass

  def getImageChannel(self):
    return str(self._imagechannel)
  
  def setImageChannel(self, value):
    if self._imagechannel != value:
      self._imagechannel = str(value)

  def resetImageChannel(self):
    if self._imagechannel != None:
      self._imagechannel = None
    
  imageChannel = pyqtProperty(str, getImageChannel, setImageChannel, resetImageChannel)
  
  def getWidthChannel(self):
    return str(self._widthchannel)
  
  def setWidthChannel(self, value):
    if self._widthchannel != value:
      self._widthchannel = str(value)

  def resetWidthChannel(self):
    if self._widthchannel != None:
      self._widthchannel = None
    
  widthChannel = pyqtProperty(str, getWidthChannel, setWidthChannel, resetWidthChannel)

  def getHeightChannel(self):
    return str(self._heightchannel)
  
  def setHeightChannel(self, value):
    if self._heightchannel != value:
      self._heightchannel = str(value)

  def resetHeightChannel(self):
    if self._heightchannel != None:
      self._heightchannel = None


  heightChannel = pyqtProperty(str, getHeightChannel, setHeightChannel, resetHeightChannel)
  
  
  def getMonChannel(self):
    return str(self._monchannel)
  
  def setMonChannel(self, value):
    if self._monchannel != value:
      self._monchannel = str(value)

  def resetMonChannel(self):
    if self._monchannel != None:
      self._monchannel = None

  
  monChannel = pyqtProperty(str, getMonChannel, setMonChannel, resetMonChannel)
  
  def channels(self):
    return [PyDMChannel(address=self.widthChannel, connection_slot=self.connectionStateChanged, value_slot=self.receiveImageWidth, severity_slot=self.alarmSeverityChanged),
            PyDMChannel(address=self.heightChannel, connection_slot=self.connectionStateChanged, value_slot=self.receiveImageHeight, severity_slot=self.alarmSeverityChanged),
            PyDMChannel(address=self.monChannel, connection_slot=self.connectionStateChanged, value_slot=self.receiveImageCounter, severity_slot=self.alarmSeverityChanged)]
