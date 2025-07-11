#!/usr/bin/env python3
"""
Linuwu Sense Fan Curve Controller
Automatically adjusts CPU and GPU fan speeds based on thermal thresholds
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class ThermalMonitor:
    """Monitor CPU and GPU temperatures"""
    
    def __init__(self):
        self.cpu_thermal_paths = [
            "/sys/class/thermal/thermal_zone0/temp",
            "/sys/class/thermal/thermal_zone1/temp",
            "/sys/class/hwmon/hwmon0/temp1_input",
            "/sys/class/hwmon/hwmon1/temp1_input",
        ]
        
        self.gpu_thermal_paths = [
            "/sys/class/drm/card0/device/hwmon/hwmon*/temp1_input",
            "/sys/class/hwmon/hwmon*/temp1_input",
        ]
    
    def read_temp(self, path: str) -> Optional[float]:
        """Read temperature from a thermal zone file"""
        try:
            with open(path, 'r') as f:
                temp = int(f.read().strip())
                # Convert from millicelsius to celsius if needed
                return temp / 1000.0 if temp > 200 else temp
        except (FileNotFoundError, ValueError, PermissionError):
            return None
    
    def find_thermal_zones(self) -> Tuple[List[str], List[str]]:
        """Find available CPU and GPU thermal zones"""
        import glob
        
        cpu_zones = []
        gpu_zones = []
        
        # Find CPU thermal zones
        for pattern in self.cpu_thermal_paths:
            if '*' in pattern:
                cpu_zones.extend(glob.glob(pattern))
            elif os.path.exists(pattern):
                cpu_zones.append(pattern)
        
        # Find GPU thermal zones
        for pattern in self.gpu_thermal_paths:
            if '*' in pattern:
                gpu_zones.extend(glob.glob(pattern))
            elif os.path.exists(pattern):
                gpu_zones.append(pattern)
        
        return cpu_zones, gpu_zones
    
    def get_cpu_temp(self) -> Optional[float]:
        """Get current CPU temperature"""
        cpu_zones, _ = self.find_thermal_zones()
        
        temps = []
        for zone in cpu_zones:
            temp = self.read_temp(zone)
            if temp is not None:
                temps.append(temp)
        
        return max(temps) if temps else None
    
    def get_gpu_temp(self) -> Optional[float]:
        """Get current GPU temperature"""
        _, gpu_zones = self.find_thermal_zones()
        
        temps = []
        for zone in gpu_zones:
            temp = self.read_temp(zone)
            if temp is not None:
                temps.append(temp)
        
        return max(temps) if temps else None

class FanController:
    """Control fan speeds via LinuWu Sense module"""
    
    def __init__(self, sysfs_path: str = "/sys/module/linuwu_sense/drivers/platform:acer-wmi/acer-wmi/predator_sense/fan_speed"):
        self.sysfs_path = sysfs_path
        self.check_module()
    
    def check_module(self):
        """Check if the LinuWu Sense module is loaded"""
        if not os.path.exists(self.sysfs_path):
            print(f"ERROR: SysFS interface not found at {self.sysfs_path}")
            print("Make sure the linuwu_sense module is loaded!")
            sys.exit(1)
    
    def set_fan_speed(self, cpu_percent: int, gpu_percent: int) -> bool:
        """Set fan speeds for CPU and GPU"""
        try:
            fan_value = f"{cpu_percent},{gpu_percent}"
            with open(self.sysfs_path, 'w') as f:
                f.write(fan_value)
            return True
        except (OSError, IOError) as e:
            print(f"ERROR: Failed to set fan speed: {e}")
            return False
    
    def get_fan_speed(self) -> Optional[Tuple[int, int]]:
        """Get current fan speeds"""
        try:
            with open(self.sysfs_path, 'r') as f:
                speeds = f.read().strip().split(',')
                return int(speeds[0]), int(speeds[1])
        except (OSError, IOError, ValueError):
            return None

class FanCurve:
    """Fan curve configuration and logic"""
    
    def __init__(self, config_file: str = "fan_curve.json"):
        self.config_file = config_file
        self.load_config()
    
    def load_config(self):
        """Load fan curve configuration"""
        # Aggressive curves for gaming/work - prioritize cooling over noise
        default_config = {
            "cpu_curve": [
                {"temp": 35, "fan": 25},   # Start cooling earlier
                {"temp": 45, "fan": 40},   # More aggressive at mid temps
                {"temp": 55, "fan": 60},   # Keep temps low during gaming
                {"temp": 65, "fan": 75},   # Prevent any heat buildup
                {"temp": 75, "fan": 90},   # High cooling before throttling
                {"temp": 85, "fan": 100}   # Max cooling at safe limits
            ],
            "gpu_curve": [
                {"temp": 40, "fan": 30},   # GPUs run hotter, start early
                {"temp": 50, "fan": 45},   # Aggressive cooling for gaming
                {"temp": 60, "fan": 65},   # Keep GPU cool during load
                {"temp": 70, "fan": 80},   # Prevent thermal throttling
                {"temp": 80, "fan": 95},   # Max cooling before limits
                {"temp": 90, "fan": 100}   # Full blast at thermal limits
            ],
            "hysteresis": 2,  # Reduced hysteresis for quicker response
            "update_interval": 1  # Faster updates for gaming
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                print(f"Loaded configuration from {self.config_file}")
            except (json.JSONDecodeError, IOError):
                print(f"Error loading config, using defaults")
                self.config = default_config
        else:
            self.config = default_config
            self.save_config()
    
    def generate_profile(self, profile_name: str):
        """Generate different fan curve profiles"""
        profiles = {
            "gaming": {
                "cpu_curve": [
                    {"temp": 35, "fan": 25},
                    {"temp": 45, "fan": 40},
                    {"temp": 55, "fan": 60},
                    {"temp": 65, "fan": 75},
                    {"temp": 75, "fan": 90},
                    {"temp": 85, "fan": 100}
                ],
                "gpu_curve": [
                    {"temp": 40, "fan": 30},
                    {"temp": 50, "fan": 45},
                    {"temp": 60, "fan": 65},
                    {"temp": 70, "fan": 80},
                    {"temp": 80, "fan": 95},
                    {"temp": 90, "fan": 100}
                ],
                "hysteresis": 2,
                "update_interval": 1
            },
            "quiet": {
                "cpu_curve": [
                    {"temp": 40, "fan": 15},
                    {"temp": 50, "fan": 25},
                    {"temp": 65, "fan": 40},
                    {"temp": 75, "fan": 60},
                    {"temp": 85, "fan": 80},
                    {"temp": 95, "fan": 100}
                ],
                "gpu_curve": [
                    {"temp": 45, "fan": 20},
                    {"temp": 55, "fan": 30},
                    {"temp": 70, "fan": 45},
                    {"temp": 80, "fan": 65},
                    {"temp": 90, "fan": 85},
                    {"temp": 100, "fan": 100}
                ],
                "hysteresis": 4,
                "update_interval": 3
            },
            "balanced": {
                "cpu_curve": [
                    {"temp": 35, "fan": 20},
                    {"temp": 50, "fan": 35},
                    {"temp": 65, "fan": 50},
                    {"temp": 75, "fan": 70},
                    {"temp": 85, "fan": 85},
                    {"temp": 95, "fan": 100}
                ],
                "gpu_curve": [
                    {"temp": 40, "fan": 25},
                    {"temp": 55, "fan": 40},
                    {"temp": 70, "fan": 55},
                    {"temp": 80, "fan": 75},
                    {"temp": 90, "fan": 90},
                    {"temp": 100, "fan": 100}
                ],
                "hysteresis": 3,
                "update_interval": 2
            }
        }
        
        if profile_name in profiles:
            self.config = profiles[profile_name]
            self.save_config()
            print(f"Applied {profile_name} profile")
        else:
            print(f"Available profiles: {', '.join(profiles.keys())}")
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"Configuration saved to {self.config_file}")
        except IOError as e:
            print(f"Error saving config: {e}")
    
    def calculate_fan_speed(self, temp: float, curve: List[Dict], current_fan: int) -> int:
        """Calculate fan speed based on temperature and curve"""
        if temp is None:
            return current_fan
        
        # Apply hysteresis to prevent fan speed oscillation
        hysteresis = self.config.get("hysteresis", 3)
        
        # Find the appropriate fan speed
        for i, point in enumerate(curve):
            if temp <= point["temp"]:
                if i == 0:
                    return point["fan"]
                
                # Interpolate between points
                prev_point = curve[i-1]
                temp_range = point["temp"] - prev_point["temp"]
                fan_range = point["fan"] - prev_point["fan"]
                
                if temp_range > 0:
                    temp_offset = temp - prev_point["temp"]
                    fan_offset = (temp_offset / temp_range) * fan_range
                    target_fan = prev_point["fan"] + fan_offset
                else:
                    target_fan = point["fan"]
                
                # Apply hysteresis
                if abs(target_fan - current_fan) > hysteresis:
                    return int(target_fan)
                else:
                    return current_fan
        
        # Temperature is above the highest point
        return curve[-1]["fan"]

class FanCurveController:
    """Main controller class"""
    
    def __init__(self, config_file: str = "fan_curve.json"):
        self.thermal_monitor = ThermalMonitor()
        self.fan_controller = FanController()
        self.fan_curve = FanCurve(config_file)
        self.last_cpu_fan = 0
        self.last_gpu_fan = 0
        self.running = False
    
    def check_root(self):
        """Check if running as root"""
        if os.geteuid() != 0:
            print("ERROR: This script must be run as root for fan control!")
            print("Please run with: sudo python3 fan_curve.py")
            sys.exit(1)
    
    def run_once(self) -> bool:
        """Run one iteration of the fan curve controller"""
        # Get current temperatures
        cpu_temp = self.thermal_monitor.get_cpu_temp()
        gpu_temp = self.thermal_monitor.get_gpu_temp()
        
        if cpu_temp is None and gpu_temp is None:
            print("WARNING: No thermal sensors found!")
            return False
        
        # Calculate new fan speeds
        cpu_curve = self.fan_curve.config["cpu_curve"]
        gpu_curve = self.fan_curve.config["gpu_curve"]
        
        new_cpu_fan = self.fan_curve.calculate_fan_speed(cpu_temp, cpu_curve, self.last_cpu_fan)
        new_gpu_fan = self.fan_curve.calculate_fan_speed(gpu_temp, gpu_curve, self.last_gpu_fan)
        
        # Update fan speeds if changed
        if new_cpu_fan != self.last_cpu_fan or new_gpu_fan != self.last_gpu_fan:
            if self.fan_controller.set_fan_speed(new_cpu_fan, new_gpu_fan):
                self.last_cpu_fan = new_cpu_fan
                self.last_gpu_fan = new_gpu_fan
                print(f"CPU: {cpu_temp:.1f}°C → {new_cpu_fan}% | GPU: {gpu_temp:.1f}°C → {new_gpu_fan}%")
                return True
        
        return False
    
    def run_daemon(self):
        """Run the fan curve controller as a daemon"""
        print("Starting fan curve controller...")
        print("Press Ctrl+C to stop")
        
        self.running = True
        update_interval = self.fan_curve.config.get("update_interval", 2)
        
        try:
            while self.running:
                self.run_once()
                time.sleep(update_interval)
        except KeyboardInterrupt:
            print("\nStopping fan curve controller...")
            self.running = False
    
    def show_status(self):
        """Show current system status"""
        cpu_temp = self.thermal_monitor.get_cpu_temp()
        gpu_temp = self.thermal_monitor.get_gpu_temp()
        fan_speeds = self.fan_controller.get_fan_speed()
        
        print("=== System Status ===")
        print(f"CPU Temperature: {cpu_temp:.1f}°C" if cpu_temp else "CPU Temperature: N/A")
        print(f"GPU Temperature: {gpu_temp:.1f}°C" if gpu_temp else "GPU Temperature: N/A")
        
        if fan_speeds:
            print(f"Current Fan Speeds: CPU {fan_speeds[0]}%, GPU {fan_speeds[1]}%")
        else:
            print("Current Fan Speeds: N/A")
    
    def edit_config(self):
        """Interactive configuration editor"""
        print("=== Fan Curve Configuration ===")
        print("Current CPU curve:")
        for i, point in enumerate(self.fan_curve.config["cpu_curve"]):
            print(f"  {i+1}. {point['temp']}°C → {point['fan']}%")
        
        print("\nCurrent GPU curve:")
        for i, point in enumerate(self.fan_curve.config["gpu_curve"]):
            print(f"  {i+1}. {point['temp']}°C → {point['fan']}%")
        
        print(f"\nHysteresis: {self.fan_curve.config['hysteresis']}°C")
        print(f"Update interval: {self.fan_curve.config['update_interval']}s")
        
        print("\nTo edit configuration, modify the fan_curve.json file manually.")
        print("Example curve point: {\"temp\": 70, \"fan\": 80}")

def main():
    parser = argparse.ArgumentParser(description="LinuWu Sense Fan Curve Controller")
    parser.add_argument("--config", default="fan_curve.json", help="Configuration file path")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--edit-config", action="store_true", help="Show configuration")
    
    parser.add_argument("--profile", choices=["gaming", "quiet", "balanced"], help="Apply a predefined profile")
    
    args = parser.parse_args()
    
    controller = FanCurveController(args.config)
    
    if args.profile:
        controller.fan_curve.generate_profile(args.profile)
        print(f"Applied {args.profile} profile. Restart the daemon to use new settings.")
    elif args.status:
        controller.show_status()
    elif args.edit_config:
        controller.edit_config()
    elif args.once:
        controller.check_root()
        controller.run_once()
    else:
        controller.check_root()
        controller.run_daemon()

if __name__ == "__main__":
    main()
