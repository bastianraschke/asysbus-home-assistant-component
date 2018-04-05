#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Asysbus light component.

For more details about this component, please refer to the documentation at
https://sicherheitskritisch.de/
"""

import asyncio
import custom_components.asysbus as asysbus
import enum
import homeassistant.helpers.config_validation as cv
import logging
import voluptuous as vol

from custom_components.asysbus import (
    ASB_BRIDGE_NODE_ID,
    ASB_CMD_S_LIGHT,
    ASB_PKGTYPE_MULTICAST,
    AsbMeta,
    AsbPacket,
    AsysbusNode,
    constrain
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_RGB_COLOR,
    PLATFORM_SCHEMA,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR_TEMP,
    SUPPORT_RGB_COLOR,
    Light
)

from homeassistant.const import CONF_ID, CONF_TYPE, CONF_NAME

from homeassistant.util.color import (
    color_rgb_to_rgbw,
    color_temperature_mired_to_kelvin as colorTemperatureToKelvin,
    color_temperature_to_rgb as colorTemperatureToRGB
)

DEPENDENCIES = ['asysbus']

_LOGGER = logging.getLogger(__name__)

@enum.unique
class LightType(enum.Enum):
    RGB = "RGB"
    RGBW = "RGBW"

    def __str__(self):
        return self.name

    def __eq__(self, other): 
        return self.name == other

DEFAULT_NAME = "Asysbus light"

LIGHT_TYPES = [str(e) for e in LightType]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ID): vol.All(vol.Coerce(int), vol.Range(
        min=0x0000,
        max=0xFFFF
    )),
    vol.Required(CONF_TYPE, default=[]): vol.All(
        cv.ensure_list,
        [vol.In(LIGHT_TYPES)]
    ),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

SUPPORT_ASYSBUSLIGHT = (
    SUPPORT_BRIGHTNESS |
    SUPPORT_RGB_COLOR |
    SUPPORT_COLOR_TEMP
)

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Asysbus light platform."""

    if asysbus.ASBSERIALBRIDGE is None:
        _LOGGER.error("async_setup_platform(): The Asysbus serial bridge " + \
            "could not be connected!"
        )
        return False

    asysbusLightNodeId = config.get(CONF_ID)
    asysbusLightName = config.get(CONF_NAME)
    asysbusLightType = config.get(CONF_TYPE)[0]

    async_add_devices([
        AsysbusLight(hass, asysbusLightNodeId, asysbusLightName, asysbusLightType)
    ])

class AsysbusLight(AsysbusNode, Light):
    """Representation of an Asysbus light."""

    def __init__(self, hass, nodeId, name, type):
        AsysbusNode.__init__(self, hass, nodeId, name)
        self.__type = type
        self.__state = False
        self.__brightness = 0
        self.__transitionEffect = True
        self.__rgbw = [0, 0, 0, 0]
        self.__colorTemperature = 0

    def onPacketReceived(self, packet):
        if (packet.meta.source == self._nodeId):
            if (packet.data[0] == ASB_CMD_S_LIGHT):
                self.__state = (packet.data[1] == 0x01)
                self.__brightness = constrain(packet.data[2], 0, 255)
                self.__transitionEffect = (packet.data[3] == 0x01)
                self.__rgbw = [
                    constrain(packet.data[4], 0, 255),
                    constrain(packet.data[5], 0, 255),
                    constrain(packet.data[6], 0, 255),
                    constrain(packet.data[7], 0, 255)
                ]

                _LOGGER.info("onPacketReceived(): The state of light '%s' " + \
                    "was received from device: " + \
                    "state = %s, " + \
                    "brightness = %s, " + \
                    "transitionEffect = %s, " + \
                    "color = %s",
                    self._name,
                    self.__state,
                    self.__brightness,
                    self.__transitionEffect,
                    self.__rgbw
                )

                self.async_schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def supported_features(self):
        """Return flag with supported features."""
        return SUPPORT_ASYSBUSLIGHT

    @property
    def brightness(self):
        """Return the brightness between 0..255."""
        return self.__brightness

    @property
    def is_on(self):
        """Return True if device is on."""
        return self.__state

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def assumed_state(self):
        """Return true if we do optimistic updates."""
        return True

    @property
    def rgb_color(self):
        """Return the RGB color value as (R, G, B)."""
        return self.__rgbw[0:3]

    @property
    def color_temp(self):
        """Return the color temperature in mired."""
        return self.__colorTemperature

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        self.__state = True

        if (ATTR_RGB_COLOR in kwargs):
            rgbColorValue = kwargs[ATTR_RGB_COLOR]
            self.__rgbw = self.__getRGBWValueFromRGBValue(rgbColorValue)

            _LOGGER.info("async_turn_on(): The color for light '%s' " + \
                "was changed to %s",
                self._name,
                self.__rgbw
            )

        if (ATTR_BRIGHTNESS in kwargs):
            if (self.__rgbw == [0, 0, 0, 0]):
                ## Initial the colors are not set, so we need to set manually
                if (self.__type == LightType.RGBW):
                    self.__rgbw = [0, 0, 0, 255]
                else:
                    self.__rgbw = [255, 255, 255, 0]

            self.__brightness = kwargs[ATTR_BRIGHTNESS]

            _LOGGER.info("async_turn_on(): The brightness for light '%s' " + \
                "was changed to %s",
                self._name,
                self.__brightness
            )

        if (ATTR_COLOR_TEMP in kwargs):
            self.__colorTemperature = kwargs[ATTR_COLOR_TEMP]
            kelvinValue = int(colorTemperatureToKelvin(self.__colorTemperature))

            rgbColorValue = colorTemperatureToRGB(kelvinValue)
            self.__rgbw = self.__getRGBWValueFromRGBValue(rgbColorValue)

            _LOGGER.info("async_turn_on(): The temperature for light '%s' " + \
                "was changed to %sK which results in color %s",
                self._name,
                kelvinValue,
                self.__rgbw
            )

        self.__sendCurrentState()
        self.async_schedule_update_ha_state()

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        self.__state = False

        _LOGGER.info("async_turn_off(): The state for light '%s' " + \
            "was changed to %s",
            self._name,
            self.__state
        )

        self.__sendCurrentState()
        self.async_schedule_update_ha_state()

    def __getRGBWValueFromRGBValue(self, rgbColorValue):
        rgbwColorValue = [0, 0, 0, 0]

        if (self.__type == LightType.RGBW):
            rgbwColorValue = color_rgb_to_rgbw(
                rgbColorValue[0],
                rgbColorValue[1],
                rgbColorValue[2]
            )
        else:
            rgbwColorValue[0:3] = rgbColorValue

        ## Convert all elements from float to integer
        rgbwColorValue = list(map(lambda x: int(x), rgbwColorValue))

        return rgbwColorValue

    def __sendCurrentState(self):

        ## TODO: do not send state until received update?

        _LOGGER.info("__sendCurrentState(): The state of light '%s' " + \
            "is send to device: " + \
            "state = %s, " + \
            "brightness = %s, " + \
            "transitionEffect = %s, " + \
            "color = %s",
            self._name,
            self.__state,
            self.__brightness,
            self.__transitionEffect,
            self.__rgbw
        )

        asbPacketData = (
            ASB_CMD_S_LIGHT,
            (0x01 if self.__state == True else 0x00),
            self.__brightness,
            self.__transitionEffect,
            self.__rgbw[0],
            self.__rgbw[1],
            self.__rgbw[2],
            self.__rgbw[3],
        )

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
