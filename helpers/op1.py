import os
import sys
import time
import opie
import click
import tarfile
import platform
from helpers import u, mount

# Constants for OP-1 USB identification
VENDOR_TE = 0x2367
PRODUCT_OP1 = 0x0002
OP1_BASE_DIRS = set(['tape', 'album', 'synth', 'drum'])

# Import Windows-specific modules only on Windows
if platform.system() == 'Windows':
    try:
        import win32api
        import win32file
    except ImportError:
        sys.exit("On Windows systems, this tool requires the pywin32 package. Please install it with: pip install pywin32")

def get_removable_drives():
    """
    Get all removable drives on Windows systems.
    
    Returns:
        list: A list of drive paths that are removable devices
    """
    if platform.system() != 'Windows':
        return []
        
    drives = []
    for letter in range(ord('A'), ord('Z')+1):
        drive = chr(letter) + ':\\'
        try:
            drive_type = win32file.GetDriveType(drive)
            if drive_type == win32file.DRIVE_REMOVABLE:
                drives.append(drive)
        except Exception as e:
            continue
    return drives

def is_connected():
    """
    Check if OP-1 is connected in disk mode.
    Handles both Windows and Unix-like systems differently.
    
    Returns:
        bool: True if OP-1 is connected, False otherwise
    """
    if platform.system() == 'Windows':
        # Windows: Look for removable drives with OP-1 structure
        return any(is_op1_drive(drive) for drive in get_removable_drives())
    else:
        try:
            # Unix: Use USB detection
            import usb.core
            dev = usb.core.find(idVendor=VENDOR_TE, idProduct=PRODUCT_OP1)
            return dev is not None
        except ImportError:
            sys.exit("On Unix-like systems, this tool requires pyusb. Please install it with: pip install pyusb")

def is_op1_drive(path):
    """
    Check if a given path matches OP-1's directory structure.
    
    Args:
        path (str): Path to check for OP-1 structure
        
    Returns:
        bool: True if path matches OP-1 structure, False otherwise
    """
    try:
        # Normalize path for cross-platform compatibility
        path = os.path.normpath(path)
        subdirs = set(u.get_visible_folders(path))
        return OP1_BASE_DIRS.issubset(subdirs)
    except (PermissionError, FileNotFoundError):
        return False
    except Exception as e:
        print(f"Warning: Unexpected error checking path {path}: {str(e)}")
        return False

def wait_for_connection():
    """
    Wait for OP-1 to connect in disk mode.
    Handles keyboard interrupts gracefully.
    
    Returns:
        bool: True when connection is established
    """
    try:
        print("Waiting for OP-1 to connect in disk mode (Shift+COM -> 3)...")
        while True:
            if is_connected():
                print("OP-1 connected and mounted!")
                return True
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)

def is_valid_mount(mount_point):
    """
    Validate if a mount point is accessible and matches OP-1 structure.
    
    Args:
        mount_point (str): Path to check
        
    Returns:
        bool: True if mount point is valid, False otherwise
    """
    try:
        mount_point = os.path.normpath(mount_point)
        return os.path.exists(mount_point) and is_op1_drive(mount_point)
    except Exception:
        return False

def get_mount_or_die_trying():
    """
    Get the OP-1 mount point, waiting if necessary.
    Exits program if mount point cannot be found.
    
    Returns:
        str: Path to OP-1 mount point
    """
    if not is_connected():
        wait_for_connection()
    
    mount_point = find_op1_mount()
    if mount_point is None:
        print("Waiting for OP-1 disk to mount...")
        mount_point = wait_for_op1_mount()
        if mount_point is None:
            sys.exit("Failed to find mount point of OP-1. Make sure it's in DISK mode and mounted.")
    return os.path.normpath(mount_point)

def find_op1_mount():
    """
    Find the OP-1's mount point on the system.
    Handles both Windows and Unix-like systems.
    
    Returns:
        str or None: Path to OP-1 mount point if found, None otherwise
    """
    if platform.system() == 'Windows':
        for drive in get_removable_drives():
            if is_op1_drive(drive):
                print(f"Found OP-1 at {drive}")
                return drive
    else:
        mounts = mount.get_potential_mounts()
        if mounts:
            for device, mount_point in mounts:
                try:
                    if is_op1_drive(mount_point):
                        print(f"Found OP-1 at {mount_point}")
                        return mount_point
                except (PermissionError, FileNotFoundError):
                    continue
    return None

def wait_for_op1_mount(timeout=15):
    """
    Wait for OP-1 to mount with timeout.
    
    Args:
        timeout (int): Maximum seconds to wait
        
    Returns:
        str or None: Mount point if found, None if timed out
    """
    try:
        for i in range(timeout):
            print(f"Checking for OP-1 mount ({i+1}/{timeout})...")
            mount_point = find_op1_mount()
            if mount_point is not None:
                return mount_point
            time.sleep(1)
        print("Timed out waiting for mount.")
        return None
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)