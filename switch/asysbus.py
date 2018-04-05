#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Asysbus switch component.

For more details about this component, please refer to the documentation at
https://sicherheitskritisch.de/
"""

import asyncio
import custom_components.asysbus as asysbus
import homeassistant.helpers.config_validation as cv
import logging
import voluptuous as vol

from custom_components.asysbus import (
    ASB_BRIDGE_NODE_ID,
    ASB_CMD_1B,
    ASB_PKGTYPE_MULTICAST,
    AsbMeta,
    AsbPacket,
    AsysbusNode
)

from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.const import CONF_ID, CONF_NAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.entity import ToggleEntity

DEPENDENCIES = ['asysbus']

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Asysbus switch"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ID): vol.All(vol.Coerce(int), vol.Range(
        min=0x0000,
        max=0xFFFF
    )),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Asysbus switch platform."""

    if asysbus.ASBSERIALBRIDGE is None:
        _LOGGER.error("async_setup_platform(): The Asysbus serial bridge " + \
            "could not be connected!"
        )
        return False

    asysbusSwitchNodeId = config.get(CONF_ID)
    asysbusSwitchName = config.get(CONF_NAME)

    async_add_devices([
        AsysbusSwitch(hass, asysbusSwitchNodeId, asysbusSwitchName)
    ])

class AsysbusSwitch(AsysbusNode, ToggleEntity):
    """Representation of an Asysbus switch."""

    def __init__(self, hass, nodeId, name):
        AsysbusNode.__init__(self, hass, nodeId, name)
        self.__state = False

    def onPacketReceived(self, packet):
        if (packet.meta.source == self._nodeId):
            if (packet.data[0] == ASB_CMD_1B and packet.data[1] in [0x0, 0x1]):
                self.__state = (packet.data[1] == 0x1)
                self.async_schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def is_on(self):
        """Return True if device is on."""
        return self.__state

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        self.__state = True
        self.__sendCurrentState()
        self.async_schedule_update_ha_state()

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        self.__state = False
        self.__sendCurrentState()
        self.async_schedule_update_ha_state()

    def __sendCurrentState(self):
        _LOGGER.info("__sendCurrentState(): The state of switch '%s' " + \
            "is send to device: state = %s",
            self._name,
            self.__state,
        )

        asbPacketData = [ASB_CMD_1B, 0x1 if self.__state == True else 0x0]
        asysbus.ASBSERIALBRIDGE.writePacket(AsbPacket(
            meta = AsbMeta(
                type = ASB_PKGTYPE_MULTICAST,
                port = 0xFF,
                source = ASB_BRIDGE_NODE_ID,
                target = self._nodeId
            ),
            length = len(asbPacketData),
            data = asbPacketData
        ))
