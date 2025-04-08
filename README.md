# Volvo Cars API

This python library lets you use the [Volvo Cars API](https://developer.volvocars.com/apis/). Authorisation follows the OAuth 2.0 authorisation code flow with PKCE.


[![GitHub release][releases-shield]][releases]
[![Sponsor][sponsor-shield]][sponsor]

## Requirements

You'll need a Volvo Developers account and create an [API application](https://developer.volvocars.com/account/). Make sure to fill in all required fields and write down the retrieved client id and secret.

## Usage

A script is worth a thousand words.

```py
# Retrieved at the end of the API application registration process
client_id = "abc"
client_secret = "very-secret-key"

# Scopes that have been requested during the API application registration. You can also
# use less scopes than requested.
scopes = [
    "openid",
    "conve:battery_charge_level",
    "conve:brake_status",
    "conve:climatization_start_stop",
    "conve:command_accessibility",
    "conve:commands",
    "conve:diagnostics_engine_status",
    # ...
]

# Must be excactly as entered during the API application registration
redirect_uri = "htttps://my-volvo-application.io/callback" 

# The VCC API key retrieved after the API application registration process
api_key = "abcdef-1234567890-abcdef"

client_session = _get_client_session()

# Authenticate
auth = VolvoCarsAuth(
    client_session,
    client_id=client_id,
    client_secret=client_secret,
    scopes=scopes,
    redirect_uri=redirect_uri)
auth_uri = await auth.get_auth_uri() # optionally pass state

# Redirect user to auth_uri and wait for the callback
# ...

# Extract code from the callback url
code = _get_code_from_url()
await auth.async_request_token(code)

# The VIN must be linked to the account you sign in with
vin = "YV123456789012345"

# Create API client
api = VolvoCarsApi(client_session, auth, vin, api_key)

# Make API request
engine_warnings = await api.async_get_engine_warnings()
```

## 🥤 Powered by snacks

When I'm coding, I run on coffee, Coca-Cola*, and Lays* potato chips. If you'd like to show your appreciation for this project, consider making a small donation to help keep my stash stocked! (Note: I'm also happy to accept 1,000,000 USD — or EUR, I'm not picky. 😁)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/N4N7UZ6KN)

<sub><sub>\* No affiliation with these brands — just personal favorites!</sub></sub>


[releases-shield]: https://img.shields.io/github/v/release/thomasddn/volvo-cars-api?style=flat-square
[releases]: https://github.com/thomasddn/volvo-cars-api/releases
[sponsor-shield]: https://img.shields.io/static/v1?label=sponsor&message=%E2%9D%A4&color=%23fe8e86&style=flat-square
[sponsor]: https://ko-fi.com/N4N7UZ6KN
