#!/usr/bin/env python3
"""
AutoClicker - A feature-rich autoclicker with multiple modes and a modern GUI.

Modes:
- Autoclick Mode: Start with delay, click at specified rate, stop with hotkey
- Keybind Mode: Click while holding a specified key
- Normal Mode: Click while holding M1 (left mouse button)
"""

import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    HAS_TTKBOOTSTRAP = True
except ImportError:
    import tkinter.ttk as ttk
    HAS_TTKBOOTSTRAP = False
    print("Note: Install ttkbootstrap for a better UI experience")

from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, KeyCode, Controller as KeyboardController


class ClickMode(Enum):
    AUTOCLICK = "autoclick"
    KEYBIND = "keybind"
    NORMAL = "normal"


@dataclass
class AutoClickSettings:
    start_delay: float = 1.0
    clicks_per_sec: float = 10.0
    kill_hotkey: str = "F6"


@dataclass
class KeybindSettings:
    clicks_per_sec: float = 10.0
    autoclick_hotkey: str = "F7"


@dataclass
class NormalSettings:
    clicks_per_sec: float = 10.0
    start_delay: float = 0.5


class ClickerEngine:
    """Handles the actual clicking logic across all modes."""
    
    def __init__(self):
        self.mouse_controller = MouseController()
        self.keyboard_controller = KeyboardController()
        self.is_clicking = False
        self.click_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.click_count = 0
        self.on_click_callback: Optional[Callable] = None
        
    def set_click_callback(self, callback: Callable):
        """Set callback function to be called on each click."""
        self.on_click_callback = callback
        
    def reset_click_count(self):
        """Reset the click counter."""
        self.click_count = 0
        if self.on_click_callback:
            self.on_click_callback(self.click_count)
        
    def start_clicking(self, clicks_per_sec: float, delay: float = 0):
        """Start the auto-clicking loop."""
        if self.is_clicking:
            return
            
        self.is_clicking = True
        self._stop_event.clear()
        
        def click_loop():
            if delay > 0:
                # Wait for delay, checking for stop event periodically
                elapsed = 0
                while elapsed < delay and not self._stop_event.is_set():
                    time.sleep(0.05)
                    elapsed += 0.05
                    
            interval = 1.0 / clicks_per_sec if clicks_per_sec > 0 else 0.1
            
            while not self._stop_event.is_set():
                self.mouse_controller.click(Button.left)
                self.click_count += 1
                if self.on_click_callback:
                    self.on_click_callback(self.click_count)
                time.sleep(interval)
                
            self.is_clicking = False
            
        self.click_thread = threading.Thread(target=click_loop, daemon=True)
        self.click_thread.start()
        
    def stop_clicking(self):
        """Stop the auto-clicking loop."""
        self._stop_event.set()
        self.is_clicking = False


class HotkeyManager:
    """Manages keyboard and mouse listeners for hotkeys."""
    
    def __init__(self):
        self.keyboard_listener: Optional[keyboard.Listener] = None
        self.mouse_listener: Optional[mouse.Listener] = None
        self.pressed_keys: set = set()
        self.callbacks: dict = {}
        self.recording_callback: Optional[Callable] = None
        self.is_recording = False
        
    def start(self):
        """Start keyboard and mouse listeners."""
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click
        )
        self.keyboard_listener.start()
        self.mouse_listener.start()
        
    def stop(self):
        """Stop all listeners."""
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
            
    def register_hotkey(self, key_name: str, callback: Callable):
        """Register a callback for a specific hotkey."""
        self.callbacks[key_name.lower()] = callback
        
    def unregister_hotkey(self, key_name: str):
        """Unregister a hotkey callback."""
        key_lower = key_name.lower()
        if key_lower in self.callbacks:
            del self.callbacks[key_lower]
            
    def start_recording(self, callback: Callable):
        """Start recording the next keypress."""
        self.is_recording = True
        self.recording_callback = callback
        
    def _key_to_name(self, key) -> str:
        """Convert a pynput key to a readable name."""
        if isinstance(key, Key):
            return key.name.upper()
        elif isinstance(key, KeyCode):
            if key.char:
                return key.char.upper()
            elif key.vk:
                # Handle special keys by virtual key code
                return f"VK_{key.vk}"
        return str(key)
        
    def _on_key_press(self, key):
        """Handle key press events."""
        key_name = self._key_to_name(key)
        
        if self.is_recording:
            self.is_recording = False
            if self.recording_callback:
                self.recording_callback(key_name)
            return
            
        self.pressed_keys.add(key_name.lower())
        
        # Check for registered hotkeys
        if key_name.lower() in self.callbacks:
            self.callbacks[key_name.lower()]("press")
            
    def _on_key_release(self, key):
        """Handle key release events."""
        key_name = self._key_to_name(key)
        self.pressed_keys.discard(key_name.lower())
        
        # Check for registered hotkeys
        if key_name.lower() in self.callbacks:
            self.callbacks[key_name.lower()]("release")
            
    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse click events."""
        if button == Button.left:
            if pressed:
                if "m1" in self.callbacks:
                    self.callbacks["m1"]("press")
            else:
                if "m1" in self.callbacks:
                    self.callbacks["m1"]("release")
        return True
    
    def is_key_pressed(self, key_name: str) -> bool:
        """Check if a key is currently pressed."""
        return key_name.lower() in self.pressed_keys


class AutoClickerGUI:
    """Main GUI application for the AutoClicker."""
    
    def __init__(self):
        # Initialize settings
        self.autoclick_settings = AutoClickSettings()
        self.keybind_settings = KeybindSettings()
        self.normal_settings = NormalSettings()
        
        # Initialize engine and hotkey manager
        self.engine = ClickerEngine()
        self.hotkey_manager = HotkeyManager()
        
        # Current mode and state
        self.current_mode = ClickMode.AUTOCLICK
        self.is_active = False
        
        # Build GUI
        self._build_gui()
        
        # Start hotkey listener
        self.hotkey_manager.start()
        self._setup_hotkeys()
        
        # Setup click counter callback
        self.engine.set_click_callback(self._update_click_counter)
        
    def _update_click_counter(self, count: int):
        """Update the click counter display (thread-safe)."""
        self.root.after(0, lambda: self.click_counter_var.set(f"Clicks: {count}"))
        
    def _reset_click_counter(self):
        """Reset the click counter."""
        self.engine.reset_click_count()
        
    def _build_gui(self):
        """Build the main GUI window."""
        if HAS_TTKBOOTSTRAP:
            self.root = ttk.Window(
                title="AutoClicker Pro",
                themename="darkly",
                size=(500, 580),
                resizable=(False, False)
            )
        else:
            self.root = tk.Tk()
            self.root.title("AutoClicker Pro")
            self.root.geometry("500x580")
            self.root.resizable(False, False)
            
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="⚡ AutoClicker Pro",
            font=("Segoe UI", 24, "bold"),
            bootstyle="primary" if HAS_TTKBOOTSTRAP else None
        )
        title_label.pack(pady=(0, 20))
        
        # Mode selection notebook
        self.notebook = ttk.Notebook(main_frame, bootstyle="primary" if HAS_TTKBOOTSTRAP else None)
        self.notebook.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # Create mode tabs
        self._create_autoclick_tab()
        self._create_keybind_tab()
        self._create_normal_tab()
        
        # Status section
        status_frame = ttk.Labelframe(main_frame, text="Status", padding=15, bootstyle="info" if HAS_TTKBOOTSTRAP else None)
        status_frame.pack(fill=X, pady=(0, 10))
        
        self.status_label = ttk.Label(
            status_frame,
            text="● Inactive",
            font=("Segoe UI", 14),
            bootstyle="danger" if HAS_TTKBOOTSTRAP else None
        )
        self.status_label.pack()
        
        # Click counter with reset button
        counter_frame = ttk.Frame(status_frame)
        counter_frame.pack(pady=(5, 0))
        
        self.click_counter_var = tk.StringVar(value="Clicks: 0")
        self.click_counter = 0
        click_counter_label = ttk.Label(
            counter_frame,
            textvariable=self.click_counter_var,
            font=("Segoe UI", 11)
        )
        click_counter_label.pack(side=LEFT, padx=(0, 10))
        
        reset_btn = ttk.Button(
            counter_frame,
            text="Reset",
            command=self._reset_click_counter,
            bootstyle="outline-secondary" if HAS_TTKBOOTSTRAP else None,
            width=6
        )
        reset_btn.pack(side=LEFT)
        
        # Bind tab change
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)
        
    def _create_autoclick_tab(self):
        """Create the Autoclick Mode tab."""
        frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(frame, text="  🎯 Autoclick Mode  ")
        
        # Description
        desc = ttk.Label(
            frame,
            text="Start clicking with a delay, stop with hotkey.",
            font=("Segoe UI", 10),
            foreground="gray"
        )
        desc.pack(anchor=W, pady=(0, 15))
        
        # Settings grid
        settings_frame = ttk.Frame(frame)
        settings_frame.pack(fill=X)
        
        # Start Delay
        row1 = ttk.Frame(settings_frame)
        row1.pack(fill=X, pady=8)
        ttk.Label(row1, text="Start Delay (sec):", font=("Segoe UI", 11)).pack(side=LEFT)
        self.autoclick_delay_var = tk.StringVar(value=str(self.autoclick_settings.start_delay))
        delay_entry = ttk.Entry(row1, textvariable=self.autoclick_delay_var, width=10, font=("Segoe UI", 11))
        delay_entry.pack(side=RIGHT)
        
        # Clicks per second
        row2 = ttk.Frame(settings_frame)
        row2.pack(fill=X, pady=8)
        ttk.Label(row2, text="Clicks per Second:", font=("Segoe UI", 11)).pack(side=LEFT)
        self.autoclick_cps_var = tk.StringVar(value=str(self.autoclick_settings.clicks_per_sec))
        cps_entry = ttk.Entry(row2, textvariable=self.autoclick_cps_var, width=10, font=("Segoe UI", 11))
        cps_entry.pack(side=RIGHT)
        
        # Kill hotkey
        row3 = ttk.Frame(settings_frame)
        row3.pack(fill=X, pady=8)
        ttk.Label(row3, text="Start/Stop Hotkey:", font=("Segoe UI", 11)).pack(side=LEFT)
        hotkey_frame = ttk.Frame(row3)
        hotkey_frame.pack(side=RIGHT)
        self.autoclick_hotkey_var = tk.StringVar(value=self.autoclick_settings.kill_hotkey)
        self.autoclick_hotkey_btn = ttk.Button(
            hotkey_frame,
            textvariable=self.autoclick_hotkey_var,
            command=lambda: self._record_hotkey("autoclick"),
            width=10,
            bootstyle="outline-secondary" if HAS_TTKBOOTSTRAP else None
        )
        self.autoclick_hotkey_btn.pack()
        
        # Start button
        self.autoclick_start_btn = ttk.Button(
            frame,
            text="▶ Start Autoclicking",
            command=self._toggle_autoclick,
            bootstyle="success" if HAS_TTKBOOTSTRAP else None,
            width=25
        )
        self.autoclick_start_btn.pack(pady=(30, 0))
        
    def _create_keybind_tab(self):
        """Create the Keybind Mode tab."""
        frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(frame, text="  ⌨️ Keybind Mode  ")
        
        # Description
        desc = ttk.Label(
            frame,
            text="Click continuously while holding a key.",
            font=("Segoe UI", 10),
            foreground="gray"
        )
        desc.pack(anchor=W, pady=(0, 15))
        
        # Settings grid
        settings_frame = ttk.Frame(frame)
        settings_frame.pack(fill=X)
        
        # Clicks per second
        row1 = ttk.Frame(settings_frame)
        row1.pack(fill=X, pady=8)
        ttk.Label(row1, text="Clicks per Second:", font=("Segoe UI", 11)).pack(side=LEFT)
        self.keybind_cps_var = tk.StringVar(value=str(self.keybind_settings.clicks_per_sec))
        cps_entry = ttk.Entry(row1, textvariable=self.keybind_cps_var, width=10, font=("Segoe UI", 11))
        cps_entry.pack(side=RIGHT)
        
        # Autoclick hotkey
        row2 = ttk.Frame(settings_frame)
        row2.pack(fill=X, pady=8)
        ttk.Label(row2, text="Hold to Click Key:", font=("Segoe UI", 11)).pack(side=LEFT)
        hotkey_frame = ttk.Frame(row2)
        hotkey_frame.pack(side=RIGHT)
        self.keybind_hotkey_var = tk.StringVar(value=self.keybind_settings.autoclick_hotkey)
        self.keybind_hotkey_btn = ttk.Button(
            hotkey_frame,
            textvariable=self.keybind_hotkey_var,
            command=lambda: self._record_hotkey("keybind"),
            width=10,
            bootstyle="outline-secondary" if HAS_TTKBOOTSTRAP else None
        )
        self.keybind_hotkey_btn.pack()
        
        # Enable button
        self.keybind_enable_btn = ttk.Button(
            frame,
            text="🔓 Enable Keybind Mode",
            command=self._toggle_keybind,
            bootstyle="success" if HAS_TTKBOOTSTRAP else None,
            width=25
        )
        self.keybind_enable_btn.pack(pady=(30, 0))
        
        # Info label
        info_label = ttk.Label(
            frame,
            text="ℹ️ Hold the specified key to autoclick.",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        info_label.pack(pady=(15, 0))
        
    def _create_normal_tab(self):
        """Create the Normal Mode tab."""
        frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(frame, text="  🖱️ Normal Mode  ")
        
        # Description
        desc = ttk.Label(
            frame,
            text="Click while holding left mouse button (M1).",
            font=("Segoe UI", 10),
            foreground="gray"
        )
        desc.pack(anchor=W, pady=(0, 15))
        
        # Settings grid
        settings_frame = ttk.Frame(frame)
        settings_frame.pack(fill=X)
        
        # Clicks per second
        row1 = ttk.Frame(settings_frame)
        row1.pack(fill=X, pady=8)
        ttk.Label(row1, text="Clicks per Second:", font=("Segoe UI", 11)).pack(side=LEFT)
        self.normal_cps_var = tk.StringVar(value=str(self.normal_settings.clicks_per_sec))
        cps_entry = ttk.Entry(row1, textvariable=self.normal_cps_var, width=10, font=("Segoe UI", 11))
        cps_entry.pack(side=RIGHT)
        
        # Start Delay
        row2 = ttk.Frame(settings_frame)
        row2.pack(fill=X, pady=8)
        ttk.Label(row2, text="Start Delay (sec):", font=("Segoe UI", 11)).pack(side=LEFT)
        self.normal_delay_var = tk.StringVar(value=str(self.normal_settings.start_delay))
        delay_entry = ttk.Entry(row2, textvariable=self.normal_delay_var, width=10, font=("Segoe UI", 11))
        delay_entry.pack(side=RIGHT)
        
        # Enable button
        self.normal_enable_btn = ttk.Button(
            frame,
            text="🔓 Enable Normal Mode",
            command=self._toggle_normal,
            bootstyle="success" if HAS_TTKBOOTSTRAP else None,
            width=25
        )
        self.normal_enable_btn.pack(pady=(30, 0))
        
        # Info label
        info_label = ttk.Label(
            frame,
            text="ℹ️ Hold Left Mouse Button to autoclick after delay.",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        info_label.pack(pady=(15, 0))
        
    def _record_hotkey(self, mode: str):
        """Start recording a hotkey."""
        if mode == "autoclick":
            self.autoclick_hotkey_var.set("Press key...")
            self.hotkey_manager.start_recording(
                lambda key: self._set_hotkey(mode, key)
            )
        elif mode == "keybind":
            self.keybind_hotkey_var.set("Press key...")
            self.hotkey_manager.start_recording(
                lambda key: self._set_hotkey(mode, key)
            )
            
    def _set_hotkey(self, mode: str, key: str):
        """Set the recorded hotkey."""
        if mode == "autoclick":
            self.autoclick_hotkey_var.set(key)
            self.autoclick_settings.kill_hotkey = key
        elif mode == "keybind":
            self.keybind_hotkey_var.set(key)
            self.keybind_settings.autoclick_hotkey = key
            
        # Re-setup hotkeys
        self._setup_hotkeys()
        
    def _setup_hotkeys(self):
        """Setup all hotkey callbacks."""
        # Clear existing
        self.hotkey_manager.callbacks.clear()
        
        # Autoclick mode hotkey
        def autoclick_hotkey_handler(event_type):
            if event_type == "press" and self.current_mode == ClickMode.AUTOCLICK:
                self.root.after(0, self._toggle_autoclick)
                
        self.hotkey_manager.register_hotkey(
            self.autoclick_settings.kill_hotkey,
            autoclick_hotkey_handler
        )
        
        # Keybind mode hotkey
        def keybind_hotkey_handler(event_type):
            if not self.is_active or self.current_mode != ClickMode.KEYBIND:
                return
            if event_type == "press":
                if not self.engine.is_clicking:
                    cps = self._get_float_value(self.keybind_cps_var.get(), 10.0)
                    self.engine.start_clicking(cps, delay=0)
                    self._update_status(True)
            elif event_type == "release":
                self.engine.stop_clicking()
                self._update_status(False)
                
        self.hotkey_manager.register_hotkey(
            self.keybind_settings.autoclick_hotkey,
            keybind_hotkey_handler
        )
        
        # Normal mode (M1)
        def normal_mode_handler(event_type):
            if not self.is_active or self.current_mode != ClickMode.NORMAL:
                return
            if event_type == "press":
                if not self.engine.is_clicking:
                    cps = self._get_float_value(self.normal_cps_var.get(), 10.0)
                    delay = self._get_float_value(self.normal_delay_var.get(), 0.5)
                    self.engine.start_clicking(cps, delay=delay)
                    self._update_status(True)
            elif event_type == "release":
                self.engine.stop_clicking()
                self._update_status(False)
                
        self.hotkey_manager.register_hotkey("m1", normal_mode_handler)
        
    def _toggle_autoclick(self):
        """Toggle autoclick mode on/off."""
        if self.engine.is_clicking:
            self.engine.stop_clicking()
            self.autoclick_start_btn.configure(
                text="▶ Start Autoclicking",
                bootstyle="success" if HAS_TTKBOOTSTRAP else None
            )
            self._update_status(False)
        else:
            try:
                cps = self._get_float_value(self.autoclick_cps_var.get(), 10.0)
                delay = self._get_float_value(self.autoclick_delay_var.get(), 1.0)
                
                self.engine.start_clicking(cps, delay=delay)
                self.autoclick_start_btn.configure(
                    text="⏹ Stop Autoclicking",
                    bootstyle="danger" if HAS_TTKBOOTSTRAP else None
                )
                self._update_status(True)
            except ValueError as e:
                messagebox.showerror("Invalid Input", str(e))
                
    def _toggle_keybind(self):
        """Toggle keybind mode enabled/disabled."""
        self.is_active = not self.is_active
        self.current_mode = ClickMode.KEYBIND
        
        if self.is_active:
            self.keybind_enable_btn.configure(
                text="🔒 Disable Keybind Mode",
                bootstyle="danger" if HAS_TTKBOOTSTRAP else None
            )
            self._update_status(False, mode_text=f"Keybind Mode Active - Hold {self.keybind_settings.autoclick_hotkey}")
        else:
            self.engine.stop_clicking()
            self.keybind_enable_btn.configure(
                text="🔓 Enable Keybind Mode",
                bootstyle="success" if HAS_TTKBOOTSTRAP else None
            )
            self._update_status(False)
            
    def _toggle_normal(self):
        """Toggle normal mode enabled/disabled."""
        self.is_active = not self.is_active
        self.current_mode = ClickMode.NORMAL
        
        if self.is_active:
            self.normal_enable_btn.configure(
                text="🔒 Disable Normal Mode",
                bootstyle="danger" if HAS_TTKBOOTSTRAP else None
            )
            self._update_status(False, mode_text="Normal Mode Active - Hold M1 to Click")
        else:
            self.engine.stop_clicking()
            self.normal_enable_btn.configure(
                text="🔓 Enable Normal Mode",
                bootstyle="success" if HAS_TTKBOOTSTRAP else None
            )
            self._update_status(False)
            
    def _update_status(self, is_clicking: bool, mode_text: str = None):
        """Update the status display."""
        if is_clicking:
            self.status_label.configure(
                text="● Clicking...",
                bootstyle="success" if HAS_TTKBOOTSTRAP else None
            )
        elif mode_text:
            self.status_label.configure(
                text=f"● {mode_text}",
                bootstyle="warning" if HAS_TTKBOOTSTRAP else None
            )
        else:
            self.status_label.configure(
                text="● Inactive",
                bootstyle="danger" if HAS_TTKBOOTSTRAP else None
            )
            
    def _get_float_value(self, value: str, default: float) -> float:
        """Parse a float value from string with validation."""
        try:
            result = float(value)
            if result <= 0:
                raise ValueError(f"Value must be positive, got {result}")
            return result
        except ValueError:
            return default
            
    def _on_tab_change(self, event):
        """Handle tab change events."""
        # Stop any active clicking when changing tabs
        self.engine.stop_clicking()
        
        # Disable modes when switching
        self.is_active = False
        
        # Reset all buttons
        self.autoclick_start_btn.configure(
            text="▶ Start Autoclicking",
            bootstyle="success" if HAS_TTKBOOTSTRAP else None
        )
        self.keybind_enable_btn.configure(
            text="🔓 Enable Keybind Mode",
            bootstyle="success" if HAS_TTKBOOTSTRAP else None
        )
        self.normal_enable_btn.configure(
            text="🔓 Enable Normal Mode",
            bootstyle="success" if HAS_TTKBOOTSTRAP else None
        )
        
        # Update current mode
        tab_index = self.notebook.index(self.notebook.select())
        if tab_index == 0:
            self.current_mode = ClickMode.AUTOCLICK
        elif tab_index == 1:
            self.current_mode = ClickMode.KEYBIND
        else:
            self.current_mode = ClickMode.NORMAL
            
        self._update_status(False)
        
    def _on_close(self):
        """Handle window close event."""
        self.engine.stop_clicking()
        self.hotkey_manager.stop()
        self.root.destroy()
        
    def run(self):
        """Run the application."""
        self.root.mainloop()


def main():
    """Main entry point."""
    try:
        app = AutoClickerGUI()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
