#!/usr/bin/python
# ****************************************************************************
# *** fonalib.py: basic library used to interface with fona module sold by 
# ***             AdaFruit. This library simplifies the startup protocol as 
# ***             well as sending text messages.
# ***
# *** Author: Serge Bollaerts
# *** Version: 21/12/2015
# ***
# *** This code is provided as-is without any warranty. it can be freely 
# *** reused in your personal or commercial projects.
# ***
# *** Change log:
# *** 21/12/2015: First version of the library
# ****************************************************************************
# === Declaration of libraries to import =====================================
import serial  # Used to manage serial communication
import time  # Used to force waiting period
from datetime import datetime


class Fona:
    OPEN_RETRY_COUNT = 3  # How many "AT" attempts before giving up?
    OPEN_RETRY_SLEEP = 5  # Delay between two attempts

    # Declaration of possible statuses
    STATUS_CLOSED = 0  # Serial connection not yet opened
    STATUS_OPENING = 1  # Opening serial port and checking for fona presence
    STATUS_DISCONNECTED = 2  # Serial connection OK but not connected to a carrier
    STATUS_CONNECTING = 3  # Enter PIN code and connect to an operator
    STATUS_IDLE = 4  # Ready to process a commande
    STATUS_BUSY = 5  # Command being processed
    STATUS_ERROR = 999  # Module in unrecoverable error state

    # Log levels
    LOG_INFO = 0
    LOG_WARNING = 1
    LOG_ERROR = 2

    # Parameters passed to the class
    __port__ = None  # Serial port (i.e.: /dev/ttyAMA0)
    __speed__ = None  # Connection speed (i.e.: 115200)
    __pin__ = None   # PIN code
    __verbose__ = False  # Show debug messages?

    # Internal members
    __serial__ = None  # Serial connection object
    __status__ = STATUS_CLOSED  # Status
    __error__ = None  # Error message

    # ========================================================================
    # === Internal methods
    # ========================================================================
    def __init__(self, port, speed, pin, verbose=False):
        """Initialize a new object"""

        # Save connection parameters
        self.__port__ = port
        self.__speed__ = speed
        self.__pin__ = pin
        self.__verbose__ = verbose

        if self.__verbose__:
            self.__log__("init",
                         "port(%s) speed(%s) pin(%s) verbose(%s)" % (port,
                                                                     speed,
                                                                     pin,
                                                                     verbose),
                         self.LOG_INFO)

        # Connect to the fona module
        try:
            rc = self.open()
        except:
            rc = False
        if not rc:
            return
        
        # Connect to the phone carrier
        try:
            rc = self.connect()
        except:
            rc = False
        if not rc:
            return

    def __request__(self, command):
        """Send a request to Fona and retrieve the result"""

        self.__serial__.write("%s\r" % command)
        self.__serial__.flush()

        result = self.__serial__.read(self.__serial__.inWaiting())
        response = result.splitlines()

        if self.__verbose__:
            self.__log__("request",
                         ("%s -> %s" % (command, response)),
                         self.LOG_INFO)

        return response

    def __log__(self, source, message, level):
        """Display log information on screen"""

        msg = "[%s] %s(): %s" % (datetime.now().time(),
                                 source,
                                 message)

        if level in [self.LOG_WARNING, self.LOG_ERROR]:
            self.__error__ = msg

        if level in [self.LOG_ERROR]:
            self.__status__ = self.STATUS_ERROR
            raise Exception(self.__error__)
        
        if self.__verbose__:
            print("%s%s" % ("***" if level in [self.LOG_WARNING, self.LOG_ERROR] else "", msg))

    # ========================================================================
    # === Public methods
    # ========================================================================
    def open(self):
        """Open serial line and verify the availability of Fona module
        :rtype: Bool
        """

        self.__error__ = None

        if self.__status__ != self.STATUS_CLOSED:
            self.__log__("open",
                         ("Cannot open serial port: unknown status (%s)" % self.__status__),
                         self.LOG_ERROR)
        else:
            self.__status__ = self.STATUS_OPENING
            try:
                self.__serial__ = serial.Serial(self.__port__, self.__speed__)
            except:
                self.__log__("open",
                             "Error while opening serial port",
                             self.LOG_ERROR)

            retry = self.OPEN_RETRY_COUNT
            while retry > 0:
                rc = self.__request__("AT")
                if len(rc) != 0 and rc[len(rc) - 1].startswith("OK"):
                    self.__status__ = self.STATUS_DISCONNECTED
                    return True
                else:
                    # Device missing or not ready -> Wait and retry
                    retry -= 1
                    time.sleep(self.OPEN_RETRY_SLEEP)

            self.__log__("open",
                         "AT command does not provide the expected result",
                         self.LOG_ERROR)

    def connect(self):
        """Connect to the phone network"""

        self.__error__ = None

        if self.__status__ != self.STATUS_DISCONNECTED:
            self.__log__("connect",
                         "Serial line is not opened: impossible to connect to the network",
                         self.LOG_ERROR)
        else:
            # Check if already connected to a network
            if self.is_connected():
                self.__log__("connect",
                             "Already connected -> Skipping PIN code",
                             self.LOG_INFO)
                self.__status__ = self.STATUS_IDLE
                return True                
            else:
                # Encodage du code PIN
                self.__status__ = self.STATUS_CONNECTING
                self.__request__("AT+CPIN=%s" % self.__pin__)

                time.sleep(10)

                if self.is_connected():
                    self.__status__ = self.STATUS_IDLE
                    return True
                else:
                    return False

    def is_connected(self):
        """Check if the device is already connected to a phone network"""
        
        if self.__serial__ is not None:
            # Retrieve information about the connected phone carrier
            rc = self.__request__("AT+COPS?")
            if rc[len(rc) - 1] != "OK":
                self.__log__("connect",
                             "Unexpected result while checking phone network",
                             self.LOG_WARNING)
                return False
            elif rc[2] == "+COPS: 0":
                return False
            else:
                return True
            
    def close(self):
        """Close the serial line"""

        self.__error__ = None

        if self.__serial__ is not None:
            self.__serial__.close()
            self.__serial__ = None

        self.__status__ = self.STATUS_CLOSED

    def panic(self):
        if self.__serial__ is not None:
            self.__serial__.close()
            self.__serial__ = None

        comm = serial.Serial(self.__port__, self.__speed__)

        comm.write("AT+CPOWD=1\r")
        comm.flush()

        comm.close()

        self.__log__("panic",
                     "Device in panic mode",
                     self.LOG_ERROR)

    def send(self, phone, message):
        """Send a text message
        :param phone: phone number
        :param message: message to send
        """

        self.__error__ = None

        # Force the communication mode to "TEXT" (instead of "PDU")
        rc = self.__request__("AT+CMGF=1")
        if rc[len(rc) - 1] != "OK":
            self.__log__("send",
                         "The message format could not be set to TEXT",
                         self.LOG_WARNING)
            return False

        # Send text message
        self.__request__('AT+CMGS="%s"' % phone)
        self.__request__("%s\x1a" % message)

        return True

    # ========================================================================
    # === Properties
    # ========================================================================
    @property
    def status(self):
        return self.__status__

    @property
    def error(self):
        return self.__error__ 
