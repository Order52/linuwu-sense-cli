
A streamlined Bash-based frontend for managing PredatorSense-like features on Linux systems, using the Linuwu-Sense kernel module.

    Fork of 0x7375646F/Linuwu-Sense
    Huge thanks to sudo / 0x7375646F for bringing PredatorSense to Linux!

This launcher script was developed (with some help from AI) to provide a clean, user-friendly, menu-driven interface for configuring system-level features via the linuwu_sense kernel module.

# Tested on:
Acer Predator Helios 16 
Model: PH16-71

## 📸 Preview

Here’s what the tool looks like in action:


<img width="490" height="325" alt="image" src="https://github.com/user-attachments/assets/83cf7180-e3db-4088-9523-5073a368d442" />



<img width="315" height="338" alt="image" src="https://github.com/user-attachments/assets/f35fc9c0-80e9-4c4c-aa78-6cc1fe0bac98" />




##  **Predator Key** 
You can also check out how bind the Predator Key on your keyboard here https://github.com/Order52/Predator-Key

🧩 Features

Easily control and monitor:

🌬️ Advanced Fan Curve Control

A new Python-based fan control utility is now included. It provides profile-based and dynamic fan control through the Linuwu-Sense interface.

## **Features:**
- 🎮 `gaming` profile: maximum cooling for performance
- 🌙 `quiet` profile: prioritizes low noise
- ⚖️ `balanced` profile: optimized for general use
- 🔁 Daemon mode for continuous monitoring
- 📊 View current status and configuration
- 🛠️ Edit config for custom behavior

> Note: All commands require root (`sudo`) for now.

    ✅ Keyboard Backlight Timeout
    🔋 Battery Charge Limiter
    🎵 Boot Animation and Sound
    🌬️ Fan Speeds (Auto, Quiet, Balanced, Performance, Turbo, Custom)
    💡 LCD Override
    ⚡ USB Charging Thresholds
    🔧 Battery Calibration

All through a terminal interface, backed by SysFS and requiring root access.
🚀 Usage
1. Prerequisites

    Linux kernel module: linuwu_sense.ko
    Compatible Acer Predator laptop
    Root privileges (the script will attempt to elevate with sudo)

    ⚠️ You must load the Linuwu-Sense kernel module before using this script.

🧱 Step 1: Install Kernel Headers

On Arch Linux:
```
sudo pacman -S linux-headers
```
🛠️ Step 2: Clone and Build the Module
```
git clone https://github.com/Order52/linuwu-sense-cli.git
cd linuwu-sense-cli
make install
```
⚠️ This will remove the default acer_wmi module and load the patched version from Linuwu-Sense. Make sure to run with sudo if needed.

⚙️ Using Clang Instead?
```
sudo make CC=clang LD=ld.lld install
```
🔄 To Uninstall
```
make uninstall
```
Then Run the Script
```
chmod +x Linuwu-sense-menu.py
chmod +x fan-curve.py
python Linuwu-sense-menu.py
python ./fan-curve.py
```

You can also add these to your .bashrc for quick control on the fan curves
```
fan-gaming() {
    sudo python3 fan_curve.py --profile gaming
    sudo python3 fan_curve.py --daemon
}

fan-balance() {
    sudo python3 fan_curve.py --profile balanced
    sudo python3 fan_curve.py --daemon
}

fan-quiet() {
    sudo python3 fan_curve.py --profile quiet
    sudo python3 fan_curve.py --daemon
}
```
