import hashlib
import base64
import os
import sys
from urllib.parse import urlparse, parse_qs
import requests

code_verifier = base64.urlsafe_b64encode(os.urandom(86)).rstrip(b"=")
code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier).digest()).rstrip(b"=").decode("utf-8")
state = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode("utf-8")

redirect_uri = "tesla://auth/callback"

print("Open this URL in a browser and sign in:")
print(
    "https://auth.tesla.com/oauth2/v3/authorize"
    f"?client_id=ownerapi"
    f"&code_challenge={code_challenge}"
    "&code_challenge_method=S256"
    "&locale=en-US"
    "&prompt=login"
    f"&redirect_uri=tesla%3A%2F%2Fauth%2Fcallback"
    "&response_type=code"
    "&scope=openid+email+offline_access"
    f"&state={state}"
)
print()
print("After signing in, the browser will show an error page for 'tesla://'.")
print("Copy the full URL from the address bar (starts with 'tesla://') and paste it here:")
callback_url = input("URL: ").strip()

parsed = urlparse(callback_url)
params = parse_qs(parsed.query)

returned_state = params.get("state", [None])[0]
if returned_state != state:
    print("ERROR: CSRF state mismatch. Do not reuse the auth URL — run the script again.")
    sys.exit(1)

code = params.get("code", [None])[0]
if not code:
    print("ERROR: No 'code' found in callback URL.")
    sys.exit(1)

response = requests.post(
    "https://auth.tesla.com/oauth2/v3/token",
    json={
        "grant_type": "authorization_code",
        "client_id": "ownerapi",
        "code_verifier": code_verifier.decode("utf-8"),
        "code": code,
        "redirect_uri": redirect_uri,
    },
)
response.raise_for_status()

data = response.json()
print()
print("***** Access Token *****")
print(data["access_token"])
print()
print("***** Refresh Token *****")
print(data["refresh_token"])
