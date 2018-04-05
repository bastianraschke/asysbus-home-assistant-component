#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Asysbus component.

For more details about this component, please refer to the documentation at
https://sicherheitskritisch.de/
"""

import asyncio
import homeassistant.helpers.config_validation as cv
import logging
import os.path
import re
import voluptuous as vol

from serial_asyncio import open_serial_connection

from homeassistant.const import (
    EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP
)

REQUIREMENTS = ['pyserial-asyncio==0.4']

_LOGGER = logging.getLogger(__name__)
DOMAIN = 'asysbus'

CONF_SERIAL_PORT = 'serial_port'
CONF_BAUDRATE = 'baudrate'

DEFAULT_BAUDRATE = 115200

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_SERIAL_PORT): cv.string,
        vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): cv.positive_int,
    }),
}, extra=vol.ALLOW_EXTRA)

EVENT_HOMEASSISTANT_ASYSBUS_SERIAL_READY = \
    "event_homeassistant_asysbus_serial_ready"

ASBSERIALBRIDGE = None

## TODO: Extract to configuration
ASB_BRIDGE_NODE_ID = 0x0001

ASB_PKGTYPE_BROADCAST = 0x00
ASB_PKGTYPE_MULTICAST = 0x01
ASB_PKGTYPE_UNICAST = 0x02

ASB_CMD_REQ = 0x40
ASB_CMD_1B = 0x51
ASB_CMD_S_LIGHT = 0xDB

@asyncio.coroutine
def async_setup(hass, config):
    """Set up the Asysbus serial bridge platform."""

    wasSuccessful = True

    serialPort = config[DOMAIN][CONF_SERIAL_PORT]
    baudrate = config[DOMAIN][CONF_BAUDRATE]

    global ASBSERIALBRIDGE

    if (os.path.exists(serialPort)):
        ASBSERIALBRIDGE = AsysbusSerialBridge(hass, serialPort, baudrate)
    else:
        _LOGGER.error("async_setup(): The serial port '%s' for " + \
            "the Asysbus serial bridge is not accessible!",
            serialPort
        )
        wasSuccessful = False

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, startAsysbusService)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stopAsysbusService)

    return wasSuccessful

@asyncio.coroutine
def startAsysbusService(event):
    """Start the Asysbus serial bridge service."""

    if (ASBSERIALBRIDGE is not None):
        ASBSERIALBRIDGE.startConnection()

@asyncio.coroutine
def stopAsysbusService(event):
    """Stop the Asysbus serial bridge service."""

    if (ASBSERIALBRIDGE is not None):
        ASBSERIALBRIDGE.closeConnection()

class AsbMeta(object):
    def __init__(self, type, port, source, target):
        self.type = type
        self.port = port
        self.source = source
        self.target = target

    def __eq__(self, other): 
        return (
            self.type == other.type and
            self.port == other.port and
            self.source == other.source and
            self.target == other.target
        )

class AsbPacket(object):
    def __init__(self, meta, length, data):
        self.meta = meta
        self.length = length
        self.data = data

    def __eq__(self, other): 
        return (
            self.meta == other.meta and
            self.length == other.length and
            self.data == other.data
        )

    def __str__(self):
        return ("<object AsbPacket " +
               "meta.type = 0x{:02X}, " +
               "meta.port = 0x{:02X}, " +
               "meta.source = 0x{:04X}, " +
               "meta.target = 0x{:04X}, " +
               "length = {}, " +
               "data = {}>").format(
                self.meta.type,
                self.meta.port,
                self.meta.source,
                self.meta.target,
                self.length,
                ["0x{:02X}".format(e) for e in self.data]
            )

def decodeAsbPacket(packetString):
    asbPacket = None

    packetStringRepresentation = repr(packetString)
    packetRegex = re.findall(
        r"\\x01([0-9a-fA-F]{1,2})" +
        r"\\x1f([0-9a-fA-F]{1,4})" +
        r"\\x1f([0-9a-fA-F]{1,4})" +
        r"\\x1f([0-9a-fA-F]{1,2})" +
        r"\\x1f([0-9a-fA-F]{1,2})" +
        r"\\x02([0-9a-fA-F\\x1f]*)\\x04",
        packetStringRepresentation
    )

    if (len(packetRegex) > 0):
        packetRegexResult = packetRegex[0]

        packetType = int(packetRegexResult[0], 16)
        packetPort = int(packetRegexResult[3], 16)
        packetSource = int(packetRegexResult[2], 16)
        packetTarget = int(packetRegexResult[1], 16)
        packetLength = int(packetRegexResult[4], 16)
        packetData = packetRegexResult[5]

        ## It seems the Python regex does not support nested group matching,
        ## thus match the data separately:
        packetDataRegex = re.findall(
            r"(([0-9a-fA-F]+)\\x1f)+?",
            packetData
        )

        packetLengthReceived = len(packetDataRegex)

        if (packetLength == packetLengthReceived):
            packetData = []

            for packetDataElement in packetDataRegex:
                packetDataElementByte = int(packetDataElement[1], 16)
                packetData.append(packetDataElementByte)

            asbPacket = AsbPacket(
                AsbMeta(
                    packetType,
                    packetPort,
                    packetSource,
                    packetTarget,
                ),
                packetLength,
                packetData
            )

        else:
            _LOGGER.warning("decodeAsbPacket(): The packet length (%s) " + \
                "is not equal to the received packet data length (%s)!",
                packetLength,
                packetLengthReceived
            )

    return asbPacket

def encodeAsbPacket(asbPacket):
    asbPacketPort = asbPacket.meta.port if asbPacket.meta.port > 0 else 0xFF

    ## The iterator element must be cast to integer to be sure it can formatted
    asbPacketData = "".join([
        "{:X}\x1F".format(int(e)) for e in asbPacket.data
    ])

    asbPacketString = (
        "\x01{:X}\x1F" +
        "{:X}\x1F" +
        "{:X}\x1F" +
        "{:X}\x1F" +
        "{:X}\x02" +
        "{:s}\x04").format(
        asbPacket.meta.type,
        asbPacket.meta.target,
        asbPacket.meta.source,
        asbPacketPort,
        asbPacket.length,
        asbPacketData,
    )

    asbPacketEncoded = asbPacketString.encode('UTF-8')
    return asbPacketEncoded

def constrain(value, minValue, maxValue):
    return min(maxValue, max(minValue, value))

class AsysbusSerialBridge(object):
    """Representation of a Asysbus serial brigde."""

    def __init__(self, hass, serialPort, baudrate):
        self.__hass = hass
        self.__serialPort = serialPort
        self.__baudrate = baudrate
        self.__serialLoopTask = None
        self.__serialWriter = None
        self.__devices = []

    def startConnection(self):
        _LOGGER.info("startConnection(): Starting serial connection to " + \
            "Asysbus serial bridge..."
        )

        self.__serialLoopTask = self.__hass.loop.create_task(
            self.__readPacket(self.__serialPort, self.__baudrate)
        )

    def closeConnection(self):
        _LOGGER.info("closeConnection(): Closing serial connection to " + \
            "Asysbus serial bridge..."
        )

        if self.__serialLoopTask:
            self.__serialLoopTask.cancel()

    def registerDevice(self, device):
        """Register a device on the bridge."""
        self.__devices.append(device)

    def unregisterDevice(self, device):
        """Unregister a device from the bridge."""
        self.__devices.remove(device)

    def writePacket(self, asbPacket):
        ## StreamWriter.write() doesn't block, so no "yield from" needed
        if (self.__serialWriter is not None):
            encodedAsbPacket = encodeAsbPacket(asbPacket)
            self.__serialWriter.write(encodedAsbPacket)

            _LOGGER.info("writePacket(): Wrote the packet: %s " + \
                "(binary representation = %s)",
                asbPacket,
                encodedAsbPacket
            )
        else:
            _LOGGER.warn("writePacket(): You tried to sent data but the " + \
                "serial connection is still not established!"
            )

    @asyncio.coroutine
    def __readPacket(self, serialPort, baudrate, **kwargs):
        """Read the data from the serial port."""

        serialReader, self.__serialWriter = yield from open_serial_connection(
            url = serialPort,
            baudrate = baudrate,
            **kwargs
        )

        serialInitializedIsSet = False

        while True:
            readLine = yield from serialReader.readline()
            asbPacketString = readLine.decode('UTF-8').strip()
            decodedAsbPacket = decodeAsbPacket(asbPacketString)

            ## If the serial connection is ready, notify event once
            if (serialInitializedIsSet == False):
                _LOGGER.info("__readPacket(): The serial connection is ready.")

                self.__hass.bus.async_fire(
                    EVENT_HOMEASSISTANT_ASYSBUS_SERIAL_READY
                )
                serialInitializedIsSet = True

            if (decodedAsbPacket is not None):
                _LOGGER.info("__readPacket(): Received a packet: %s",
                    decodedAsbPacket
                )

                try:
                    for device in self.__devices:
                        device.onPacketReceived(decodedAsbPacket)
                except Exception as e:
                    _LOGGER.exception("__readPacket(): An exception is " + \
                        "occurred while notifying observing devices!"
                    )

class AsysbusNode():
    """Parent class for all Asysbus devices."""

    def __init__(self, hass, nodeId, name):
        self._nodeId = nodeId
        self._name = name

        ASBSERIALBRIDGE.registerDevice(self)

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_ASYSBUS_SERIAL_READY,
            lambda event: self._sendRequestCurrentState()
        )

    def _sendRequestCurrentState(self):
        global ASBSERIALBRIDGE

        _LOGGER.info("_sendRequestCurrentState((): Request current state " + \
            "of device '%s' to be synced with device.",
            self._name
        )

        asbPacketData = [ASB_CMD_REQ]
        ASBSERIALBRIDGE.writePacket(AsbPacket(
            meta = AsbMeta(
                type = ASB_PKGTYPE_MULTICAST,
                port = 0xFF,
                source = ASB_BRIDGE_NODE_ID,
                target = self._nodeId
            ),
            length = len(asbPacketData),
            data = asbPacketData
        ))

    def onPacketReceived(self, packet):
        raise NotImplementedError()
