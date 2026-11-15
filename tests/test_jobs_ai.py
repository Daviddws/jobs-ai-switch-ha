"""Jobs AI Switch in a real Home Assistant, against a mocked Jobs server."""

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.jobs_ai.const import CONF_NOTIFY, CONF_SECRET, CONF_URL, DOMAIN

URL = "https://crew.example.com"
API = f"{URL}/api/ai-switch"
OFF = {"inUse": True, "on": False, "until": None, "secondsLeft": 0, "asked": None, "denied": False}
ON = {**OFF, "on": True, "until": "2026-11-14T15:15:00.000Z", "secondsLeft": 900}
ASKED = {**OFF, "asked": {"at": "2026-11-14T15:00:00.000Z", "by": "David"}}


def answer(mock: AiohttpClientMocker, state: dict, post: dict | None = None) -> None:
    mock.clear_requests()
    mock.get(API, json=state)
    mock.post(API, json=post or ON)


async def setup(hass: HomeAssistant, mock: AiohttpClientMocker, state: dict, phone: str = "mobile_app_fold") -> MockConfigEntry:
    answer(mock, state)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: URL, CONF_SECRET: "s3cret", CONF_NOTIFY: phone}, unique_id=URL)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def phone_calls(hass: HomeAssistant) -> list[ServiceCall]:
    calls: list[ServiceCall] = []

    async def record(call: ServiceCall) -> None:
        calls.append(call)

    hass.services.async_register("notify", "mobile_app_fold", record)
    return calls


async def test_setup_form(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """The form checks the secret against Jobs before saving."""
    calls = phone_calls(hass)
    del calls
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    aioclient_mock.get(API, status=401)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL, CONF_SECRET: "wrong", CONF_NOTIFY: "mobile_app_fold"})
    assert result["errors"] == {"base": "invalid_auth"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(API, status=404)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL, CONF_SECRET: "s3cret", CONF_NOTIFY: "mobile_app_fold"})
    assert result["errors"] == {"base": "no_switch"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(API, json=OFF)
    aioclient_mock.post(API, json=OFF)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL + "/", CONF_SECRET: "s3cret", CONF_NOTIFY: "mobile_app_fold"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_URL: URL, CONF_SECRET: "s3cret", CONF_NOTIFY: "mobile_app_fold"}
    # the secret goes in the header, never in the address
    _, url, _, headers = aioclient_mock.mock_calls[0]
    assert str(url) == API and headers["X-Ai-Switch-Secret"] == "s3cret"


async def test_switch(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """The switch follows Jobs, and turning it on asks for 15 minutes."""
    await setup(hass, aioclient_mock, OFF)
    assert hass.states.get("switch.jobs_ai_ai").state == "off"
    assert hass.states.get("sensor.jobs_ai_turns_off_at").state == "unknown"
    assert hass.states.get("binary_sensor.jobs_ai_ask_waiting").state == "off"

    answer(aioclient_mock, OFF, post=ON)
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.jobs_ai_ai"}, blocking=True)
    method, _, body, _ = aioclient_mock.mock_calls[-1]
    assert method == "POST" and body == {"on": True, "minutes": 15}
    assert hass.states.get("switch.jobs_ai_ai").state == "on"
    assert hass.states.get("sensor.jobs_ai_turns_off_at").state.startswith("2026-11-14T15:15:00")

    answer(aioclient_mock, ON, post=OFF)
    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.jobs_ai_ai"}, blocking=True)
    method, _, body, _ = aioclient_mock.mock_calls[-1]
    assert method == "POST" and body == {"on": False}
    assert hass.states.get("switch.jobs_ai_ai").state == "off"


async def test_ask_reaches_the_phone_and_approve(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """An ask from Jobs sends one alert with Approve / Deny; Approve turns AI on; the alert is cleared."""
    calls = phone_calls(hass)
    entry = await setup(hass, aioclient_mock, ASKED)
    assert hass.states.get("binary_sensor.jobs_ai_ask_waiting").state == "on"
    assert hass.states.get("binary_sensor.jobs_ai_ask_waiting").attributes["asked_by"] == "David"
    await hass.async_block_till_done()
    assert len(calls) == 1
    data = calls[0].data
    assert data["title"] == "Turn AI on in Jobs?"
    actions = [a["action"] for a in data["data"]["actions"]]
    assert actions == [f"JOBS_AI_APPROVE_{entry.entry_id}", f"JOBS_AI_DENY_{entry.entry_id}"]

    # the same ask on the next poll: no second alert
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert len(calls) == 1

    # an action meant for something else is ignored
    hass.bus.async_fire("mobile_app_notification_action", {"action": "SOMETHING_ELSE"})
    await hass.async_block_till_done()
    assert not any(c[0] == "POST" for c in aioclient_mock.mock_calls)

    # Approve on the phone: on for 15 minutes; the ask is gone, so the alert is cleared
    answer(aioclient_mock, ON, post=ON)
    hass.bus.async_fire("mobile_app_notification_action", {"action": actions[0]})
    await hass.async_block_till_done()
    posts = [c for c in aioclient_mock.mock_calls if c[0] == "POST"]
    assert posts and posts[0][2] == {"on": True, "minutes": 15}
    assert hass.states.get("switch.jobs_ai_ai").state == "on"
    assert calls[-1].data == {"message": "clear_notification", "data": {"tag": f"jobs_ai_{entry.entry_id}"}}


async def test_deny(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Deny on the phone answers no."""
    phone_calls(hass)
    entry = await setup(hass, aioclient_mock, ASKED)
    answer(aioclient_mock, {**OFF, "denied": True}, post={**OFF, "denied": True})
    hass.bus.async_fire("mobile_app_notification_action", {"action": f"JOBS_AI_DENY_{entry.entry_id}"})
    await hass.async_block_till_done()
    posts = [c for c in aioclient_mock.mock_calls if c[0] == "POST"]
    assert posts and posts[0][2] == {"deny": True}
    assert hass.states.get("binary_sensor.jobs_ai_ask_waiting").state == "off"


async def test_no_phone(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Without a phone picked, an ask just shows on the sensor."""
    await setup(hass, aioclient_mock, ASKED, phone="")
    assert hass.states.get("binary_sensor.jobs_ai_ask_waiting").state == "on"


async def test_secret_refused_starts_reauth(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """The secret changed on the server: Home Assistant asks for the new one."""
    entry = await setup(hass, aioclient_mock, OFF)
    aioclient_mock.clear_requests()
    aioclient_mock.get(API, status=401)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == config_entries.SOURCE_REAUTH for f in flows)
