#!/bin/bash
# Fan Curve Controller - No-Sudo Setup Script
#  Work Without sudo script

USER=$(logname 2>/dev/null || echo $SUDO_USER || whoami)
HOME_DIR="/home/$USER"
SCRIPT_PATH="$HOME_DIR/.scripts/Acer/PredatorSense/Fan Curve/Fan_Curve.py"
SERVICE_NAME="fan-curve"

echo "=== Fan Curve Controller - No-Sudo Setup ==="
echo "User: $USER"
echo "Home: $HOME_DIR"
echo "Script: $SCRIPT_PATH"

# Check if script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "ERROR: fan.py not found at $SCRIPT_PATH"
    echo "Please make sure fan.py is in your home directory"
    exit 1
fi

# Create udev rules to set proper permissions
echo "Creating udev rules..."
cat > /etc/udev/rules.d/99-linuwu-sense.rules << 'EOF'
# LinuWu Sense Fan Control - Allow user access without sudo
SUBSYSTEM=="module", KERNEL=="linuwu_sense", RUN+="/bin/chmod 666 /sys/module/linuwu_sense/drivers/platform:acer-wmi/acer-wmi/predator_sense/fan_speed"
SUBSYSTEM=="platform", KERNEL=="acer-wmi", RUN+="/bin/chmod 666 /sys/module/linuwu_sense/drivers/platform:acer-wmi/acer-wmi/predator_sense/fan_speed"

# Set permissions on thermal zones for temperature monitoring
SUBSYSTEM=="thermal", KERNEL=="thermal_zone*", MODE="0644"
SUBSYSTEM=="hwmon", KERNEL=="hwmon*", MODE="0644"
SUBSYSTEM=="drm", KERNEL=="card*", RUN+="/bin/chmod -R 644 /sys/class/drm/card*/device/hwmon/*/temp*_input"

# Alternative approach - run script when module loads
ACTION=="add", SUBSYSTEM=="module", KERNEL=="linuwu_sense", RUN+="/usr/local/bin/setup-fan-permissions.sh"
EOF

echo "✓ Created udev rules: /etc/udev/rules.d/99-linuwu-sense.rules"

# Create permission setup script
cat > /usr/local/bin/setup-fan-permissions.sh << 'EOF'
#!/bin/bash
# Set permissions on LinuWu Sense sysfs files

sleep 2  # Wait for sysfs to be ready

SYSFS_PATH="/sys/module/linuwu_sense/drivers/platform:acer-wmi/acer-wmi/predator_sense"

if [ -d "$SYSFS_PATH" ]; then
    chmod 666 "$SYSFS_PATH/fan_speed" 2>/dev/null
    chmod 666 "$SYSFS_PATH/backlight_timeout" 2>/dev/null
    chmod 666 "$SYSFS_PATH/battery_limiter" 2>/dev/null
    chmod 666 "$SYSFS_PATH/boot_animation_sound" 2>/dev/null
    chmod 666 "$SYSFS_PATH/lcd_override" 2>/dev/null
    chmod 666 "$SYSFS_PATH/usb_charging" 2>/dev/null
    chmod 666 "$SYSFS_PATH/battery_calibration" 2>/dev/null
    
    # Set ownership to allow user access
    chown root:users "$SYSFS_PATH"/* 2>/dev/null
fi

# Also set thermal zone permissions
chmod 644 /sys/class/thermal/thermal_zone*/temp 2>/dev/null
chmod 644 /sys/class/hwmon/hwmon*/temp*_input 2>/dev/null
EOF

chmod +x /usr/local/bin/setup-fan-permissions.sh
echo "✓ Created permission setup script: /usr/local/bin/setup-fan-permissions.sh"

# Add user to necessary groups
usermod -a -G users "$USER" 2>/dev/null
echo "✓ Added user to 'users' group"



# Create systemd system service (runs as user, not root)
SYSTEM_SERVICE_DIR="/etc/systemd/system"

cat > "$SYSTEM_SERVICE_DIR/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Fan Curve Controller (System Service - No Sudo)
After=graphical.target
Wants=graphical.target

[Service]
Type=simple
User=$USER
Group=users
WorkingDirectory=$HOME_DIR
ExecStart=/usr/bin/python3 $SCRIPT_PATH --daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Created system systemd service: $SYSTEM_SERVICE_DIR/${SERVICE_NAME}.service"


# Create systemd user service (runs as user, not root)
#USER_SERVICE_DIR="/home/$USER/.config/systemd/user"
#mkdir -p "$USER_SERVICE_DIR"

#cat > "$USER_SERVICE_DIR/${SERVICE_NAME}.service" << EOF
#[Unit]
#Description=Fan Curve Controller (User Service)
#After=graphical-session.target
#Wants=graphical-session.target

#[Service]
#Type=simple
#WorkingDirectory=$HOME_DIR
#ExecStart=/usr/bin/python3 $SCRIPT_PATH --daemon
#Restart=always
#RestartSec=10
#StandardOutput=journal
#StandardError=journal

#[Install]
#WantedBy=default.target
#EOF

#chown -R "$USER:$USER" "$USER_SERVICE_DIR"
#echo "✓ Created user systemd service: $USER_SERVICE_DIR/${SERVICE_NAME}.service"

# Reload udev rules
udevadm control --reload-rules
udevadm trigger

# Apply permissions now if module is loaded
if lsmod | grep -q linuwu_sense; then
    echo "LinuWu Sense module detected, applying permissions..."
    /usr/local/bin/setup-fan-permissions.sh
fi

#echo ""
#echo "=== User Service Setup ==="
#echo "Run these commands as your user (not sudo):"
#echo "systemctl --user daemon-reload"
#echo "systemctl --user enable ${SERVICE_NAME}.service"
#echo "systemctl --user start ${SERVICE_NAME}.service"
#echo ""

echo ""
echo "=== System Service Setup ==="
echo "Run these commands as root/sudo:"
echo "systemctl daemon-reload"
echo "systemctl enable ${SERVICE_NAME}.service"
echo "systemctl start ${SERVICE_NAME}.service"
echo "Enable lingering to start service on boot:"
echo "sudo loginctl enable-linger $USER"

echo ""
echo "=== System Service Management Commands ==="
echo "Start:   sudo systemctl start ${SERVICE_NAME}"
echo "Stop:    sudo systemctl stop ${SERVICE_NAME}"
echo "Restart: sudo systemctl restart ${SERVICE_NAME}"
echo "Status:  sudo systemctl status ${SERVICE_NAME}"
echo "Logs:    sudo journalctl -u ${SERVICE_NAME} -f"
echo "Disable: sudo systemctl disable ${SERVICE_NAME}"


#echo ""
#echo "=== User Service Management Commands ==="
#echo "Start:   systemctl --user start ${SERVICE_NAME}"
#echo "Stop:    systemctl --user stop ${SERVICE_NAME}"
#echo "Restart: systemctl --user restart ${SERVICE_NAME}"
#echo "Status:  systemctl --user status ${SERVICE_NAME}"
#echo "Logs:    journalctl --user -u ${SERVICE_NAME} -f"
#echo "Disable: systemctl --user disable ${SERVICE_NAME}"

echo ""
echo "=== Hyprland Integration ==="
echo "Add to ~/.config/hypr/hyprland.conf:"
echo "exec-once = systemctl start ${SERVICE_NAME}"
echo "# or"
echo "exec-once = python3 $SCRIPT_PATH --daemon"

echo ""
echo "=== Manual Testing ==="
echo "Test without sudo: python3 $SCRIPT_PATH --status"
echo "Run daemon: python3 $SCRIPT_PATH --daemon"

echo ""
echo "=== Setup Complete! ==="
echo "1. Reboot to ensure udev rules take effect"
echo "2. Run: systemctl enable ${SERVICE_NAME}.service"
echo "3. Run: systemctl start ${SERVICE_NAME}.service"
echo "4. Test: python3 ~/fan.py --status"
