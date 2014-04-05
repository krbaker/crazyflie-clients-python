#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2014 Keith Baker
#
#  Phoenix USB PWM Adapter Control
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""
Driver for reading data directly from Phoenix RC USB Adapter. Used from Inpyt.py for reading input data.
"""

__author__ = 'Keith Baker'
__all__ = ['PhoenixUsbReader']

VENDOR = 0x1781
PRODUCT = 0x0898

import usb
from time import time

class PhoenixUsbReader():
    """Used for reading data from input devices using the Phoenix USB."""
    def __init__(self):
        self.inputMap = None
        self._ts_last_event = None
        self._first_time_opened = True
        self._current_device_id = -1
        self._device_count = 0

    def start_input(self, device, inputMap):
        """Initalize the reading and open the device with deviceId and set the mapping for axis/buttons using the
        inputMap"""
        self.data = {"roll":0.0, "pitch":0.0, "yaw":0.0, "thrust":0.0, "pitchcal":0.0, "rollcal":0.0, "estop": False, "exit":False, "althold":False}
        self.inputMap = inputMap
        self._ts_last_event = time()
        self._first_time_opened = True
        self._usb_device = self.getAvailableDevices()[0]["id"]
        self._usb_handle = self._usb_device.open()
        try:
            self._usb_handle.detachKernelDriver(0)
        except usb.USBError:
            pass #probably already done?
        self._usb_handle.setConfiguration(1)
        self._usb_handle.claimInterface(0)

    def _zero_output(self):
        self.data["roll"] = 0.0
        self.data["pitch"] = 0.0
        self.data["yaw"] = 0.0
        self.data["thrust"] = 0.0

    def read_input(self):
        """Read input from the selected device."""
        # We only want the pitch/roll cal to be "oneshot", don't
        # save this value.
        self.data["pitchcal"] = 0.0
        self.data["rollcal"] = 0.0

        data = self._usb_handle.bulkRead(1, self._usb_device.maxPacketSize)

        for i,d in enumerate(data):
            index = "Input.AXIS-%d" % i 
            try:
                if self.inputMap[index]["type"] == "Input.AXIS":
                    key = self.inputMap[index]["key"]
                    # values are 0 - 255, recenter
                    axisvalue = float(d - 128) * self.inputMap[index]["scale"]
                    #keep in bounds so we don't try to send bad data
                    axisvalue = min(1,axisvalue)
                    axisvalue = max(-1,axisvalue)
                    # The value is now in the correct direction and in the range [-1,1]
                    self.data[key] = axisvalue
            except Exception:
                # Axis not mapped, ignore..
                pass          

        self._ts_last_event = time()

        # Ignore the first round of events from the device
        # after it has been opened. This cases issues on
        # Linux since it will max out all the axis
        if self._first_time_opened == True:
            self._zero_output()
            self._first_time_opened = False

        return self.data

    def enableRawReading(self, device):
        """Enable reading of raw values (without mapping)"""
        self._usb_device = self.getAvailableDevices()[0]["id"]
        self._usb_handle = self._usb_device.open()
        try:
            self._usb_handle.detachKernelDriver(0)
        except usb.USBError:
            pass #probably already done?
        self._usb_handle.setConfiguration(1)
        self._usb_handle.claimInterface(0)

    def disableRawReading(self):
        """Disable raw reading"""
        # No need to de-init since there's no good support for multiple input devices
        self._usb_handle.releaseInterface()

    # This doesn't seem to work, maybe becuase we feed all values, not just changes?
    def readRawValues(self):
        """Read out the raw values from the device"""
        rawaxis = {}
        rawbutton = {}

        data = self._usb_handle.bulkRead(1, self._usb_device.maxPacketSize)

        for i,d in enumerate(data):
            rawaxis[i] = d

        return [rawaxis,rawbutton]

    def getAvailableDevices(self):
        """List all the available devices."""
        devices = []
        for bus in usb.busses():
            for device in bus.devices:
                if device.idVendor == VENDOR and device.idProduct == PRODUCT:
                    devices.append({"id": device, "name": str(device.devnum)})
        return devices

