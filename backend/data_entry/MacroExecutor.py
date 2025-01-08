import pyautogui
import time
import clipboard


def click(position):
    """
    Simulate a mouse click at the specified position.

    Args:
        position (list): [x, y] coordinates on the screen.
    """
    pyautogui.click(x=position[0], y=position[1])

def type_text(text, data):
    """
    Simulate typing text.

    Args:
        text (str): Text to type. Supports placeholders in {field_name} format.
    """
    resolved_text = text.format(data)
    pyautogui.typewrite(resolved_text)

def paste_field(data):
    """
    Paste the value of a specific field using the clipboard.

    Args:
        field (str): Name of the field to paste.
    """
    clipboard.copy(data)
    pyautogui.hotkey("ctrl", "v")

def wait(duration):
    """
    Pause execution for a specified duration.

    Args:
        duration (float): Time to wait in seconds.
    """

    time.sleep(duration)

def key(key):
    """
    Press a specific key.

    Args:
        key (str): Key to press.
    """
    pyautogui.press(key)