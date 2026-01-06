#!/usr/bin/env python3
"""
R-MOS WebSocket Debug Tool

Usage:
    python ws_debug.py [command]

Commands:
    test        - Test connection and validate messages (default)
    frequency   - Measure message push frequency
    monitor     - Continuously monitor messages
    faults      - Check active faults in telemetry
    full        - Run full diagnostic

Examples:
    python ws_debug.py test
    python ws_debug.py frequency
    python ws_debug.py monitor --count 20
    python ws_debug.py full
"""

import asyncio
import json
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

# Install websockets if not available
try:
    import websockets
except ImportError:
    print("Installing websockets package...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets", "-q"])
    import websockets


# Configuration
WS_URL = "ws://localhost:8000/ws/robot/status"
HEALTH_URL = "http://localhost:8000/api/v1/health"
EXPECTED_FREQUENCY_HZ = 5.0
FREQUENCY_TOLERANCE = 1.0  # +/- 1Hz


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")


def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}! {msg}{Colors.RESET}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")


def validate_message(data: Dict[str, Any]) -> List[str]:
    """
    Validate WebSocket message against R-MOS schema (骨架文档 §4.4)
    Returns list of validation errors
    """
    errors = []

    # Check type field
    if data.get("type") != "telemetry":
        errors.append(f"Invalid type: expected 'telemetry', got '{data.get('type')}'")

    # Check timestamp
    if "timestamp" not in data:
        errors.append("Missing 'timestamp' field")
    else:
        try:
            # Validate ISO 8601 format
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"Invalid timestamp format: {data['timestamp']}")

    # Check payload
    if "payload" not in data:
        errors.append("Missing 'payload' field")
    else:
        payload = data["payload"]

        # Check joints
        if "joints" not in payload:
            errors.append("Missing 'payload.joints' field")
        elif not isinstance(payload["joints"], list):
            errors.append("'payload.joints' must be an array")
        else:
            for i, joint in enumerate(payload["joints"]):
                required_fields = ["joint_id", "position", "velocity"]
                for field in required_fields:
                    if field not in joint:
                        errors.append(f"Joint[{i}] missing required field: {field}")

        # Check sensors
        if "sensors" not in payload:
            errors.append("Missing 'payload.sensors' field")

        # Check active_faults
        if "active_faults" not in payload:
            errors.append("Missing 'payload.active_faults' field")
        elif not isinstance(payload["active_faults"], list):
            errors.append("'payload.active_faults' must be an array")

    return errors


async def check_backend_health() -> bool:
    """Check if backend is running and healthy"""
    try:
        import urllib.request
        with urllib.request.urlopen(HEALTH_URL, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data.get("status") == "healthy"
    except Exception:
        return False


async def test_connection(message_count: int = 5) -> bool:
    """Test WebSocket connection and validate messages"""
    print_header("WebSocket Connection Test")

    # Check backend first
    print_info(f"Checking backend health at {HEALTH_URL}...")
    if await check_backend_health():
        print_success("Backend is healthy")
    else:
        print_error("Backend is not responding")
        print_info("Start backend with: python r-mos-backend/main.py")
        return False

    print_info(f"Connecting to {WS_URL}...")

    try:
        async with websockets.connect(WS_URL, ping_interval=30) as ws:
            print_success("Connected successfully!")
            print()

            valid_count = 0
            invalid_count = 0

            for i in range(message_count):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(msg)
                    errors = validate_message(data)

                    if errors:
                        invalid_count += 1
                        print_error(f"Message {i+1}/{message_count}: INVALID")
                        for e in errors:
                            print(f"    - {e}")
                    else:
                        valid_count += 1
                        joints_count = len(data["payload"]["joints"])
                        faults = data["payload"]["active_faults"]
                        print_success(f"Message {i+1}/{message_count}: VALID | Joints: {joints_count} | Faults: {len(faults)}")

                except asyncio.TimeoutError:
                    print_error(f"Message {i+1}: Timeout (no message received)")
                    invalid_count += 1

            print()
            print(f"Results: {valid_count}/{message_count} messages valid")

            if invalid_count == 0:
                print_success("All messages conform to schema!")
                return True
            else:
                print_warning(f"{invalid_count} messages had issues")
                return False

    except ConnectionRefusedError:
        print_error("Connection refused - Backend not running")
        return False
    except Exception as e:
        print_error(f"Error: {type(e).__name__}: {e}")
        return False


async def measure_frequency(sample_count: int = 20) -> Optional[float]:
    """Measure WebSocket message push frequency"""
    print_header("Message Frequency Test")

    print_info(f"Measuring frequency over {sample_count} messages...")

    try:
        async with websockets.connect(WS_URL) as ws:
            timestamps = []

            for i in range(sample_count):
                await ws.recv()
                timestamps.append(time.time())
                print(f"\r  Collecting samples: {i+1}/{sample_count}", end="", flush=True)

            print()

            intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            avg_interval = sum(intervals) / len(intervals)
            min_interval = min(intervals)
            max_interval = max(intervals)
            frequency = 1.0 / avg_interval

            print()
            print(f"  Average interval: {avg_interval*1000:.1f}ms")
            print(f"  Min interval:     {min_interval*1000:.1f}ms")
            print(f"  Max interval:     {max_interval*1000:.1f}ms")
            print(f"  Frequency:        {frequency:.2f}Hz")
            print(f"  Expected:         {EXPECTED_FREQUENCY_HZ}Hz (200ms)")
            print()

            if abs(frequency - EXPECTED_FREQUENCY_HZ) <= FREQUENCY_TOLERANCE:
                print_success(f"Frequency is within acceptable range ({EXPECTED_FREQUENCY_HZ}Hz ± {FREQUENCY_TOLERANCE}Hz)")
                return frequency
            else:
                print_warning(f"Frequency is outside expected range")
                print_info("Check WEBSOCKET_PUSH_FREQUENCY in .env")
                return frequency

    except Exception as e:
        print_error(f"Error: {type(e).__name__}: {e}")
        return None


async def monitor_messages(count: int = 10):
    """Continuously monitor WebSocket messages"""
    print_header("WebSocket Monitor")

    print_info(f"Monitoring {count} messages (Ctrl+C to stop)...")
    print()

    try:
        async with websockets.connect(WS_URL) as ws:
            for i in range(count):
                msg = await ws.recv()
                data = json.loads(msg)

                timestamp = data.get("timestamp", "N/A")
                joints = data.get("payload", {}).get("joints", [])
                faults = data.get("payload", {}).get("active_faults", [])
                sensors = data.get("payload", {}).get("sensors", {})

                print(f"{Colors.CYAN}[{i+1:3d}]{Colors.RESET} {timestamp}")

                # Show joint summary
                joint_temps = [j.get("temperature", 0) for j in joints if j.get("temperature")]
                avg_temp = sum(joint_temps) / len(joint_temps) if joint_temps else 0
                print(f"      Joints: {len(joints)} | Avg Temp: {avg_temp:.1f}°C")

                # Show sensors
                battery = sensors.get("battery", "N/A")
                print(f"      Battery: {battery}%")

                # Show faults
                if faults:
                    print(f"      {Colors.RED}Faults: {', '.join(faults)}{Colors.RESET}")

                print()

    except KeyboardInterrupt:
        print("\nMonitoring stopped")
    except Exception as e:
        print_error(f"Error: {type(e).__name__}: {e}")


async def check_faults():
    """Check for active faults in telemetry"""
    print_header("Fault Status Check")

    try:
        async with websockets.connect(WS_URL) as ws:
            msg = await ws.recv()
            data = json.loads(msg)

            faults = data.get("payload", {}).get("active_faults", [])
            joints = data.get("payload", {}).get("joints", [])

            if faults:
                print_warning(f"Active faults: {len(faults)}")
                for fault in faults:
                    print(f"  - {Colors.RED}{fault}{Colors.RESET}")
            else:
                print_success("No active faults")

            print()

            # Check joints for error codes
            joints_with_errors = [j for j in joints if j.get("error_code")]
            if joints_with_errors:
                print_warning("Joints with errors:")
                for joint in joints_with_errors:
                    print(f"  - {joint['joint_id']}: {Colors.RED}{joint['error_code']}{Colors.RESET}")
            else:
                print_success("No joint errors")

    except Exception as e:
        print_error(f"Error: {type(e).__name__}: {e}")


async def run_full_diagnostic():
    """Run complete diagnostic suite"""
    print_header("R-MOS WebSocket Full Diagnostic")

    results = {}

    # Test 1: Connection
    print(f"\n{Colors.BOLD}Test 1: Connection & Schema Validation{Colors.RESET}")
    results["connection"] = await test_connection(5)

    # Test 2: Frequency
    print(f"\n{Colors.BOLD}Test 2: Message Frequency{Colors.RESET}")
    freq = await measure_frequency(10)
    results["frequency"] = freq is not None and abs(freq - EXPECTED_FREQUENCY_HZ) <= FREQUENCY_TOLERANCE

    # Test 3: Faults
    print(f"\n{Colors.BOLD}Test 3: Fault Detection{Colors.RESET}")
    await check_faults()
    results["faults"] = True  # Always passes (just informational)

    # Summary
    print_header("Diagnostic Summary")

    all_passed = all(results.values())

    for test, passed in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {test.capitalize():20s} [{status}]")

    print()
    if all_passed:
        print_success("All tests passed!")
    else:
        print_warning("Some tests failed - see details above")

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="R-MOS WebSocket Debug Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="test",
        choices=["test", "frequency", "monitor", "faults", "full"],
        help="Debug command to run (default: test)"
    )

    parser.add_argument(
        "--count", "-c",
        type=int,
        default=10,
        help="Number of messages to process (for monitor command)"
    )

    args = parser.parse_args()

    if args.command == "test":
        asyncio.run(test_connection())
    elif args.command == "frequency":
        asyncio.run(measure_frequency())
    elif args.command == "monitor":
        asyncio.run(monitor_messages(args.count))
    elif args.command == "faults":
        asyncio.run(check_faults())
    elif args.command == "full":
        success = asyncio.run(run_full_diagnostic())
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
