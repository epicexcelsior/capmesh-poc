"""Collect two selected BLE contacts once. No payment, output GPIO, or automatic retry.

Run from the repository root with python -m scripts.check_contact_pair.
The parent snapshots public pins before it starts a bounded worker process.
"""

import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

from capmesh.corroboration import ContactObserver, ContactPairVerifier
from capmesh.pair_collection import collect_contact_pair
from capmesh.protocol.identity import ReceiptPublicKey, provisioned_observation_keys

ROOT = Path(__file__).resolve().parents[1]


def observers_from_profile(profile):
    if not isinstance(profile, dict) or set(profile) != {"observers"} or not isinstance(profile["observers"], list):
        raise ValueError("Supply an explicit public observer profile")
    observers = []
    for row in profile["observers"]:
        if not isinstance(row, dict) or set(row) != {"provider", "sensor", "public_key_sec1_hex"}:
            raise ValueError("Each observer requires exactly its provider, sensor, and public pin")
        observers.append(ContactObserver(row["provider"], row["sensor"], ReceiptPublicKey(row["public_key_sec1_hex"])))
    ContactPairVerifier(observers)
    return observers


def public_profile(observer_specs, pins_path):
    if not isinstance(observer_specs, list) or len(observer_specs) != 2:
        raise ValueError("Select exactly two --observer provider:sensor values")
    selections = []
    for specification in observer_specs:
        if not isinstance(specification, str) or specification.count(":") != 1:
            raise ValueError("Select each observer as provider:sensor")
        selections.append(specification.split(":"))
    pins = provisioned_observation_keys(ROOT / pins_path)
    if any(provider not in pins for provider, _ in selections):
        raise ValueError("Each selected provider requires its own independently provisioned public pin")
    profile = {"observers": [{"provider": provider, "sensor": sensor, "public_key_sec1_hex": pins[provider].sec1_hex}
                             for provider, sensor in selections]}
    observers_from_profile(profile)
    return profile


async def run_diagnostic(profile, *, timeout=45):
    if os.name != "posix":
        raise ValueError("The bounded BLE pair runner requires POSIX process groups")
    if type(timeout) is not int or not 1 <= timeout <= 60:
        raise ValueError("Worker timeout must be an integer from 1 through 60 seconds")
    profile = deepcopy(profile)
    observers = observers_from_profile(profile)
    from scripts.soak_observations import WorkerCleanupError, run_sample
    cleanup_confirmed = True
    try:
        result = await run_sample(timeout, command=[sys.executable, "-m", "scripts.check_contact_pair",
            "--worker-profile", json.dumps(profile, separators=(",", ":"))])
    except (TimeoutError, RuntimeError, ValueError, OSError) as error:
        # Preserve an unreaped worker as a separate operator failure. A WAIT result never certifies cleanup.
        cleanup_confirmed = not isinstance(error, WorkerCleanupError)
        result = {"payment_mode": "none; no funds moved", "received_receipts": {}, "challenges": {},
                  "pair": ContactPairVerifier(observers).verify({}),
                  "collection": {"transport": "ble", "errors": [{"reason": f"WORKER_FAILED: {type(error).__name__}"}]}}
        if not cleanup_confirmed:
            result["collection"]["errors"][0]["action"] = "Stop BLE work. Inspect and stop the remaining worker before another observation."
            if error.worker_pid is not None:
                result["collection"]["errors"][0]["worker_pid"] = error.worker_pid
    result["mode"] = "LIVE BLE CONTACT DEMO"
    result["worker_deadline_seconds"] = timeout
    result["worker_cleanup_confirmed"] = cleanup_confirmed
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observer", action="append", help="Selected provider:sensor; supply exactly twice")
    parser.add_argument("--pins", help="Trusted public pin file, relative to the repository root or absolute")
    parser.add_argument("--timeout", type=int, default=45, help="Whole-worker deadline, 1–60 seconds")
    parser.add_argument("--worker-profile", help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    try:
        if arguments.worker_profile is not None:
            observers = observers_from_profile(json.loads(arguments.worker_profile))
            result = asyncio.run(collect_contact_pair(observers))
        else:
            if not arguments.pins:
                raise ValueError("Select a trusted --pins file before BLE access")
            result = asyncio.run(run_diagnostic(public_profile(arguments.observer, arguments.pins), timeout=arguments.timeout))
        print(json.dumps(result, indent=2, allow_nan=False))
        # The worker reports an unmet pair as data. Only the parent sets the diagnostic's policy exit status.
        return 0 if arguments.worker_profile is not None or result["pair"]["status"] == "verified-pair" else 1
    except (ValueError, OSError) as error:
        print(f"Contact-pair configuration failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
