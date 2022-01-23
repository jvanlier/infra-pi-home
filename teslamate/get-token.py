import os
import hashlib
import base64
import requests

code_verifier = base64.urlsafe_b64encode(os.urandom(86)).rstrip(b"=")
code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier).digest()).rstrip(b"=").decode("utf-8")
state = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode("utf-8")

headers = {
    "User-Agent": "",
    "x-tesla-user-agent": "",
    "X-Requested-With": "com.teslamotors.tesla",
}


print("Open link in browser and sign in:")
print(
    "https://auth.tesla.com/oauth2/v3/authorize?audience=https%3A%2F%2Fownership.tesla.com%2F"
    f"&client_id=ownerapi&code_challenge={code_challenge}"
    "&code_challenge_method=S256"
    "&locale=en-US"
    "&prompt=login"
    "&redirect_uri=https%3A%2F%2Fauth.tesla.com%2Fvoid%2Fcallback"
    "&response_type=code&scope=openid+email+offline_access"
    f"&state={state}"
)

print("After authentication, you'll get a code in the URL. Paste it here:")
code = input("Code: ")

data = {
    "grant_type": "authorization_code",
    "client_id": "ownerapi",
    "code_verifier": code_verifier.decode("utf-8"),
    "code": code,
    "redirect_uri": "https://auth.tesla.com/void/callback",
}

session = requests.Session()
response = session.post("https://auth.tesla.com/oauth2/v3/token", headers=headers, json=data)
response.raise_for_status()

print("")
print("***** Your access_token is *****")
print("")
access_token = response.json()["access_token"]
print(access_token)
print("")
print("***** Your refresh_token is *****")
print("")
refresh_token = response.json()["refresh_token"]
print(refresh_token)
