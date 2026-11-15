# Jobs AI Switch

Turn AI on in the Jobs app from Home Assistant, 15 minutes at a time, and answer its "Ask to turn on" from your phone.

When `AI_SWITCH_SECRET` is set on the Jobs server, Jobs uses AI only while the switch is on. The Jobs server enforces this: it turns AI off after 15 minutes even if Home Assistant is down, and a restart turns it off too. This integration only tells Jobs "on", "off" or "deny".

## What you get

- **Jobs AI · AI** (switch): on gives AI for 15 minutes, and off ends it now. It follows the server, so it switches off by itself when the time runs out.
- **Jobs AI · Turns off at** (sensor): when it goes off, while it's on.
- **Jobs AI · Ask waiting** (binary sensor): on while an "Ask to turn on" from Jobs waits for an answer (5 minutes at most). Its attributes say who asked and when.
- **Jobs AI · Deny ask** (button).
- **A phone alert:** when you tap **Ask to turn on** in Jobs, the phone you picked gets "Turn AI on in Jobs?" with **Approve** and **Deny**. Approve turns the switch on.

Home Assistant asks Jobs every 10 seconds. Jobs never connects to Home Assistant.

## Set up

1. On the Jobs server, set `AI_SWITCH_SECRET` in `.env` to a long random value and restart the app.
2. In HACS, open the menu, choose **Custom repositories**, and add this repository as type **Integration**.
3. Download **Jobs AI Switch** and restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration** and choose **Jobs AI Switch**. Then:
   - Leave the address as `https://crew.dwsct.com`. That address reaches Jobs without Cloudflare Access, and the secret guards the switch.
   - Paste the secret.
   - Pick your phone. It needs the Home Assistant app.

To change the phone later, open the integration's **Configure**. If the secret changes on the server, Home Assistant asks for the new one.
