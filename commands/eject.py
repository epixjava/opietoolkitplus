import os
import sys
import opie
import click
import shutil
import platform
import subprocess
from subprocess import run, PIPE, STDOUT, CalledProcessError
from helpers import u, op1

description = "  Eject your OP-1"

def eject_windows(mount_point):
    """
    Eject a drive on Windows using PowerShell.
    
    On Windows, we need to use PowerShell's Remove-PSDrive command to safely eject
    a USB drive. We first get the drive letter from the mount point, then construct
    and execute the appropriate PowerShell command.
    """
    try:
        # Get drive letter from mount point (e.g., "C:" from "C:\")
        drive_letter = os.path.splitdrive(mount_point)[0]
        
        # Construct PowerShell command to safely eject the drive
        powershell_command = [
            "powershell",
            "-Command",
            f"""
            $driveEject = New-Object -comObject Shell.Application
            $driveEject.Namespace(17).ParseName(\"{drive_letter}\").InvokeVerb(\"Eject\")
            """
        ]
        
        # Execute the command
        result = run(powershell_command, stdout=PIPE, stderr=STDOUT, text=True)
        
        # Check if the command was successful
        if result.returncode == 0:
            return "OP-1 safely ejected."
        else:
            return f"Error ejecting OP-1: {result.stdout}"
            
    except Exception as e:
        return f"Failed to eject OP-1: {str(e)}"

def eject_unix(mount_point):
    """
    Eject a drive on Unix-like systems.
    
    On Unix systems, we use different commands depending on the specific OS:
    - macOS: diskutil eject
    - Linux: udisksctl unmount and power-off
    """
    try:
        if platform.system() == 'Darwin':  # macOS
            result = run(["diskutil", "eject", mount_point], 
                        stdout=PIPE, stderr=STDOUT, text=True)
            return result.stdout
        else:  # Linux
            # First unmount the device
            unmount_result = run(["udisksctl", "unmount", "--block-device", mount_point],
                               stdout=PIPE, stderr=STDOUT, text=True)
            if unmount_result.returncode != 0:
                return f"Error unmounting OP-1: {unmount_result.stdout}"
            
            # Then power off the device
            poweroff_result = run(["udisksctl", "power-off", "--block-device", mount_point],
                                stdout=PIPE, stderr=STDOUT, text=True)
            return poweroff_result.stdout
            
    except FileNotFoundError:
        return ("Error: Required system utilities not found.\n"
                "Please install: \n"
                "- macOS: diskutil (should be pre-installed)\n"
                "- Linux: udisks2 (sudo apt install udisks2 or equivalent)")
    except Exception as e:
        return f"Failed to eject OP-1: {str(e)}"

@click.command()
@click.argument('name', required=False)
def cli(name=None):
    """
    Command-line interface for ejecting the OP-1.
    
    This function checks if the OP-1 is connected, finds its mount point,
    and safely ejects it using the appropriate method for the current operating system.
    """
    # First verify OP-1 is connected
    if not op1.is_connected():
        click.echo("OP-1 doesn't appear to be connected.")
        sys.exit(1)
    
    # Find the mount point
    mount = op1.find_op1_mount()
    if mount is None:
        click.echo("Looks like your OP-1 is already dismounted.")
        sys.exit(0)
    
    click.echo("Attempting to eject OP-1...")
    
    # Use appropriate eject method based on operating system
    if platform.system() == 'Windows':
        result = eject_windows(mount)
    else:
        result = eject_unix(mount)
    
    # Display the result
    click.echo(result)