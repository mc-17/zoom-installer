# Zoom

A vulnerability has been discovered in the way Zoom initiates
the installation of an update package which, when paired with
a command injection vulnerability, can lead to a privilege escalation

This is only really useful if you already have execution, and want to
take an opportunity to escalate.

Zoom are fine with this as the user needs to enter a password (to update 
Zoom)

Tested: Injected against 6.0.10 updating to 6.0.11 (at the time of writing,
the most recent version)

## Background

Zoom provides an in-app update option (`zoom` -> `check for updates...`) as well
as regular prompts when an update is available after a user ends a call.

For many operations, Zoom makes use of a privileged helper tool, however
when installing an update `Installer` is run from the main process.

The impact of this is that any other local process at user permissions can
send signals to the process to fake a freeze or kill it.

When paired with a command injection bug, a local process
can achieve execution as a child of `package_script_service`, which runs
as root.

## Command Injection

Like many other applications, Zoom has `preinstall` and `postinstall`
scripts.

In `postinstall`, the script attempts to resolve the `USER` environment
variable to a real value if it's ran as root:

```
if [[ $USER == root ]] ; then
    # USER=$(stat -f "%Su" ~)
    USER=$(stat -f '%Su' /dev/console)
    LOG_PATH=/Library/Logs/zoomusinstall.log
fi
```

Following this, it deletes any existing log file, and then creates a new one:

```
sudo --user=$USER echo "["$(date)"] user : $USER ">>"$LOG_PATH"
```

However, if `USER` isn't `root`, then the provided value is used. As
`package_script_service` doesn't sanitise any environment variables
apart from `PATH`, a user can start the package with e.g:

```USER=root /usr/bin/python3 /tmp/zoom_payload.py```

Which expands the above command to

```
sudo --user=root /usr/bin/python3 /tmp/zoom_payload.py echo "["$(date)"] user : $USER ">>"$LOG_PATH"
```

Achieving execution. Some effort must be taken to only call your payload on the first `sudo echo` call,
as there are many, however this is simple with a file lock

## Exploitation

1. Local process waits for instance of `Installer`
2. When open, sends `SIGSTOP`, causing a fake freeze
4. Verifies the signature is that of Zoom
5. Starts a new `Installer` instance with a bad `USER` value
6. Kills the first `Installer` in the background
