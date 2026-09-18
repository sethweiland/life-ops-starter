# Weather that helps you get ready

Enable a small **Before you head out** section on Home for umbrella, rain-jacket
and clothing cues. It uses the current forecast hour and the following eight
hourly points, including feels-like temperatures, precipitation and gusts. It
does not track you, read your calendar's locations, or send notifications.

A separate **This evening** row shows the feels-like range and a clothing cue for
6–10 p.m. in your configured timezone, so a morning check can help you pack a layer
for later. During that window it uses the remaining hours. At 10 p.m. it switches
to **Tomorrow evening**. Times show the available hourly forecast points, including
half-hour offsets where applicable. Missing evening coverage is labeled unavailable.
The same cached provider request includes 48 hours; no extra connection is needed.

## Choose a location privately

Location is specific to each installation. The shared starter has no default city;
another owner's choice never becomes yours. You can change the coordinates, label,
timezone and units below without editing application code. These are setup settings,
not a location picker in the dashboard.

1. In your private `config/tenant.yaml`, set `modules.weather: true`.
2. In your private `.env` or hosted environment, set `LIFE_OPS_WEATHER_LATITUDE`
   and `LIFE_OPS_WEATHER_LONGITUDE` to the approximate center of your city. Use
   signed decimal degrees: latitude from -90 to 90, longitude from -180 to 180.
   Do not use your street address or a live GPS position.
3. Optionally set `LIFE_OPS_WEATHER_LABEL` to a short name such as `My area` and
   `LIFE_OPS_WEATHER_UNITS` to `fahrenheit` (default) or `celsius`. Wind displays
   in mph or km/h respectively. Labels do not locate a city; coordinates do.
4. Set `human.timezone` in private tenant configuration to the timezone of that
   location. The display uses this timezone, including daylight-saving changes.
5. Restart, run `python scripts/check_setup.py --env-file .env`, then open Home.
   Confirm your location choice privately and compare a known forecast hour and
   the displayed end time with a local forecast. The offline checker cannot
   verify provider access or that you selected the intended city.

No weather API key is required for this connector. The app sends coordinates
rounded to two decimal places to the fixed Open-Meteo HTTPS endpoint, along with
requested forecast fields. The label, tenant configuration, calendar and account
credentials are not sent. The provider can see the server's IP address and the
approximate coordinates. Browser geolocation is never requested.

The connector uses Open-Meteo's free endpoint for personal non-commercial use.
Review the provider's [terms and limits](https://open-meteo.com/en/terms) before
enabling it. Commercial products require a suitable plan and a separately
implemented commercial connector; adding a key alone does not switch this code.
Attribution and the [data licence](https://open-meteo.com/en/licence) are available
under **Source** on the weather card. Life Ops's clothing rules are its own interpretation.

## What the cues mean

- **Umbrella:** upcoming hourly precipitation chance is at least 40%, modeled
  precipitation is at least 0.2 mm, or the weather code indicates rain.
- **Rain jacket:** wet weather coincides with gusts of at least 40 km/h (about
  25 mph). A hooded layer may be more practical than an umbrella.
- **Snow, freezing rain or thunderstorms:** distinct cues take priority over an
  umbrella suggestion. For storms, consult local alerts and plan shelter.
- **Clothing:** the lowest feels-like value in the window suggests a warm coat
  below 5°C, a jacket below 13°C, a light layer below 19°C, otherwise breathable
  clothing. A rise of at least 8°C suggests removable layers; a high of 28°C or
  more adds a warm-weather cue. These are starting preferences, not guarantees
  of comfort. A coding agent can adjust them in `src/core/weather.py`.

Wet-weather timing spans the first to last indicated period; rain may be
intermittent. The percentage is the **highest hourly** precipitation probability,
not the probability for the whole day. Snow also counts as precipitation.
Hourly accumulated precipitation and gusts describe the preceding hour; apparent
temperature and condition codes describe their hourly point. See the provider's
[forecast definitions](https://open-meteo.com/en/docs).

The card shows its covered windows and offers an expandable source credit.
It is not an official severe-weather alert or a substitute for checking local
conditions. No advice is shown when a response is missing data, malformed,
unavailable or no longer covers the upcoming hours.

## Loading, privacy and disconnecting

Home loads first; its authenticated `/api/weather` request retrieves the card
separately. Each worker caches successful forecasts for 20 minutes and failed
requests for one minute. Refreshing the page reuses that cache. The card refreshes
every 20 minutes while Home is visible, and when returning to a tab whose forecast
is due for refresh. Hidden tabs skip periodic requests; closing Home stops them.
Additional workers/restarts can make additional calls. Forecasts are held in memory and are not written to S3
or runtime files. Exceptions never show coordinates or provider response bodies.

If setup is missing, Home shows a setup message. If the service fails, check
another forecast and retry after a minute; expired clothing advice is not reused.
In a restricted environment, allow outbound HTTPS to `api.open-meteo.com` only
if you choose to enable this connection. Disabling JavaScript leaves a link to
the authenticated summary.

**Disconnect:** set `modules.weather: false`, remove the optional weather
environment variables and restart all workers. Both Home and the weather endpoint
then stop making forecast requests. Disabling this module never affects Projects,
Spend, the calendar or stored records.
