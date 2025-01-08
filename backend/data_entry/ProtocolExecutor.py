import json
import pyautogui
import time
import clipboard
import platform
import subprocess
import ctypes
import traceback
from AppKit import NSWorkspace
from PyQt5.QtWidgets import QMessageBox

from backend.database.database import PatientRecord, DatabaseManager


class ProtocolExecutor:
    def __init__(self, protocol_path: str):
        """
        Initialize the ProtocolExecutor with the protocol path.

        Args:
            protocol_path (str): Path to the protocol JSON file.
        """
        self.protocol_path = protocol_path
        self.db_manager = DatabaseManager()

    def load_protocol(self):
        """
        Load the protocol from the JSON file.

        Returns:
            list: Loaded protocol steps.
        """
        with open(self.protocol_path, 'r') as file:
            protocol = json.load(file)
        return protocol.get("protocol", [])

    def execute_protocol(self, data: dict):
        """
        Execute the actions defined in the loaded protocol for a single data record.
        """
        protocol = self.load_protocol()
        for step in protocol:
            action = step.get("action")

            if action == "click":
                position = step.get("position")
                self.click(position)

            elif action == "paste":
                field = step.get("field")
                self.paste_field(field, data)

            elif action == "type":
                text = step.get("text", "")
                self.type_text(text, data)

            elif action == "key_press":
                key = step.get("key")
                self.key_press(key)

            elif action == "wait":
                duration = step.get("duration", 1)
                self.wait(duration)

            else:
                print(f"Unknown action: {action}")

    def click(self, position):
        """
        Simulate a mouse click at the specified position.
        """
        pyautogui.click(x=position[0], y=position[1])

    def paste_field(self, field, data):
        """
        Paste the value of a specific field using the clipboard.
        """
        if field in data:
            clipboard.copy(data[field])
        else:
            print(f"Field '{field}' not found in data.")

    def type_text(self, text, data):
        """
        Simulate typing text.
        """
        resolved_text = text.format(**data)
        pyautogui.typewrite(resolved_text)

    def key_press(self, key):
        """
        Simulate a key press.
        """
        pyautogui.press(key)

    def wait(self, duration):
        """
        Pause execution for a specified duration.
        """
        time.sleep(duration)

    def execute_for_multiple_records(self, records):
        time.sleep(5)  # Give user time to minimize, if desired

        for record in records:
            session = self.db_manager.Session()
            try:
                data = {
                    "request_date": record.request_date.strftime("%d/%m/%Y") if record.request_date else "",
                    "request_number": record.request_number,
                    "given_names": record.given_names,
                    "surname": record.surname,
                    "address": record.address,
                    "suburb": record.suburb,
                    "state": record.state,
                    "postcode": record.postcode,
                    "home_phone": record.home_phone,
                    "mobile_phone": record.mobile_phone,
                    "medicare_number": record.medicare_number,
                    "medicare_position": record.medicare_position,
                    "provider_number": record.provider_number,
                    "date_of_birth": record.date_of_birth.strftime("%d/%m/%Y") if record.date_of_birth else "",
                    "ocr_confidence": str(record.ocr_confidence) if record.ocr_confidence else "",
                    "sex": record.sex
                }
                self.execute_protocol(data)

                local_record = session.merge(record)
                session.delete(local_record)
                session.commit()


            except Exception as e:
                session.rollback()
            finally:
                session.close()

        # Or, if you want a final "All done" popup after everything:
        self.show_pyqt_popup(
            title="Data Entry Complete",
            message="All records have been processed.\nYou can restore your window now."
        )

    def show_pyqt_popup(self, title: str, message: str):
        """
        Shows a modal QMessageBox to notify about the current status.
        Requires a running QApplication in your PyQt application.
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()

    def refresh_database(self):
        """
        Example method if you still need to refresh the DB externally.
        """
        session = self.db_manager.Session()
        try:
            records = session.query(PatientRecord).all()
            # Detach them from the session so they're safe to pass around
            session.expunge_all()
            return records
        except Exception as e:
            print(f"Error refreshing DB: {e}")
            return []
        finally:
            session.close()
