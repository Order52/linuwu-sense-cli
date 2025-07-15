#!/bin/bash

# Module configuration
MODULE_NAME="linuwu_sense"
MODULE_PATH="~/.scripts/Acer/PredatorSense/Linuwu-Sense/src/linuwu_sense.ko"

# SysFS paths
SYSFS_BASE="/sys/module/linuwu_sense/drivers/platform:acer-wmi/acer-wmi/predator_sense"
declare -A PATHS=(
    [backlight]="$SYSFS_BASE/backlight_timeout"
    [battery_limiter]="$SYSFS_BASE/battery_limiter"
    [boot_animation]="$SYSFS_BASE/boot_animation_sound"
    [fan_speed]="$SYSFS_BASE/fan_speed"
    [lcd_override]="$SYSFS_BASE/lcd_override"
    [usb_charging]="$SYSFS_BASE/usb_charging"
    [battery_calibration]="$SYSFS_BASE/battery_calibration"
)

# Color handling with tput for portability
RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
NC=$(tput sgr0)

# System checks
check_root() {
    [ "$(id -u)" -ne 0 ] && {
        echo -e "${RED}ERROR: This script must be run as root. Restarting with sudo...${NC}"
        exec sudo "$0" "$@"
        exit $?
    }
}

check_module() {
    if ! lsmod | grep -q "$MODULE_NAME"; then
        echo -e "${YELLOW}Loading $MODULE_NAME module...${NC}"
        if [ ! -f "$MODULE_PATH" ]; then
            echo -e "${RED}ERROR: Kernel module not found at $MODULE_PATH${NC}"
            exit 1
        fi
        KERNEL_VERSION=$(uname -r)
        if ! modinfo "$MODULE_PATH" | grep -q "$KERNEL_VERSION"; then
            echo -e "${RED}ERROR: Module not compatible with kernel version ($KERNEL_VERSION)${NC}"
            exit 1
        fi
        if ! insmod "$MODULE_PATH"; then
            echo -e "${RED}ERROR: Failed to load module!${NC}"
            echo "Check: 1) Module path: $MODULE_PATH 2) Kernel compatibility 3) Hardware support"
            exit 1
        fi
        sleep 1  # Allow time for SysFS paths to register
    fi
}

# Core functions
validate_path() {
    [ -f "$1" ] || {
        echo -e "${RED}ERROR: SysFS interface missing! ($1)${NC}"
        echo "Possible causes: 1) Module not loaded 2) Kernel mismatch 3) Hardware unsupported"
        exit 1
    }
}

read_state() { validate_path "$1"; cat "$1" 2>/dev/null; }

write_state() {
    validate_path "$1"
    echo "$2" | tee "$1" >/dev/null || {
        echo -e "${RED}ERROR: Failed to write value!${NC}"
        echo "Check: 1) File permissions: $1 2) Valid input value: $2 3) Hardware support"
        return 1
    }
}

# Menu utilities
return_prompt() { echo -e "\n${YELLOW}Returning to main menu...${NC}"; sleep 1; }

numeric_input() {
    while :; do
        read -p "$1" input
        [[ "$input" =~ ^[0-9]+$ ]] && { echo "$input"; return; }
        echo -e "${RED}Invalid input! Please enter a number.${NC}"
    done
}

# State formatters
format_binary() { [ "$1" -eq 1 ] && echo "Enabled" || echo "Disabled"; }
format_fan() {
    case "$1" in
        "0,0") echo "Auto" ;;
        "30,30") echo "Quiet" ;;
        "50,50") echo "Balanced" ;;
        "70,70") echo "Performance" ;;
        "100,100") echo "Turbo" ;;
        *) echo "Custom ($1%)" ;;
    esac
}
format_usb() { [ "$1" -eq 0 ] && echo "Disabled" || echo "Until $1%"; }

# Generic menu system
create_menu() {
    local title=$1 sysfs_path=$2 format_current=$3
    shift 3
    local options=("$@")

    while :; do
        clear
        current=$(read_state "$sysfs_path")
        echo -e "${GREEN}=== $title ===${NC}"
        echo "Current state: $($format_current "$current")"

        for i in "${!options[@]}"; do
            printf "%d. %s\n" $((i+1)) "${options[i]%%|*}"
        done

        echo -e "\n0. Return to main menu"
        choice=$(numeric_input "Choice (0-${#options[@]}): ")

        case $choice in
            0) return_prompt; return ;;
            *)
                if (( choice <= ${#options[@]} )); then
                    IFS='|' read -r action value <<< "${options[$((choice-1))]}"
                    if [ "$action" = "confirm" ]; then
                        read -p "Confirm $value? (y/N): " confirm
                        [[ "$confirm" =~ [Yy] ]] || { echo -e "${YELLOW}Cancelled!${NC}"; continue; }
                    fi
                    write_state "$sysfs_path" "$value" && echo -e "${GREEN}${action^} successful!${NC}"
                    sleep 1
                else
                    echo -e "${RED}Invalid option!${NC}"; sleep 1
                fi
                ;;
        esac
    done
}

# Fan speed menu
fan_control_menu() {
    while :; do
        clear
        current=$(read_state "${PATHS[fan_speed]}")
        echo -e "${GREEN}=== Fan Speed Control ===${NC}"
        echo "Current state: $(format_fan "$current")"
        echo "1. Auto (system controlled)"
        echo "2. Quiet (30% speed)"
        echo "3. Balanced (50% speed)"
        echo "4. Performance (70% speed)"
        echo "5. Turbo (100% speed)"
        echo "6. Custom speeds"
        echo -e "\n0. Return to main menu"

        choice=$(numeric_input "Choice (0-6): ")
        case $choice in
            0) return_prompt; break ;;
            [1-5])
                speeds=("0,0" "30,30" "50,50" "70,70" "100,100")
                write_state "${PATHS[fan_speed]}" "${speeds[$((choice-1))]}" &&
                    echo -e "${GREEN}Fan speed set to $(format_fan "${speeds[$((choice-1))]}")${NC}"
                ;;
            6)
                cpu=$(numeric_input "Enter CPU fan % (0-100): ")
                gpu=$(numeric_input "Enter GPU fan % (0-100): ")
                if [[ "$cpu" =~ ^[0-9]+$ && "$gpu" =~ ^[0-9]+$ && "$cpu" -le 100 && "$gpu" -le 100 ]]; then
                    write_state "${PATHS[fan_speed]}" "$cpu,$gpu" &&
                        echo -e "${GREEN}Fan speed set to Custom ($cpu%, $gpu%)${NC}"
                else
                    echo -e "${RED}Invalid values! Must be 0-100.${NC}"
                fi
                ;;
            *) echo -e "${RED}Invalid option!${NC}"
        esac
        sleep 1
    done
}

# Main menu with current states
main_menu() {
    check_root "$@"
    check_module

    while :; do
        clear
        echo -e "${GREEN}===== Predator Sense Control =====${NC}"
        backlight_state=$(format_binary "$(read_state "${PATHS[backlight]}")")
        battery_limiter_state=$(format_binary "$(read_state "${PATHS[battery_limiter]}")")
        boot_animation_state=$(format_binary "$(read_state "${PATHS[boot_animation]}")")
        fan_state=$(format_fan "$(read_state "${PATHS[fan_speed]}")")
        lcd_override_state=$(format_binary "$(read_state "${PATHS[lcd_override]}")")
        usb_charging_state=$(format_usb "$(read_state "${PATHS[usb_charging]}")")
        battery_calibration_state=$(format_binary "$(read_state "${PATHS[battery_calibration]}")")

        printf "%-2s %-25s %s\n" "1." "Keyboard Backlight" "[$backlight_state]"
        printf "%-2s %-25s %s\n" "2." "Battery Limiter" "[$battery_limiter_state]"
        printf "%-2s %-25s %s\n" "3." "Boot Animation/Sound" "[$boot_animation_state]"
        printf "%-2s %-25s %s\n" "4." "Fan Speed Control" "[$fan_state]"
        printf "%-2s %-25s %s\n" "5." "LCD Override" "[$lcd_override_state]"
        printf "%-2s %-25s %s\n" "6." "USB Charging" "[$usb_charging_state]"
        printf "%-2s %-25s %s\n" "7." "Battery Calibration" "[$battery_calibration_state]"
        echo -e "\n0. Exit"
        echo -e "${GREEN}==================================${NC}"

        choice=$(numeric_input "Select feature (0-7): ")
        case $choice in
            0) echo -e "${GREEN}Exiting...${NC}"; exit 0 ;;
            1) create_menu "Keyboard Backlight Timeout" "${PATHS[backlight]}" format_binary \
                "Enable timeout (turns off when inactive)|1" \
                "Disable timeout (always on)|0" ;;
            2) create_menu "Battery Charge Limiter" "${PATHS[battery_limiter]}" format_binary \
                "Enable (80% limit)|1" \
                "Disable (full charge)|0" ;;
            3) create_menu "Boot Animation/Sound" "${PATHS[boot_animation]}" format_binary \
                "Enable animation/sound|1" \
                "Disable animation/sound|0" ;;
            4) fan_control_menu ;;
            5) create_menu "LCD Override" "${PATHS[lcd_override]}" format_binary \
                "Enable override|1" \
                "Disable override|0" ;;
            6) create_menu "USB Charging Control" "${PATHS[usb_charging]}" format_usb \
                "Disable charging|0" \
                "Enable until 10% battery|10" \
                "Enable until 20% battery|20" \
                "Enable until 30% battery|30" ;;
            7) create_menu "Battery Calibration" "${PATHS[battery_calibration]}" format_binary \
                "Start calibration (requires AC)|1|confirm" \
                "Stop calibration|0" ;;
            *) echo -e "${RED}Invalid option!${NC}"; sleep 1
        esac
    done
}

main_menu "$@"
