# -*- coding: utf-8 -*-
"""
Widget for entering amplitude specifications

Author: Christian Münker
"""

# TODO: Check specs IIR / FIR A_PB <-> delta_PB

from __future__ import print_function, division, unicode_literals
from numpy import sqrt
import sys
import logging
logger = logging.getLogger(__name__)
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import pyqtSignal, Qt

import pyfda.filterbroker as fb
from pyfda.pyfda_lib import rt_label, lin2unit
from pyfda.simpleeval import simple_eval

class InputAmpSpecs(QtGui.QWidget): #QtGui.QWidget,
    """
    Build and update widget for entering the amplitude
    specifications like A_sb, A_pb etc.
    """
    
    sigSpecsChanged = pyqtSignal()
    
    def __init__(self, parent, title = "Amplitude Specs"):
        """
        Initialize
        """
        super(InputAmpSpecs, self).__init__(parent)
        self.title = title

        self.qlabels = [] # list with references to QLabel widgets
        self.qlineedit = [] # list with references to QLineEdit widgets

        self._init_UI()

    def _init_UI(self):
        """
        Initialize User Interface
        """
        self.layVMain = QtGui.QVBoxLayout() # Widget vertical layout

        amp_units = ["dB", "V", "W"]

        bfont = QtGui.QFont()
        bfont.setBold(True)
#            bfont.setWeight(75)
        self.lblTitle = QtGui.QLabel(self) # field for widget title
        self.lblTitle.setText(str(self.title))
        self.lblTitle.setFont(bfont)
        self.lblTitle.setWordWrap(True)
        self.layVMain.addWidget(self.lblTitle)

        self.lblUnits = QtGui.QLabel(self)
        self.lblUnits.setText("Unit:")

        self.cmbUnitsA = QtGui.QComboBox(self)
        self.cmbUnitsA.addItems(amp_units)
        self.cmbUnitsA.setObjectName("cmbUnitsA")
        self.cmbUnitsA.setToolTip("Set unit for amplitude specifications:\n"
        "dB is attenuation (positive values)\nV and W are less than 1.")

        self.cmbUnitsA.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToContents)
        # fit size dynamically to largest element

        # find index for default unit from dictionary and set the unit     
        amp_idx = self.cmbUnitsA.findData(fb.fil[0]['amp_specs_unit'])
        if amp_idx < 0:
            amp_idx = 0
        self.cmbUnitsA.setCurrentIndex(amp_idx) # initialize for dBsg
        
        self.layGSpecs = QtGui.QGridLayout() # sublayout for spec fields
        self.layGSpecs.addWidget(self.lblUnits,0,0)
        self.layGSpecs.addWidget(self.cmbUnitsA,0,1, Qt.AlignLeft)

        # - Build a list from all entries in the fil_dict dictionary starting
        #   with "A" (= amplitude specifications of the current filter)
        # - Pass the list to setEntries which recreates the widget
        # ATTENTION: Entries need to be converted from QString to str for Py 2
        newLabels = [str(l) for l in fb.fil[0] if l[0] == 'A'] 
        self.update_UI(newLabels = newLabels)

        frmMain = QtGui.QFrame()
        frmMain.setFrameStyle(QtGui.QFrame.StyledPanel|QtGui.QFrame.Sunken)
        frmMain.setLayout(self.layGSpecs)

        self.layVMain.addWidget(frmMain)
        self.layVMain.setContentsMargins(1,1,1,1)

        self.setLayout(self.layVMain)

        #----------------------------------------------------------------------
        # SIGNALS & SLOTs
        #----------------------------------------------------------------------
        self.cmbUnitsA.currentIndexChanged.connect(self.load_entries)
        # DYNAMIC SIGNAL SLOT CONNECTION:
        # Every time a field is edited, call self.load_entries - this signal-slot
        # mechanism is constructed in self._add_entry/ destructed in 
        # self._del_entry each time the widget is updated, i.e. when a new 
        # filter design method is selected.
        #----------------------------------------------------------------------

#        self.load_entries() # is executed by the statement above

#------------------------------------------------------------------------------
    def load_entries(self):
        """
        Reload textfields from filter dictionary to reflect settings that
        may have been changed by the filter design algorithm and convert to 
        selected unit. Store the unit in the filter dictionary.
        """

        unit = str(self.cmbUnitsA.currentText())
        fb.fil[0]['amp_specs_unit'] = unit
 
        for i in range(len(self.qlineedit)):
            amp_label = str(self.qlineedit[i].objectName())
            value = fb.fil[0][amp_label]
            filt_type = fb.fil[0]['ft']
            
            self.qlineedit[i].setText(
                str(lin2unit(value, filt_type, amp_label, unit = unit)))

#------------------------------------------------------------------------------
    def _store_entries(self):
        """
        Transform the amplitude spec input fields according to the Units
        setting. Spec entries are *always* stored in linear units; only the 
        displayed values are adapted to the amplitude unit, not the dictionary!
        """


        def unit2lin(amp_label, dB_value, unit = 'dB'):
            """
            Convert unit to linear ripple:
            - passband: delta_PB = 1 - 10 ** (-A_PB/10 resp. 20) [IIR]
                        delta_PB = (10 ** (A_PB / 20) - 1)/ (10 ** (A_PB / 20) + 1)[FIR]
            - stopband: delta_SB = -10 ** (-A_SB/10 resp. 20)
            """
            if "PB" in amp_label: # passband
                if fb.fil[0]['ft'] == 'IIR':
                    delta = round(1. - 10.**(-dB_value / 20.), 10)
                else: 
                    delta = round((10.**(dB_value / 20.) - 1)/
                                    (10.**(dB_value / 20.) + 1),10)
            else: # stopband
                delta = round(10.**(-dB_value / 20), 10)
            return delta

        idx = self.cmbUnitsA.currentIndex()  # read index of units combobox  
        unit = str(self.cmbUnitsA.currentText())
        
        for i in range(len(self.qlineedit)):
            amp_label = str(self.qlineedit[i].objectName())
            amp_value = simple_eval(self.qlineedit[i].text())
            if idx == 0: # Entry is in dBs, convert to linear
                fb.fil[0].update({amp_label:unit2lin(amp_label, amp_value)})
            elif idx == 1:  # Entries are linear ripple, same as dictionary
                fb.fil[0].update({amp_label:amp_value})
            else:  # Entries are powers, convert to lin
                fb.fil[0].update({amp_label:sqrt(amp_value)})
                       
        self.sigSpecsChanged.emit() # -> input_specs


#------------------------------------------------------------------------------
    def update_UI(self, newLabels = []):
        """
        Set labels and get corresponding values from filter dictionary.
        When number of elements changes, the layout of subwidget is rebuilt in
        self.layGSpecs.
        """
        # Check whether the number of entries has changed
        for i in range(max(len(self.qlabels), len(newLabels))):
             # newLabels is shorter than qlabels -> delete the difference
            if (i > (len(newLabels)-1)):
                self._del_entry(len(newLabels))

            # newLabels is longer than existing qlabels -> create new ones!
            elif (i > (len(self.qlabels)-1)):
             self._add_entry(i,newLabels[i])

            else:
                # when entry has changed, update label and corresponding value
                if self.qlineedit[i].objectName() != newLabels[i]:
                    self.qlabels[i].setText(rt_label(newLabels[i]))
                    
                    self.qlineedit[i].setText(str(fb.fil[0][newLabels[i]]))
                    self.qlineedit[i].setObjectName(newLabels[i])  # update ID

        self.load_entries()

#------------------------------------------------------------------------------
    def _del_entry(self,i):
        """
        Delete entry number i from subwidget (QLabel and QLineEdit) and
        disconnect the lineedit field from self._amp_units
        """
        self.qlineedit[i].editingFinished.disconnect(self._store_entries) # needed?
        
        self.layGSpecs.removeWidget(self.qlabels[i])
        self.layGSpecs.removeWidget(self.qlineedit[i])

        self.qlabels[i].deleteLater()
        del self.qlabels[i]
        self.qlineedit[i].deleteLater()
        del self.qlineedit[i]


#------------------------------------------------------------------------------
    def _add_entry(self, i, newLabel):
        """
        Append entry number i to subwidget (QLabel und QLineEdit) in self.layGSpecs
        and connect QLineEdit.editingFinished to self._amp_text. This way, the
        filter dictionary is updated automatically when a QLineEdit field has 
        been edited (i.e. looses focus or when a return is entered).
        """
        self.qlabels.append(QtGui.QLabel(self))
        self.qlabels[i].setText(rt_label(newLabel))

        self.qlineedit.append(QtGui.QLineEdit(str(fb.fil[0][newLabel])))
        self.qlineedit[i].setObjectName(newLabel) # update ID
        
        self.qlineedit[i].editingFinished.connect(self._store_entries)

        self.layGSpecs.addWidget(self.qlabels[i],(i+2),0)
        self.layGSpecs.addWidget(self.qlineedit[i],(i+2),1)

#------------------------------------------------------------------------------

if __name__ == '__main__':
    
    
    class MainWindow(QtGui.QMainWindow):
        """
        QMainWindow is used here as it is a class that understands GUI elements like
        toolbar, statusbar, central widget, docking areas etc.
        """

        def __init__(self):
            super(MainWindow, self).__init__()
            self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            self.main_widget = QtGui.QWidget()
            self.test_widget = InputAmpSpecs(self)           # instantiate widget

            layV = QtGui.QVBoxLayout(self.main_widget) # create layout manager
            layV.addWidget(self.test_widget)                 # add widget to layout
#            self.main_widget.setFocus()             # give keyboard focus to main_widget
            self.setCentralWidget(self.main_widget)
            # Set the given widget to be the main window's central widget, QMainWindow
            #  takes ownership of the widget pointer and deletes it at the appropriate time.
        def update_UI(self, newLabels):
            self.amp_widget.update_UI(newLabels=newLabels)
#------------------------------------------------------------------------------

    app = QtGui.QApplication(sys.argv) # instantiate app, pass command line arguments

    main_window = MainWindow()
    main_window.update_UI(newLabels = ['A_SB','A_SB2','A_PB','A_PB2'])
    main_window.update_UI(newLabels = ['A_PB','A_SB'])

    app.setActiveWindow(main_window)
    # Sets the active window to the active widget in response to a system event.
    # The function is called from the platform specific event handlers.
    # It sets the activeWindow() and focusWidget() attributes and sends proper 
    # WindowActivate/WindowDeactivate and FocusIn/FocusOut events to all appropriate 
    # widgets. The window will then be painted in active state (e.g. cursors in 
    # line edits will blink), and it will have tool tips enabled.
    # Warning: This function does not set the keyboard focus to the active widget. 
    # Call QWidget.activateWindow() instead.

    main_window.show()



    ret = app.exec_()
    del main_window
    sys.exit(ret)

