"""ADB wrapper: pull the SMS inbox from a connected Android phone."""

import os
import re
import subprocess

# Rows arrive as "Row: <n> _id=..., address=..., date=..., body=..." where only
# _id, date are guaranteed single-token, so split on row-start lines and take
# the body as everything after "body=" (may contain commas and newlines).
ROW_START = re.compile(r"(?m)^Row: \d+ _id=(\d+), address=(.*), date=(\d+), body=")


def adb_path():
    return os.environ.get("MSGR_ADB", "adb")


def run_adb(args, serial=None):
    cmd = [adb_path()]
    if serial:
        cmd += ["-s", serial]
    cmd += args
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise RuntimeError(f"adb {' '.join(args)} failed: {detail}")
    return proc.stdout


def list_devices():
    out = run_adb(["devices", "-l"])
    devices = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def resolve_serial(requested=None):
    serial = requested or os.environ.get("MSGR_SERIAL")
    if serial:
        return serial
    devices = list_devices()
    if not devices:
        raise RuntimeError(
            "No Android device connected. Plug in the phone with USB debugging "
            "enabled, or set MSGR_SERIAL."
        )
    if len(devices) > 1:
        raise RuntimeError(
            "Multiple devices connected: " + ", ".join(devices) +
            ". Pick one with --serial or MSGR_SERIAL."
        )
    return devices[0]


def parse_rows(output):
    """Parse `content query` output into dicts: id, address, date_ms, body."""
    matches = list(ROW_START.finditer(output))
    messages = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(output)
        body = output[m.end():end].strip().replace("\r", "")
        messages.append(
            {
                "id": int(m.group(1)),
                "address": m.group(2),
                "date_ms": int(m.group(3)),
                "body": body,
            }
        )
    return messages


def fetch_inbox(serial=None):
    """Return the phone's SMS inbox, oldest first."""
    serial = resolve_serial(serial)
    out = run_adb(
        [
            "exec-out",
            "content",
            "query",
            "--uri",
            "content://sms/inbox",
            "--projection",
            "_id,address,date,body",
        ],
        serial,
    )
    messages = parse_rows(out)
    messages.sort(key=lambda m: (m["date_ms"], m["id"]))
    return serial, messages
