# Registration API — email code, phone number, SMS code, captcha
# Integrates with: mail_api (Outlook), firefox_sms (火狐狸), 2captcha
import json
import re
import time
import base64
from typing import Optional

from insomniac import network, HTTP_OK
from insomniac.sleeper import sleeper
from insomniac.utils import *

# ── Config ──

MAIL_API_URL = "http://127.0.0.1:9700"
HELPER_API_URL = "http://127.0.0.1:18234"
CAPTCHA_API_KEY = "REMOVED_KEY"

SMS_PROJECT_ID = 1001
SMS_COUNTRY = "HK"
SMS_POLL_TIMEOUT = 300
EMAIL_POLL_TIMEOUT = 120

CAPTCHA_SUBMIT_URL = "http://2captcha.com/in.php"
CAPTCHA_RESULT_URL = "http://2captcha.com/res.php"
CAPTCHA_POLL_TIMEOUT = 120


class PhoneNumberData:
    response_id = None
    country_code = None
    phone_number = None
    pkey = None

    def __init__(self, response_id, country_code, phone_number, pkey=None):
        self.response_id = response_id
        self.country_code = country_code
        self.phone_number = phone_number
        self.pkey = pkey


# ── Email Code (via mail_api) ──

def get_email_code(email, timeout=EMAIL_POLL_TIMEOUT) -> Optional[str]:
    """Poll mail API for 6-digit Instagram verification code."""
    print(f"Polling email code for {email} (timeout {timeout}s)...")
    try:
        import httpx
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                resp = httpx.get(
                    f"{MAIL_API_URL}/api/mail-new",
                    params={"email": email, "mailbox": "INBOX"},
                    timeout=15,
                )
                data = resp.json()
                if data.get("code"):
                    c = str(data["code"])
                    if re.match(r"^\d{6}$", c):
                        print(COLOR_OKGREEN + f"Email code: {c}" + COLOR_ENDC)
                        return c
                body = data.get("body", "") or data.get("text", "") or ""
                match = re.search(r"\b(\d{6})\b", body)
                if match:
                    code = match.group(1)
                    print(COLOR_OKGREEN + f"Email code: {code}" + COLOR_ENDC)
                    return code
            except Exception as e:
                print(f"Email poll error: {e}")
            time.sleep(5)
    except ImportError:
        print(COLOR_FAIL + "httpx not installed, falling back to manual input" + COLOR_ENDC)
        return input(f"Enter the 6-digit code sent to {email}: ")

    print(COLOR_FAIL + "Email code timeout" + COLOR_ENDC)
    return None


# ── Phone Number (via helper_server / 火狐狸) ──

def get_phone_number() -> Optional[PhoneNumberData]:
    """Get a phone number from firefox_sms via helper server."""
    print("Getting phone number from SMS platform...")
    try:
        import httpx
        resp = httpx.post(
            f"{HELPER_API_URL}/sms/phone",
            params={"project_id": SMS_PROJECT_ID, "country": SMS_COUNTRY},
            timeout=30,
        )
        data = resp.json()
        if data.get("phone"):
            phone = str(data["phone"])
            pkey = data.get("pkey", "")
            country_code = data.get("country_code", SMS_COUNTRY)
            print(COLOR_OKGREEN + f"Got phone: +{country_code} {phone}" + COLOR_ENDC)
            return PhoneNumberData(
                response_id=pkey,
                country_code=country_code,
                phone_number=phone,
                pkey=pkey,
            )
        print(COLOR_FAIL + f"SMS platform error: {data}" + COLOR_ENDC)
    except ImportError:
        print(COLOR_FAIL + "httpx not installed, falling back to manual input" + COLOR_ENDC)
        return _get_phone_number_simple()
    except Exception as e:
        print(COLOR_FAIL + f"SMS platform error: {e}" + COLOR_ENDC)
        return _get_phone_number_simple()
    return None


# ── SMS Code (via helper_server / 火狐狸) ──

def get_confirmation_code(response_id, timeout=SMS_POLL_TIMEOUT) -> Optional[str]:
    """Wait for SMS code via helper server."""
    if not response_id:
        return input("Enter SMS confirmation code: ")
    print(f"Waiting for SMS code (pkey={response_id}, timeout={timeout}s)...")
    try:
        import httpx
        resp = httpx.post(
            f"{HELPER_API_URL}/sms/code",
            json={"pkey": str(response_id), "timeout": timeout},
            timeout=timeout + 30,
        )
        data = resp.json()
        code = data.get("code")
        if code:
            print(COLOR_OKGREEN + f"SMS code: {code}" + COLOR_ENDC)
            return str(code)
        print(COLOR_FAIL + f"SMS code error: {data.get('error', 'unknown')}" + COLOR_ENDC)
    except ImportError:
        return input("Enter SMS confirmation code: ")
    except Exception as e:
        print(COLOR_FAIL + f"SMS code error: {e}" + COLOR_ENDC)
    return None


# ── Captcha (via 2Captcha) ──

def solve_captcha(img_bytes: bytes, timeout=CAPTCHA_POLL_TIMEOUT) -> Optional[str]:
    """Solve image captcha via 2Captcha API."""
    print("Submitting captcha to 2Captcha...")
    try:
        import httpx
        client = httpx.Client(timeout=30)
        img_b64 = base64.b64encode(img_bytes).decode()

        resp = client.post(CAPTCHA_SUBMIT_URL, data={
            "key": CAPTCHA_API_KEY,
            "method": "base64",
            "body": img_b64,
            "json": "1",
            "minLen": "6",
            "maxLen": "6",
            "numeric": "1",
        })
        result = resp.json()
        if result.get("status") != 1:
            print(COLOR_FAIL + f"2Captcha submit failed: {result}" + COLOR_ENDC)
            return None

        request_id = result["request"]
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            time.sleep(5)
            resp = client.get(CAPTCHA_RESULT_URL, params={
                "key": CAPTCHA_API_KEY,
                "action": "get",
                "id": request_id,
                "json": "1",
            })
            result = resp.json()
            if result.get("status") == 1:
                code = result["request"]
                print(COLOR_OKGREEN + f"Captcha solved: {code}" + COLOR_ENDC)
                return code

        print(COLOR_FAIL + f"Captcha timeout after {timeout}s" + COLOR_ENDC)
    except ImportError:
        print(COLOR_FAIL + "httpx not installed" + COLOR_ENDC)
    except Exception as e:
        print(COLOR_FAIL + f"Captcha error: {e}" + COLOR_ENDC)
    return None


# ── Fallback: manual input ──

def _get_phone_number_simple() -> Optional[PhoneNumberData]:
    data = PhoneNumberData(0, None, None)
    while data.country_code is None or data.phone_number is None:
        user_input = input('Enter mobile phone (format "+852 12345678"): ')
        try:
            data.country_code, data.phone_number = user_input.split(' ')
        except ValueError:
            continue
        if data.country_code[0] != '+':
            data.country_code = None
    return data
