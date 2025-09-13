import sdl2
import time
import re
import pyautogui
import threading
import subprocess
import configparser
from functools import wraps
from pywinauto.application import Application


def get_config():
    global config
    if config is None:
        config = configparser.ConfigParser()
        config.read('config.ini')
    return config


detected_controllers: int = -1
config: configparser.ConfigParser = None
CONTROLLER_LIMIT: int = get_config().getint(
    'general', 'controller_limit', fallback=4)
PAUSE_WHEN_NO_CONTROLLERS: bool = get_config().getboolean(
    'general', 'pause_when_no_controllers', fallback=False)


def failsafe_wrap(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except pyautogui.FailSafeException:
                print(
                    "PyAutoGUI failsafe triggered! Waiting for mouse to leave corner...")
                while pyautogui.position() in pyautogui.FAILSAFE_POINTS:
                    time.sleep(0.5)
                print("Failsafe cleared. Resuming automation.")
    return wrapper


@failsafe_wrap
def get_controllers():
    sdl2.SDL_Init(sdl2.SDL_INIT_GAMECONTROLLER)
    num_joysticks = sdl2.SDL_NumJoysticks()
    if num_joysticks == 0:
        sdl2.SDL_Quit()
        return []
    name_counts = {}
    names = []
    for i in range(num_joysticks):
        name_ptr = sdl2.SDL_JoystickNameForIndex(i)
        if name_ptr:
            name = name_ptr.decode("utf-8")
        else:
            name = "Unknown"
        count = name_counts.get(name, 0)
        names.append(f"{name} {count}")
        name_counts[name] = count + 1
    sdl2.SDL_Quit()
    return names


@failsafe_wrap
def pause_emulator():
    pyautogui.press('f4')


@failsafe_wrap
def open_controller_settings():
    pyautogui.press('alt', interval=0.1)
    pyautogui.press('right', interval=0.1)
    pyautogui.press('down', interval=0.1)
    pyautogui.press('f', interval=0.1)
    time.sleep(2)
    pyautogui.keyDown('shift')
    pyautogui.press('tab', presses=2, interval=0.1)
    pyautogui.keyUp('shift')
    pyautogui.typewrite('cc', interval=0.5)
    pyautogui.press('tab', interval=0.1)


@failsafe_wrap
def set_controller(controller: str):
    controller_name, controller_index = controller.rsplit(' ', 1)
    pyautogui.press('tab', presses=6, interval=0.1)
    pyautogui.typewrite('a', interval=0.1)
    time.sleep(0.5)
    pyautogui.typewrite(controller_name[:5], interval=0.1)
    pyautogui.press('down', presses=int(controller_index), interval=0.1)
    pyautogui.press('enter', interval=0.1)
    time.sleep(0.1)
    pyautogui.keyDown('shift')
    pyautogui.press('tab', presses=6, interval=0.1)
    pyautogui.keyUp('shift')
    pyautogui.press('right', interval=0.1)


@failsafe_wrap
def parse_line(line):
    # Example: [2024-06-01 12:34:56] user#1234 connected.
    m = re.search(r"\]\s(.+#\d+)", line)
    if not m:
        return
    user = m.group(1)
    if line.strip().endswith("is trying to connect to your computer."):
        parsec_accept_all(user)


@failsafe_wrap
def parsec_accept_all_every_x_secs():
    while True:
        parsec_accept_all()
        time.sleep(5)


@failsafe_wrap
def parsec_accept_all():
    pyautogui.hotkey('ctrl', 'f1')


@failsafe_wrap
def toggle_fullscreen():
    time.sleep(0.5)
    pyautogui.press('f11')
    time.sleep(0.5)


@failsafe_wrap
def exit_controller_setup():
    pyautogui.press('tab', interval=0.1)
    pyautogui.press('space', interval=0.1)


@failsafe_wrap
def open_bluetooth_settings():
    subprocess.Popen("start ms-settings:bluetooth", shell=True)
    time.sleep(3)  # give time to open


@failsafe_wrap
def pair_pro_controller():
    open_bluetooth_settings()

    # Connect to Settings by class instead of title
    app = Application(backend="uia").connect(
        class_name="ApplicationFrameWindow")
    dlg = app.window(class_name="ApplicationFrameWindow")

    print("✅ Connected to Settings window")
    # Try printing children to explore
    print(dlg.print_control_identifiers())


def new_func():
    global detected_controllers
    while True:
        # perform controller detectiona and emulator handling
        controllers = get_controllers()
        if detected_controllers == len(controllers):
            time.sleep(5)
            continue
        if len(controllers) == 0:
            if detected_controllers != len(controllers):
                print("No SDL controllers detected to set up.")
                if PAUSE_WHEN_NO_CONTROLLERS:
                    pause_emulator()
        else:
            if len(controllers) > (detected_controllers if detected_controllers is not None else 0):
                print(f"Detected {len(controllers)} controllers")
                if detected_controllers or not PAUSE_WHEN_NO_CONTROLLERS:
                    pause_emulator()
                toggle_fullscreen()
                open_controller_settings()
                for i, controller in enumerate(controllers):
                    if i + 1 > CONTROLLER_LIMIT:
                        break
                    print(f"Using GUID: {controller}")
                    set_controller(controller)
                exit_controller_setup()
                pause_emulator()
                toggle_fullscreen()
        detected_controllers = len(controllers)
        time.sleep(1)


if __name__ == "__main__":
    # threading.Thread(target=pair_pro_controller, daemon=True).start()
    threading.Thread(target=parsec_accept_all_every_x_secs,
                     daemon=True).start()
    time.sleep(2)
    new_func()
