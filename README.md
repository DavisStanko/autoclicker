# ⚡ AutoClicker Pro

A feature-rich Python autoclicker with a modern dark-themed GUI and multiple clicking modes.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

### 🎯 Autoclick Mode
- **Start Delay**: Set a delay before clicking begins
- **Clicks per Second**: Configure clicking speed
- **Hotkey Control**: Start/Stop with a customizable hotkey (default: F6)

### ⌨️ Keybind Mode
- **Hold to Click**: Clicks continuously while holding a specified key
- **Clicks per Second**: Configure clicking speed
- **Customizable Hotkey**: Choose which key triggers clicking (default: F7)

### 🖱️ Normal Mode
- **M1 Hold**: Clicks while holding the left mouse button
- **Start Delay**: Delay before rapid clicking begins after M1 is pressed
- **Clicks per Second**: Configure clicking speed

## Installation

1. Clone or download this repository
2. Create a virtual environment and install dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate it (Linux/Mac)
source venv/bin/activate

# Or on Windows
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

Run the application (with venv activated):

```bash
python autoclicker.py
```

### Mode Instructions

#### Autoclick Mode
1. Set your desired start delay and clicks per second
2. Optionally change the hotkey by clicking the button
3. Click "Start Autoclicking" or press the hotkey (F6)
4. Press the hotkey again to stop

#### Keybind Mode
1. Set your desired clicks per second
2. Set the key you want to hold for clicking
3. Click "Enable Keybind Mode"
4. Hold the configured key to autoclick

#### Normal Mode
1. Set your desired clicks per second and start delay
2. Click "Enable Normal Mode"
3. Hold left mouse button (M1) - clicking starts after the delay

## Requirements

- Python 3.8+
- pynput >= 1.7.6
- ttkbootstrap >= 1.10.1

## Notes

- On Linux, you may need to run with `sudo` for mouse/keyboard control to work properly, or add yourself to the `input` group
- The app uses a dark theme by default for comfortable use

## License

This project is licensed under the [GPL-3.0](LICENSE.md)
GNU General Public License - see the [LICENSE.md](LICENSE.md) file for
details.
