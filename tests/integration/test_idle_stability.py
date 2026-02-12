"""
Idle Stability Test Script for WhisperLocal

This script stress-tests the keyboard library over extended periods to help
reproduce and diagnose the issue where the app stops working after idle.

Run this script to monitor for:
- Phantom key presses
- Keyboard library errors
- State inconsistencies

Usage:
    python test_idle_stability.py [--duration MINUTES] [--interval SECONDS]

Options:
    --duration: How long to run the test (default: 60 minutes)
    --interval: How often to check keyboard state (default: 0.5 seconds)
"""

import keyboard
import time
import argparse
import sys
import os
from datetime import datetime
from collections import defaultdict

# Keys to monitor for phantom presses
MONITORED_KEYS = [
    "esc", "f8", "f9", "windows", "ctrl", "alt", "shift",
    "j", "d", "b", "s"  # Used in hotkey combos
]

# Statistics
stats = {
    "total_checks": 0,
    "errors": 0,
    "phantom_presses": defaultdict(int),
    "start_time": None,
    "last_error": None,
    "error_details": [],
}


def log(message, level="INFO"):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [{level}] {message}")
    
    # Also write to log file
    log_file = os.path.join(os.path.dirname(__file__), "idle_stability_test.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{level}] {message}\n")


def check_keyboard_state():
    """Check state of all monitored keys and detect anomalies."""
    pressed_keys = []
    errors = []
    
    for key in MONITORED_KEYS:
        try:
            is_pressed = keyboard.is_pressed(key)
            if is_pressed:
                pressed_keys.append(key)
        except Exception as e:
            errors.append(f"{key}: {e}")
    
    return pressed_keys, errors


def run_stability_test(duration_minutes=60, interval_seconds=0.5):
    """Run the stability test for the specified duration."""
    stats["start_time"] = time.time()
    end_time = stats["start_time"] + (duration_minutes * 60)
    
    log(f"Starting idle stability test")
    log(f"Duration: {duration_minutes} minutes")
    log(f"Check interval: {interval_seconds} seconds")
    log(f"Monitored keys: {', '.join(MONITORED_KEYS)}")
    log("=" * 60)
    log("Press Ctrl+C to stop the test early")
    log("")
    
    last_status_time = time.time()
    status_interval = 60  # Print status every minute
    
    try:
        while time.time() < end_time:
            stats["total_checks"] += 1
            
            pressed_keys, errors = check_keyboard_state()
            
            # Log any errors
            if errors:
                stats["errors"] += 1
                stats["last_error"] = time.time()
                for error in errors:
                    log(f"KEYBOARD ERROR: {error}", "ERROR")
                    stats["error_details"].append({
                        "time": time.time(),
                        "error": error,
                        "check_num": stats["total_checks"]
                    })
            
            # Log any phantom key presses (keys pressed when user isn't touching keyboard)
            # We expect no keys to be pressed during idle
            if pressed_keys:
                for key in pressed_keys:
                    stats["phantom_presses"][key] += 1
                log(f"PHANTOM PRESS DETECTED: {', '.join(pressed_keys)}", "WARNING")
            
            # Print periodic status
            if time.time() - last_status_time >= status_interval:
                elapsed = (time.time() - stats["start_time"]) / 60
                remaining = (end_time - time.time()) / 60
                phantom_count = sum(stats["phantom_presses"].values())
                log(f"STATUS: {elapsed:.1f}min elapsed, {remaining:.1f}min remaining, "
                    f"{stats['total_checks']} checks, {stats['errors']} errors, "
                    f"{phantom_count} phantom presses")
                last_status_time = time.time()
            
            time.sleep(interval_seconds)
    
    except KeyboardInterrupt:
        log("\nTest interrupted by user", "INFO")
    
    # Print final summary
    print_summary()


def print_summary():
    """Print test summary statistics."""
    elapsed = (time.time() - stats["start_time"]) / 60
    
    log("")
    log("=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)
    log(f"Total runtime: {elapsed:.1f} minutes")
    log(f"Total checks: {stats['total_checks']}")
    log(f"Keyboard errors: {stats['errors']}")
    
    phantom_count = sum(stats["phantom_presses"].values())
    log(f"Phantom key presses: {phantom_count}")
    
    if stats["phantom_presses"]:
        log("Phantom presses by key:")
        for key, count in sorted(stats["phantom_presses"].items(), key=lambda x: -x[1]):
            log(f"  {key}: {count}")
    
    if stats["error_details"]:
        log("\nError timeline (first 10):")
        for err in stats["error_details"][:10]:
            err_time = datetime.fromtimestamp(err["time"]).strftime("%H:%M:%S")
            log(f"  [{err_time}] Check #{err['check_num']}: {err['error']}")
    
    log("=" * 60)
    
    # Verdict
    if stats["errors"] == 0 and phantom_count == 0:
        log("RESULT: PASS - No issues detected", "INFO")
    elif phantom_count > 0 and stats["errors"] == 0:
        log("RESULT: WARNING - Phantom key presses detected (possible cause of idle crash)", "WARNING")
    elif stats["errors"] > 0:
        log("RESULT: FAIL - Keyboard library errors detected", "ERROR")
    else:
        log("RESULT: FAIL - Multiple issues detected", "ERROR")


def test_hotkey_registration():
    """Test if hotkey registration causes issues."""
    log("Testing hotkey registration...")
    
    test_hotkeys = [
        ("f8", "F8 key"),
        ("f9", "F9 key"),
        ("ctrl+alt+j", "Ctrl+Alt+J"),
        ("ctrl+alt+d", "Ctrl+Alt+D"),
    ]
    
    callbacks_triggered = defaultdict(int)
    
    def make_callback(name):
        def callback(e=None):
            callbacks_triggered[name] += 1
            log(f"CALLBACK TRIGGERED: {name}", "WARNING")
        return callback
    
    # Register hotkeys
    for hotkey, name in test_hotkeys:
        try:
            if "+" in hotkey:
                keyboard.add_hotkey(hotkey, make_callback(name))
            else:
                keyboard.on_press_key(hotkey, make_callback(name))
            log(f"Registered: {name}")
        except Exception as e:
            log(f"Failed to register {name}: {e}", "ERROR")
    
    log("Hotkeys registered. Monitoring for 30 seconds...")
    
    # Monitor for unexpected callbacks
    for _ in range(60):
        time.sleep(0.5)
    
    if callbacks_triggered:
        log(f"UNEXPECTED CALLBACKS: {dict(callbacks_triggered)}", "WARNING")
    else:
        log("No unexpected callbacks during monitoring period")
    
    # Cleanup
    keyboard.unhook_all()
    log("Hotkeys unhooked")


def main():
    parser = argparse.ArgumentParser(description="Test keyboard library idle stability")
    parser.add_argument("--duration", type=int, default=60,
                       help="Test duration in minutes (default: 60)")
    parser.add_argument("--interval", type=float, default=0.5,
                       help="Check interval in seconds (default: 0.5)")
    parser.add_argument("--hotkey-test", action="store_true",
                       help="Run hotkey registration test instead of idle test")
    
    args = parser.parse_args()
    
    # Clear log file
    log_file = os.path.join(os.path.dirname(__file__), "idle_stability_test.log")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Idle Stability Test Log - {datetime.now()}\n")
        f.write("=" * 60 + "\n\n")
    
    if args.hotkey_test:
        test_hotkey_registration()
    else:
        run_stability_test(args.duration, args.interval)


if __name__ == "__main__":
    main()

