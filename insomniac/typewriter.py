import insomniac
from insomniac.globals import is_insomniac
from insomniac.utils import *

# Typewriter uses Android application (apk file) built from this repo: https://github.com/alexal1/InsomniacAutomator
# It provides IME (Input Method Editor) that replaces virtual keyboard with it's own one, which listens to specific
# broadcast messages and simulates key presses.
ADB_KEYBOARD_PKG = "com.alexal1.adbkeyboard"
ADB_KEYBOARD_IME = "com.alexal1.adbkeyboard/.AdbIME"
ADB_KEYBOARD_APK = "ADBKeyboard.apk"
ADB_KEYBOARD_APK_NOMIX = "ADBKeyboard-nomix.apk"
ADB_KEYBOARD_VERSION = versiontuple("3.0.2")
DELAY_MEAN = 180
DELAY_DEVIATION = 80
TYPO_CHANCE = 0.04
IME_MESSAGE_B64 = "ADB_INPUT_B64"
IME_CLEAR_TEXT = "ADB_CLEAR_TEXT"
EXTRA_MESSAGE = "msg"
EXTRA_DELAY_MEAN = "delay_mean"
EXTRA_DELAY_DEVIATION = "delay_deviation"


class Typewriter:
    is_adb_keyboard_set = False
    device_id = None

    def __init__(self, device_id):
        self.is_adb_keyboard_set = False
        self.device_id = device_id

    def set_adb_keyboard(self):
        need_to_install_apk = False
        if self._is_adb_ime_existing():
            # Check version and update if needed
            stream = os.popen("adb" + ("" if self.device_id is None else " -s " + self.device_id) +
                              f" shell dumpsys package {ADB_KEYBOARD_PKG}")
            output = stream.read()
            stream.close()
            version_match = re.findall('versionName=(\\S+)', output)
            if len(version_match) == 1 and versiontuple(version_match[0]) >= ADB_KEYBOARD_VERSION:
                print_debug("ADB Keyboard version is good")
            else:
                need_to_install_apk = True
        else:
            need_to_install_apk = True

        if need_to_install_apk:
            print("Installing ADB Keyboard to enable typewriting...")
            adb_keybpard_apk = ADB_KEYBOARD_APK if is_insomniac() else ADB_KEYBOARD_APK_NOMIX
            apk_path = os.path.join(os.path.dirname(os.path.abspath(insomniac.__file__)), "assets", adb_keybpard_apk)
            os.popen("adb" + ("" if self.device_id is None else " -s " + self.device_id)
                     + f' install "{apk_path}"').close()
        self.is_adb_keyboard_set = self._set_adb_ime()
        if not self.is_adb_keyboard_set:
            print(COLOR_FAIL + "Cannot setup ADB Keyboard. Don't worry! Fallback to text copy-pasting will be used."
                  + COLOR_ENDC)

    def write(self, view, text) -> bool:
        if not self.is_adb_keyboard_set:
            return False
        if not view.is_focused():
            view.click()
        if not self.clear():
            return False

        import random as _rnd
        typed_len = 0
        for i, char in enumerate(text):
            # 4% chance to type wrong char then delete (letters only)
            if _rnd.random() < TYPO_CHANCE and char.isalpha():
                wrong = _rnd.choice("abcdefghijklmnopqrstuvwxyz")
                self._type_char(wrong)
                sleep(_rnd.gauss(0.18, 0.05))
                self._send_broadcast(IME_CLEAR_TEXT)
                sleep(_rnd.gauss(0.12, 0.03))
                self._type_char(char)
            else:
                self._type_char(char)

            # Variable delay per character
            delay = max(0.04, _rnd.gauss(DELAY_MEAN / 1000.0, DELAY_DEVIATION / 1000.0))
            # Consecutive digits are faster (phone numbers, codes)
            if char.isdigit() and i > 0 and text[i - 1].isdigit():
                delay *= 0.6
            # Uppercase is slightly slower
            if char.isupper():
                delay += _rnd.uniform(0.03, 0.08)
            # 8% chance of a longer pause (thinking)
            if _rnd.random() < 0.08:
                delay += _rnd.uniform(0.3, 0.8)
            sleep(delay)
            typed_len += 1

        return True

    def _type_char(self, char):
        char_b64 = base64.b64encode(char.encode('utf-8')).decode('utf-8')
        extras = {EXTRA_MESSAGE: char_b64, EXTRA_DELAY_MEAN: 0, EXTRA_DELAY_DEVIATION: 0}
        self._send_broadcast(IME_MESSAGE_B64, extras)

    def clear(self) -> bool:
        if not self.is_adb_keyboard_set:
            return False
        self._send_broadcast(IME_CLEAR_TEXT)
        return True

    def _set_adb_ime(self):
        attempts_count = 0
        while not self._is_adb_ime_existing():
            attempts_count += 1
            if attempts_count == 5:
                return False
            sleep(2)
        stream = os.popen("adb" + ("" if self.device_id is None else " -s " + self.device_id)
                          + f" shell ime set {ADB_KEYBOARD_IME}")
        output = stream.read()
        succeed = "selected" in output
        stream.close()
        return succeed

    def _is_adb_ime_existing(self):
        stream = os.popen("adb" + ("" if self.device_id is None else " -s " + self.device_id) + " shell ime list -a")
        output = stream.read()
        result = ADB_KEYBOARD_IME in output
        stream.close()
        return result

    def _send_broadcast(self, action, extras=None):
        command = "adb" + ("" if self.device_id is None else " -s " + self.device_id) \
                  + f" shell am broadcast -a {action}"
        if extras is not None:
            for key, value in extras.items():
                if isinstance(value, str):
                    command += f" --es {key} '{value}'"
                elif isinstance(value, int):
                    command += f" --ei {key} {value}"
                else:
                    print_debug(COLOR_FAIL + f"Unexpected broadcast extra: {value}" + COLOR_ENDC)
                    continue
        os.popen(command).close()
