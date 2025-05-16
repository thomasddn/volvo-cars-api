# Volvo Cars API

This python library lets you use the [Volvo Cars API](https://developer.volvocars.com/apis/). Authorisation follows the OAuth 2.0 authorisation code flow with PKCE.


[![GitHub release][releases-shield]][releases]
[![Sponsor][sponsor-shield]](#sponsor)

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
api = VolvoCarsApi(client_session, auth, api_key, vin)

# Make API request
engine_warnings = await api.async_get_engine_warnings()
```

<a name="sponsor"></a>

## 🚗 Powered by dreams

If you'd like to show your appreciation for this project, feel free to toss a coin to your dev. Donations help keep things running — and who knows, maybe one day they'll add up to a Volvo EX90 (hey, let me dream!). If you're feeling generous, you may donate one too — I'll even come pick it up! 😁

[![ko-fi sponsor][kofi-sponsor-shield]][kofi-sponsor]
[![github sponsor][github-sponsor-shield]][github-sponsor]


[releases-shield]: https://img.shields.io/github/v/release/thomasddn/volvo-cars-api?style=flat-square
[releases]: https://github.com/thomasddn/volvo-cars-api/releases
[sponsor-shield]: https://img.shields.io/static/v1?label=sponsor&message=%E2%9D%A4&color=%23fe8e86&style=flat-square
[kofi-sponsor-shield]: https://img.shields.io/badge/Support_me_on_Ko--fi-%E2%9D%A4-fe8e86?style=for-the-badge&logo=kofi&logoColor=ffffff
[kofi-sponsor]: https://ko-fi.com/N4N7UZ6KN
[github-sponsor-shield]: https://img.shields.io/badge/Support_me_on_GitHub-%E2%9D%A4-fe8e86?style=for-the-badge&logo=github&color=fe8e86
[github-sponsor]: https://github.com/sponsors/thomasddn
