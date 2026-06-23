import random
from typing import Optional

from insomniac.extra_features.actions_impl import airplane_mode_on_off
from insomniac.extra_features.utils import new_identity
from insomniac.navigation import close_instagram_and_system_dialogs
from insomniac.sleeper import sleeper
from insomniac.utils import *
from insomniac.views import TabBarView, TabBarTabs, LanguageNotEnglishException
from registration.api import get_email_code, get_phone_number, get_confirmation_code


class UserData:
    email = None
    full_name = None
    password = None
    username = None


def register_accounts(device_wrapper,
                      users_file_path,
                      session_state,
                      on_action):
    device = device_wrapper.get()
    device_id = device_wrapper.device_id
    app_id = device_wrapper.app_id

    sleeper.random_sleep(multiplier=2.0)

    user_data = _get_user_data(users_file_path)
    if user_data is None:
        print(COLOR_FAIL + f"No more not registered users in {users_file_path}!" + COLOR_ENDC)
        return

    # Step 1: Click "Create new account"
    print("Step 1: Click 'Create new account'")
    create_btn = device.find(descriptionMatches="(?i)create new account")
    if not create_btn.exists():
        print("Clearing Instagram data to get login page...")
        clear_instagram_data(device_id, app_id)
        open_instagram(device_id, app_id)
        sleeper.random_sleep(multiplier=3.0)
        create_btn = device.find(descriptionMatches="(?i)create new account")
    if not create_btn.exists():
        print(COLOR_FAIL + "Cannot find 'Create new account' button!" + COLOR_ENDC)
        return
    create_btn.click()
    sleeper.random_sleep()

    # Step 2: Choose email registration
    print("Step 2: Choose email registration")
    email_btn = device.find(descriptionMatches="(?i)sign up with email")
    if email_btn.exists():
        email_btn.click()
        sleeper.random_sleep()
    else:
        print("No 'Sign up with email' button, might already be on email page")

    # Step 3: Enter email
    print(f"Step 3: Enter email: {user_data.email}")
    email_input = device.find(className="android.widget.EditText",
                               descriptionMatches="(?i)email")
    if not email_input.exists():
        print(COLOR_FAIL + "Cannot find email input!" + COLOR_ENDC)
        return
    email_input.click()
    email_input.set_text(user_data.email)
    sleeper.random_sleep()
    _click_next(device)
    sleeper.random_sleep(multiplier=2.0)

    # Step 4: Email confirmation code
    print("Step 4: Waiting for email confirmation code...")
    email_code = get_email_code(user_data.email)
    if email_code is None:
        print(COLOR_FAIL + "Cannot get email confirmation code!" + COLOR_ENDC)
        return
    code_input = device.find(className="android.widget.EditText",
                              descriptionMatches="(?i)code")
    if not code_input.exists():
        code_input = device.find(className="android.widget.EditText")
    code_input.click()
    code_input.set_text(email_code)
    sleeper.random_sleep()
    _click_next(device)
    sleeper.random_sleep()

    # Step 5: Create password
    print(f"Step 5: Create password")
    password_input = device.find(className="android.widget.EditText",
                                  descriptionMatches="(?i)password")
    if password_input.exists():
        password_input.click()
        password_input.set_text(user_data.password)
        sleeper.random_sleep()
        _click_next(device)
        sleeper.random_sleep()

    # Step 6: Birthday
    print("Step 6: Set birthday")
    _set_birthday(device)
    sleeper.random_sleep()

    # Step 7: Full name
    print(f"Step 7: Enter full name: {user_data.full_name}")
    name_input = device.find(className="android.widget.EditText",
                              descriptionMatches="(?i)full name")
    if name_input.exists():
        name_input.click()
        name_input.set_text(user_data.full_name)
        sleeper.random_sleep()
        _click_next(device)
        sleeper.random_sleep()

    # Step 8: Username
    print(f"Step 8: Set username")
    username_input = device.find(className="android.widget.EditText",
                                  descriptionMatches="(?i)username")
    if username_input.exists() and user_data.username:
        username_input.click()
        username_input.clear_text()
        username_input.set_text(user_data.username)
        sleeper.random_sleep()
    _click_next(device)
    sleeper.random_sleep(multiplier=2.0)

    # Step 9: Agree to terms
    print("Step 9: Agree to terms")
    agree_btn = device.find(descriptionMatches="(?i)i agree")
    if agree_btn.exists():
        agree_btn.click()
        sleeper.random_sleep(multiplier=3.0)

    # Step 10: Captcha
    print("Step 10: Captcha verification")
    continue_btn = device.find(descriptionMatches="(?i)^continue$")
    if continue_btn.exists():
        continue_btn.click()
        sleeper.random_sleep(multiplier=3.0)
    # ponytail: captcha solving needs external service, skip for now
    captcha_input = device.find(className="android.widget.EditText",
                                 textMatches="(?i).*enter.*code.*")
    if captcha_input.exists():
        print(COLOR_FAIL + "Captcha detected! Manual intervention needed." + COLOR_ENDC)
        print("Please solve the captcha manually and press Next.")
        input("Press ENTER after solving captcha...")
    _click_next(device)
    sleeper.random_sleep(multiplier=2.0)

    # Step 11: Phone number
    print("Step 11: Enter phone number")
    phone_number_data = get_phone_number()
    if phone_number_data is None:
        print(COLOR_FAIL + "Cannot get phone number!" + COLOR_ENDC)
        return
    phone_input = device.find(className="android.widget.EditText",
                               textMatches="(?i)phone number")
    if not phone_input.exists():
        phone_input = device.find(className="android.widget.EditText",
                                   descriptionMatches="(?i)phone")
    if phone_input.exists():
        # Set country code if needed
        country_btn = device.find(descriptionMatches="(?i).*\\+\\d+.*")
        if country_btn.exists() and phone_number_data.country_code:
            country_btn.click()
            sleeper.random_sleep()
            search = device.find(className="android.widget.EditText")
            if search.exists():
                search.set_text(phone_number_data.country_code)
                sleeper.random_sleep()
                first_item = device.find(className="android.widget.TextView",
                                          textMatches=f".*{phone_number_data.country_code}.*")
                if first_item.exists():
                    first_item.click()
                    sleeper.random_sleep()
        phone_input.click()
        phone_input.set_text(phone_number_data.phone_number)
        sleeper.random_sleep()

    send_code_btn = device.find(descriptionMatches="(?i)send code")
    if send_code_btn.exists():
        send_code_btn.click()
        sleeper.random_sleep(multiplier=3.0)

    # Step 12: SMS verification
    print("Step 12: SMS verification")
    # Switch from WhatsApp to SMS if needed
    sms_btn = device.find(descriptionMatches="(?i)send code via sms")
    if sms_btn.exists():
        print("Switching from WhatsApp to SMS...")
        sms_btn.click()
        sleeper.random_sleep(multiplier=2.0)

    sms_code = get_confirmation_code(phone_number_data.response_id)
    if sms_code is None:
        print(COLOR_FAIL + "Cannot get SMS confirmation code!" + COLOR_ENDC)
        return
    sms_input = device.find(className="android.widget.EditText",
                             textMatches="(?i).*digit code.*")
    if not sms_input.exists():
        sms_input = device.find(className="android.widget.EditText")
    if sms_input.exists():
        sms_input.click()
        sms_input.set_text(sms_code)
        sleeper.random_sleep()
    _click_next(device)
    sleeper.random_sleep(multiplier=5.0)

    # Skip any remaining dialogs
    print("Skipping remaining setup dialogs...")
    for _ in range(10):
        if not _skip(device):
            break

    if _is_succeed(device):
        print(COLOR_OKGREEN + "Registration successfully completed!" + COLOR_ENDC)
        _set_user_done(users_file_path)
    else:
        print(COLOR_FAIL + "Registration may have failed." + COLOR_ENDC)

    new_identity(device_id, app_id)
    sleeper.random_sleep(multiplier=2.0)
    close_instagram_and_system_dialogs(device)
    airplane_mode_on_off(device_wrapper)


def _click_next(device):
    next_btn = device.find(descriptionMatches="(?i)^next$")
    if next_btn.exists():
        next_btn.click()


def _set_birthday(device):
    # DatePicker dialog
    set_btn = device.find(resourceId="android:id/button1")
    if set_btn.exists():
        # DatePicker is shown, set year to make user 18+
        pickers = device.find(resourceId="android:id/numberpicker_input")
        if pickers.exists():
            # Year is the 3rd picker (instance=2)
            year_picker = device.find(resourceId="android:id/numberpicker_input", instance=2)
            if year_picker.exists():
                year_picker.long_click()
                year_picker.set_text(str(random.randint(1985, 2005)))
                device.close_keyboard()
                sleeper.random_sleep()
        set_btn.click()
        sleeper.random_sleep()

    # Birthday confirmation page
    next_btn = device.find(descriptionMatches="(?i)^next$")
    if next_btn.exists():
        next_btn.click()


def _skip(device) -> bool:
    sleeper.random_sleep()
    for desc in ["Skip", "Not now", "Close"]:
        btn = device.find(descriptionMatches=f"(?i)^{desc}$")
        if btn.exists(quick=True):
            print(f"Click '{desc}'")
            btn.click()
            return True
    for text in ["Skip", "Not Now", "Close", "OK"]:
        btn = device.find(text=text, clickable=True)
        if btn.exists(quick=True):
            print(f"Click '{text}'")
            btn.click()
            return True
    return False


def _is_succeed(device):
    try:
        TabBarView(device).navigate_to(TabBarTabs.PROFILE)
    except (LanguageNotEnglishException, Exception):
        print(COLOR_FAIL + "Cannot open newly created profile..." + COLOR_ENDC)
        return False
    return True


def _get_user_data(path) -> Optional[UserData]:
    with open(path, "r", encoding="utf-8") as file:
        lines = [line.rstrip() for line in file]
        for i, line in enumerate(lines):
            if i == 0:
                continue
            if "DONE" in line:
                continue
            parts = line.split(', ')
            user_data = UserData()
            if len(parts) >= 4:
                user_data.email, user_data.full_name, user_data.password, user_data.username = parts[:4]
            elif len(parts) == 3:
                user_data.full_name, user_data.password, user_data.username = parts
            return user_data


def _set_user_done(path):
    with open(path, "r+", encoding="utf-8") as file:
        lines = [line.rstrip() for line in file]
        for i, line in enumerate(lines):
            if i == 0:
                continue
            if "DONE" in line:
                continue
            lines[i] += " - DONE"
            break
        file.truncate(0)
        file.seek(0)
        file.write("\n".join(lines))
