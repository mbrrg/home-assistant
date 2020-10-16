"""Support for Vanderbilt (formerly Siemens) SPC alarm systems."""
from pyspcwebgw.const import AreaMode

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
    SUPPORT_ALARM_ARM_NIGHT,
)
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import DOMAIN as SPC_DOMAIN, SIGNAL_UPDATE_ALARM


def _get_alarm_state(area):
    """Get the alarm state."""

    if area.verified_alarm:
        return STATE_ALARM_TRIGGERED

    mode_to_state = {
        AreaMode.UNSET: STATE_ALARM_DISARMED,
        AreaMode.PART_SET_A: STATE_ALARM_ARMED_HOME,
        AreaMode.PART_SET_B: STATE_ALARM_ARMED_NIGHT,
        AreaMode.FULL_SET: STATE_ALARM_ARMED_AWAY,
    }
    return mode_to_state.get(area.mode)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up platform."""
    client = hass.data[SPC_DOMAIN][entry.entry_id]
    async_add_entities(
        [SpcAlarm(area=area, client=client) for area in client.areas.values()]
    )


class SpcAlarm(alarm.AlarmControlPanelEntity):
    """Representation of the SPC alarm panel."""

    def __init__(self, area, client):
        """Initialize the SPC alarm panel."""
        self._area = area
        self._client = client

    async def async_added_to_hass(self):
        """Call for adding new entities."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ALARM.format(self._area.id),
                self._update_callback,
            )
        )

    @property
    def unique_id(self) -> str:
        """Get the unique identifier of the device."""
        serial = self._client.info["sn"]
        return f"{serial}-{self._area.id}"

    @property
    def device_info(self):
        """Provide device info."""
        return {
            "identifiers": {(SPC_DOMAIN, self.unique_id)},
            "name": self._area.name,
            "manufacturer": "Vanderbilt",
            "model": f"SPC {self._client.info['variant']}",
        }

    @callback
    def _update_callback(self):
        """Call update method."""
        self.async_schedule_update_ha_state(True)

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the device."""
        return self._area.name

    @property
    def changed_by(self):
        """Return the user the last change was triggered by."""
        return self._area.last_changed_by

    @property
    def state(self):
        """Return the state of the device."""
        return _get_alarm_state(self._area)

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_AWAY | SUPPORT_ALARM_ARM_NIGHT

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""

        await self._client.change_mode(area=self._area, new_mode=AreaMode.UNSET)

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""

        await self._client.change_mode(area=self._area, new_mode=AreaMode.PART_SET_A)

    async def async_alarm_arm_night(self, code=None):
        """Send arm home command."""

        await self._client.change_mode(area=self._area, new_mode=AreaMode.PART_SET_B)

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""

        await self._client.change_mode(area=self._area, new_mode=AreaMode.FULL_SET)
