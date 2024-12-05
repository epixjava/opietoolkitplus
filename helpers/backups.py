import os
import tarfile
from datetime import datetime
from tqdm import tqdm
from helpers import op1, u  # Import our updated u.py helper

def get_backups_dir():
    """
    Get the backups directory in a cross-platform way.
    Creates the directory if it doesn't exist.
    """
    # Use the same home directory resolution we established in u.py
    backups_dir = os.path.join(u.HOME, "backups")
    return backups_dir

# Define backups directory using our cross-platform function
BACKUPS_DIR = get_backups_dir()

def assert_environment():
    """Ensure the backup environment exists and is properly configured."""
    try:
        os.makedirs(BACKUPS_DIR, exist_ok=True)
    except Exception as e:
        raise EnvironmentError(f"Failed to create backups directory: {e}")

def generate_archive(mount=None, backups_dir=None):
    """
    Generate a backup archive of the OP-1 contents.
    
    Args:
        mount: Path to the mounted OP-1 directory
        backups_dir: Custom backup directory (defaults to BACKUPS_DIR)
    """
    if mount is None:
        mount = op1.get_mount_or_die_trying()
    
    if backups_dir is None:
        backups_dir = BACKUPS_DIR

    # Ensure the backup directory exists
    os.makedirs(backups_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    archive_name = f"opie-backup-{timestamp}.tar.xz"
    archive_path = os.path.join(backups_dir, archive_name)
    
    print(f"Writing backup as {archive_path}")
    
    # Use normpath to ensure consistent path handling across platforms
    mount = os.path.normpath(mount)
    
    # Calculate total items with platform-agnostic path handling
    total_items = sum([len(files) + len(dirs) for _, dirs, files in os.walk(mount)])
    
    with tarfile.open(archive_path, "w:xz") as tar:
        with tqdm(total=total_items, unit="item", desc="Backing up") as pbar:
            for child in os.listdir(mount):
                if not child.startswith('.'):
                    child_path = os.path.join(mount, child)
                    # Use normpath for consistent path handling
                    archive_child = os.path.normpath(child)
                    tar.add(child_path, archive_child, recursive=False)
                    pbar.update(1)
                    
                    if os.path.isdir(child_path):
                        for root, dirs, files in os.walk(child_path):
                            for name in files + dirs:
                                if not name.startswith('.'):
                                    full_path = os.path.join(root, name)
                                    # Ensure consistent path separators in archive
                                    archive_name = os.path.normpath(
                                        os.path.relpath(full_path, mount)
                                    )
                                    tar.add(full_path, archive_name)
                                    pbar.update(1)
    
    return archive_path


def verify_backup_before_restore(backup_path):
    """
    Verify backup integrity before attempting restoration.
    This helps prevent restoring corrupted backups.
    """
    from commands import verify
    is_valid, issues = verify.verify_backup_structure(backup_path)
    return is_valid, issues

def restore_archive(archive_path, mount=None, progress_callback=None):
    """
    Restore a backup archive to the OP-1.
    
    Args:
        archive_path: Path to the backup archive
        mount: Path to the mounted OP-1 directory
        progress_callback: Optional callback function for progress updates
    """
    if mount is None:
        mount = op1.get_mount_or_die_trying()

    # Normalize paths for cross-platform compatibility
    archive_path = os.path.normpath(archive_path)
    mount = os.path.normpath(mount)

    if not os.path.exists(archive_path):
        raise FileNotFoundError(f"Backup file not found: {archive_path}")

    # Cross-platform mount point validation
    if not op1.is_valid_mount(mount):  # Assuming this function exists in op1.py
        raise ValueError(f"Invalid mount point: {mount}")

    try:
        with tarfile.open(archive_path, "r:xz") as tar:
            members = tar.getmembers()
            total_members = len(members)

            for i, member in enumerate(members):
                # Normalize paths during extraction
                member.name = os.path.normpath(member.name)
                tar.extract(member, path=mount)
                if progress_callback:
                    progress_callback(int((i + 1) / total_members * 100))

        print("Restore completed successfully.")
    except Exception as e:
        raise RuntimeError(f"Failed to restore backup: {e}")