#!/usr/bin/env python3

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

@dataclass
class ModuleConfig:
    name: str = "linuwu_sense"
    path: str = "~/Linuwu-Sense/src/linuwu_sense.ko"
    sysfs_base: str = "/sys/module/linuwu_sense/drivers/platform:acer-wmi/acer-wmi/predator_sense"

class PredatorSenseError(Exception):
    """Custom exception for Predator Sense operations"""
    pass

class SystemInterface:
    """Handles system-level operations and checks"""
    
    @staticmethod
    def check_root() -> bool:
        """Check if running as root"""
        return os.geteuid() == 0
    
    @staticmethod
    def restart_as_root() -> None:
        """Restart script with sudo privileges"""
        print(f"{Colors.RED}ERROR: This script must be run as root. Restarting with sudo...{Colors.RESET}")
        try:
            subprocess.run(['sudo', 'python3'] + sys.argv, check=True)
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}Failed to restart with sudo: {e}{Colors.RESET}")
            sys.exit(1)
    
    @staticmethod
    def run_command(cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run system command with error handling"""
        try:
            return subprocess.run(cmd, capture_output=capture_output, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise PredatorSenseError(f"Command failed: {' '.join(cmd)}\nError: {e.stderr}")
    
    @staticmethod
    def is_module_loaded(module_name: str) -> bool:
        """Check if kernel module is loaded"""
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True, check=True)
            return module_name in result.stdout
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def get_kernel_version() -> str:
        """Get current kernel version"""
        try:
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            raise PredatorSenseError("Failed to get kernel version")

class ModuleManager:
    """Handles kernel module operations"""
    
    def __init__(self, config: ModuleConfig):
        self.config = config
        self.module_path = Path(config.path).expanduser()
    
    def validate_module(self) -> None:
        """Validate module file and compatibility"""
        if not self.module_path.exists():
            raise PredatorSenseError(f"Kernel module not found at {self.module_path}")
        
        kernel_version = SystemInterface.get_kernel_version()
        try:
            result = subprocess.run(['modinfo', str(self.module_path)], 
                                  capture_output=True, text=True, check=True)
            if kernel_version not in result.stdout:
                raise PredatorSenseError(f"Module not compatible with kernel version ({kernel_version})")
        except subprocess.CalledProcessError:
            raise PredatorSenseError("Failed to get module information")
    
    def load_module(self) -> bool:
        """Load the kernel module"""
        if SystemInterface.is_module_loaded(self.config.name):
            print(f"{Colors.YELLOW}Module {self.config.name} is already loaded{Colors.RESET}")
            return True
        
        print(f"{Colors.YELLOW}Loading {self.config.name} module...{Colors.RESET}")
        
        try:
            self.validate_module()
            SystemInterface.run_command(['insmod', str(self.module_path)])
            time.sleep(1)  # Allow time for SysFS paths to register
            
            if SystemInterface.is_module_loaded(self.config.name):
                print(f"{Colors.GREEN}Module {self.config.name} loaded successfully{Colors.RESET}")
                return True
            else:
                raise PredatorSenseError("Module failed to load properly")
                
        except PredatorSenseError as e:
            print(f"{Colors.RED}ERROR: {e}{Colors.RESET}")
            print("Check: 1) Module path 2) Kernel compatibility 3) Hardware support")
            return False
    
    def unload_module(self) -> bool:
        """Unload the kernel module"""
        if not SystemInterface.is_module_loaded(self.config.name):
            print(f"{Colors.YELLOW}Module {self.config.name} is not loaded{Colors.RESET}")
            return True
        
        try:
            print(f"{Colors.YELLOW}Unloading {self.config.name} module...{Colors.RESET}")
            SystemInterface.run_command(['rmmod', self.config.name])
            
            if not SystemInterface.is_module_loaded(self.config.name):
                print(f"{Colors.GREEN}Module {self.config.name} unloaded successfully{Colors.RESET}")
                return True
            else:
                raise PredatorSenseError("Module failed to unload properly")
                
        except PredatorSenseError as e:
            print(f"{Colors.RED}ERROR: {e}{Colors.RESET}")
            return False
    
    def reload_module(self) -> bool:
        """Reload the kernel module"""
        print(f"{Colors.YELLOW}Reloading {self.config.name} module...{Colors.RESET}")
        return self.unload_module() and self.load_module()

class SysfsInterface:
    """Handles SysFS file operations"""
    
    def __init__(self, config: ModuleConfig):
        self.config = config
        self.paths = {
            'backlight': f"{config.sysfs_base}/backlight_timeout",
            'battery_limiter': f"{config.sysfs_base}/battery_limiter",
            'boot_animation': f"{config.sysfs_base}/boot_animation_sound",
            'fan_speed': f"{config.sysfs_base}/fan_speed",
            'lcd_override': f"{config.sysfs_base}/lcd_override",
            'usb_charging': f"{config.sysfs_base}/usb_charging",
            'battery_calibration': f"{config.sysfs_base}/battery_calibration"
        }
    
    def validate_path(self, path: str) -> None:
        """Validate SysFS path exists"""
        if not Path(path).exists():
            raise PredatorSenseError(f"SysFS interface missing! ({path})")
    
    def read_state(self, key: str) -> str:
        """Read state from SysFS file"""
        path = self.paths[key]
        self.validate_path(path)
        
        try:
            with open(path, 'r') as f:
                return f.read().strip()
        except (OSError, IOError) as e:
            raise PredatorSenseError(f"Failed to read from {path}: {e}")
    
    def write_state(self, key: str, value: str) -> None:
        """Write state to SysFS file"""
        path = self.paths[key]
        self.validate_path(path)
        
        try:
            with open(path, 'w') as f:
                f.write(str(value))
        except (OSError, IOError) as e:
            raise PredatorSenseError(f"Failed to write to {path}: {e}")
    
    def get_all_states(self) -> Dict[str, str]:
        """Get all current states"""
        states = {}
        for key in self.paths:
            try:
                states[key] = self.read_state(key)
            except PredatorSenseError:
                states[key] = "N/A"
        return states

class StateFormatters:
    """Format state values for display"""
    
    @staticmethod
    def format_binary(value: str) -> str:
        """Format binary state (0/1)"""
        return "Enabled" if value == "1" else "Disabled"
    
    @staticmethod
    def format_fan(value: str) -> str:
        """Format fan speed state"""
        fan_modes = {
            "0,0": "Auto",
            "30,30": "Quiet",
            "50,50": "Balanced", 
            "70,70": "Performance",
            "100,100": "Turbo"
        }
        return fan_modes.get(value, f"Custom ({value}%)")
    
    @staticmethod
    def format_usb(value: str) -> str:
        """Format USB charging state"""
        return "Disabled" if value == "0" else f"Until {value}%"

class MenuOption:
    """Represents a menu option"""
    def __init__(self, text: str, value: str, confirm: bool = False):
        self.text = text
        self.value = value
        self.confirm = confirm

class Menu:
    """Generic menu system"""
    
    def __init__(self, sysfs: SysfsInterface):
        self.sysfs = sysfs
    
    def get_numeric_input(self, prompt: str, min_val: int = 0, max_val: int = None) -> int:
        """Get numeric input with validation"""
        while True:
            try:
                value = int(input(prompt))
                if value >= min_val and (max_val is None or value <= max_val):
                    return value
                else:
                    range_str = f"{min_val}-{max_val}" if max_val else f">= {min_val}"
                    print(f"{Colors.RED}Invalid input! Please enter a number in range {range_str}.{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}Invalid input! Please enter a number.{Colors.RESET}")
    
    def confirm_action(self, action: str) -> bool:
        """Get confirmation for action"""
        response = input(f"Confirm {action}? (y/N): ").lower()
        return response in ['y', 'yes']
    
    def create_menu(self, title: str, key: str, formatter: Callable[[str], str], 
                   options: List[MenuOption]) -> None:
        """Create and run a generic menu"""
        while True:
            os.system('clear')
            
            try:
                current = self.sysfs.read_state(key)
                formatted_current = formatter(current)
            except PredatorSenseError as e:
                print(f"{Colors.RED}Error reading current state: {e}{Colors.RESET}")
                input("Press Enter to continue...")
                return
            
            print(f"{Colors.GREEN}=== {title} ==={Colors.RESET}")
            print(f"Current state: {Colors.CYAN}{formatted_current}{Colors.RESET}")
            print()
            
            for i, option in enumerate(options, 1):
                print(f"{i}. {option.text}")
            
            print(f"\n0. Return to main menu")
            print(f"{Colors.GREEN}{'=' * (len(title) + 8)}{Colors.RESET}")
            
            choice = self.get_numeric_input("Choice: ", 0, len(options))
            
            if choice == 0:
                print(f"{Colors.YELLOW}Returning to main menu...{Colors.RESET}")
                time.sleep(0.5)
                break
            
            option = options[choice - 1]
            
            if option.confirm and not self.confirm_action(option.text):
                print(f"{Colors.YELLOW}Cancelled!{Colors.RESET}")
                time.sleep(1)
                continue
            
            try:
                self.sysfs.write_state(key, option.value)
                print(f"{Colors.GREEN}✓ {option.text} successful!{Colors.RESET}")
                time.sleep(1)
            except PredatorSenseError as e:
                print(f"{Colors.RED}Error: {e}{Colors.RESET}")
                time.sleep(2)
    
    def fan_control_menu(self) -> None:
        """Special menu for fan control with custom option"""
        while True:
            os.system('clear')
            
            try:
                current = self.sysfs.read_state('fan_speed')
                formatted_current = StateFormatters.format_fan(current)
            except PredatorSenseError as e:
                print(f"{Colors.RED}Error reading fan speed: {e}{Colors.RESET}")
                input("Press Enter to continue...")
                return
            
            print(f"{Colors.GREEN}=== Fan Speed Control ==={Colors.RESET}")
            print(f"Current state: {Colors.CYAN}{formatted_current}{Colors.RESET}")
            print()
            print("1. Auto (system controlled)")
            print("2. Quiet (30% speed)")
            print("3. Balanced (50% speed)")
            print("4. Performance (70% speed)")
            print("5. Turbo (100% speed)")
            print("6. Custom speeds")
            print(f"\n0. Return to main menu")
            print(f"{Colors.GREEN}========================{Colors.RESET}")
            
            choice = self.get_numeric_input("Choice: ", 0, 6)
            
            if choice == 0:
                print(f"{Colors.YELLOW}Returning to main menu...{Colors.RESET}")
                time.sleep(0.5)
                break
            
            if choice <= 5:
                speeds = ["0,0", "30,30", "50,50", "70,70", "100,100"]
                try:
                    self.sysfs.write_state('fan_speed', speeds[choice - 1])
                    new_formatted = StateFormatters.format_fan(speeds[choice - 1])
                    print(f"{Colors.GREEN}✓ Fan speed set to {new_formatted}{Colors.RESET}")
                    time.sleep(1)
                except PredatorSenseError as e:
                    print(f"{Colors.RED}Error: {e}{Colors.RESET}")
                    time.sleep(2)
            
            elif choice == 6:
                cpu = self.get_numeric_input("Enter CPU fan % (0-100): ", 0, 100)
                gpu = self.get_numeric_input("Enter GPU fan % (0-100): ", 0, 100)
                
                try:
                    custom_value = f"{cpu},{gpu}"
                    self.sysfs.write_state('fan_speed', custom_value)
                    print(f"{Colors.GREEN}✓ Fan speed set to Custom ({cpu}%, {gpu}%){Colors.RESET}")
                    time.sleep(1)
                except PredatorSenseError as e:
                    print(f"{Colors.RED}Error: {e}{Colors.RESET}")
                    time.sleep(2)

class PredatorSenseControl:
    """Main application controller"""
    
    def __init__(self):
        self.config = ModuleConfig()
        self.module_manager = ModuleManager(self.config)
        self.sysfs = SysfsInterface(self.config)
        self.menu = Menu(self.sysfs)
    
    def initialize(self) -> bool:
        """Initialize the application"""
        if not SystemInterface.check_root():
            SystemInterface.restart_as_root()
        
        return self.module_manager.load_module()
    
    def module_management_menu(self) -> None:
        """Menu for module management operations"""
        while True:
            os.system('clear')
            
            is_loaded = SystemInterface.is_module_loaded(self.config.name)
            status = f"{Colors.GREEN}Loaded{Colors.RESET}" if is_loaded else f"{Colors.RED}Not Loaded{Colors.RESET}"
            
            print(f"{Colors.GREEN}=== Module Management ==={Colors.RESET}")
            print(f"Module status: {status}")
            print()
            print("1. Load module")
            print("2. Unload module") 
            print("3. Reload module")
            print(f"\n0. Return to main menu")
            print(f"{Colors.GREEN}========================{Colors.RESET}")
            
            choice = self.menu.get_numeric_input("Choice: ", 0, 3)
            
            if choice == 0:
                print(f"{Colors.YELLOW}Returning to main menu...{Colors.RESET}")
                time.sleep(0.5)
                break
            elif choice == 1:
                self.module_manager.load_module()
                time.sleep(2)
            elif choice == 2:
                self.module_manager.unload_module()
                time.sleep(2)
            elif choice == 3:
                self.module_manager.reload_module()
                time.sleep(2)
    
    def main_menu(self) -> None:
        """Main application menu"""
        while True:
            os.system('clear')
            
            # Check if module is still loaded
            if not SystemInterface.is_module_loaded(self.config.name):
                print(f"{Colors.RED}WARNING: Module {self.config.name} is not loaded!{Colors.RESET}")
                print("Please load the module first from the Module Management menu.\n")
            
            try:
                states = self.sysfs.get_all_states()
            except:
                states = {key: "N/A" for key in self.sysfs.paths}
            
            print(f"{Colors.GREEN}{Colors.BOLD}===== Predator Sense Control ====={Colors.RESET}")
            print()
            
            menu_items = [
                ("Keyboard Backlight", StateFormatters.format_binary(states.get('backlight', 'N/A'))),
                ("Battery Limiter", StateFormatters.format_binary(states.get('battery_limiter', 'N/A'))),
                ("Boot Animation/Sound", StateFormatters.format_binary(states.get('boot_animation', 'N/A'))),
                ("Fan Speed Control", StateFormatters.format_fan(states.get('fan_speed', 'N/A'))),
                ("LCD Override", StateFormatters.format_binary(states.get('lcd_override', 'N/A'))),
                ("USB Charging", StateFormatters.format_usb(states.get('usb_charging', 'N/A'))),
                ("Battery Calibration", StateFormatters.format_binary(states.get('battery_calibration', 'N/A'))),
                ("Module Management", "---")
            ]
            
            for i, (name, status) in enumerate(menu_items, 1):
                print(f"{i:2}. {name:<25} [{Colors.CYAN}{status}{Colors.RESET}]")
            
            print(f"\n 0. Exit")
            print(f"{Colors.GREEN}==================================={Colors.RESET}")
            
            choice = self.menu.get_numeric_input("Select feature: ", 0, len(menu_items))
            
            if choice == 0:
                print(f"{Colors.GREEN}Exiting...{Colors.RESET}")
                break
            
            # Check if module is loaded for hardware control options
            if choice <= 7 and not SystemInterface.is_module_loaded(self.config.name):
                print(f"{Colors.RED}Module not loaded! Please load the module first.{Colors.RESET}")
                time.sleep(2)
                continue
            
            if choice == 1:
                self.menu.create_menu("Keyboard Backlight Timeout", "backlight", 
                                    StateFormatters.format_binary, [
                    MenuOption("Enable timeout (turns off when inactive)", "1"),
                    MenuOption("Disable timeout (always on)", "0")
                ])
            elif choice == 2:
                self.menu.create_menu("Battery Charge Limiter", "battery_limiter", 
                                    StateFormatters.format_binary, [
                    MenuOption("Enable (80% limit)", "1"),
                    MenuOption("Disable (full charge)", "0")
                ])
            elif choice == 3:
                self.menu.create_menu("Boot Animation/Sound", "boot_animation", 
                                    StateFormatters.format_binary, [
                    MenuOption("Enable animation/sound", "1"),
                    MenuOption("Disable animation/sound", "0")
                ])
            elif choice == 4:
                self.menu.fan_control_menu()
            elif choice == 5:
                self.menu.create_menu("LCD Override", "lcd_override", 
                                    StateFormatters.format_binary, [
                    MenuOption("Enable override", "1"),
                    MenuOption("Disable override", "0")
                ])
            elif choice == 6:
                self.menu.create_menu("USB Charging Control", "usb_charging", 
                                    StateFormatters.format_usb, [
                    MenuOption("Disable charging", "0"),
                    MenuOption("Enable until 10% battery", "10"),
                    MenuOption("Enable until 20% battery", "20"),
                    MenuOption("Enable until 30% battery", "30")
                ])
            elif choice == 7:
                self.menu.create_menu("Battery Calibration", "battery_calibration", 
                                    StateFormatters.format_binary, [
                    MenuOption("Start calibration (requires AC)", "1", confirm=True),
                    MenuOption("Stop calibration", "0")
                ])
            elif choice == 8:
                self.module_management_menu()
    
    def run(self) -> None:
        """Run the application"""
        try:
            if self.initialize():
                self.main_menu()
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}Unexpected error: {e}{Colors.RESET}")
            sys.exit(1)

if __name__ == "__main__":
    app = PredatorSenseControl()
    app.run()
