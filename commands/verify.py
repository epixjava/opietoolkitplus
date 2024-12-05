# verify.py
import os
import click
import hashlib
import tarfile
from pathlib import Path
from helpers import u, op1, backups
from datetime import datetime
from tqdm import tqdm

description = "  Verify the integrity of OP-1 backup files"

def calculate_file_hash(file_path):
    """
    Calculate SHA-256 hash of a file using chunks to handle large files efficiently.
    This helps us verify file integrity without loading entire files into memory.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.digest()

def verify_backup_structure(archive_path):
    """
    Verify that a backup archive contains all expected OP-1 directories and files.
    Returns tuple of (is_valid, issues_found).
    """
    required_dirs = {'tape', 'album', 'synth', 'drum'}
    found_dirs = set()
    issues = []

    try:
        with tarfile.open(archive_path, 'r:xz') as tar:
            # Get all members of the archive
            members = tar.getmembers()
            
            # Check for required directories
            for member in members:
                top_level_dir = member.name.split('/')[0]
                found_dirs.add(top_level_dir)
            
            # Check if all required directories are present
            missing_dirs = required_dirs - found_dirs
            if missing_dirs:
                issues.append(f"Missing required directories: {', '.join(missing_dirs)}")
            
            # Check for any empty directories
            for required_dir in required_dirs - missing_dirs:
                dir_contents = [m for m in members if m.name.startswith(required_dir)]
                if not dir_contents:
                    issues.append(f"Directory '{required_dir}' is empty")

    except Exception as e:
        issues.append(f"Error reading backup archive: {str(e)}")
        return False, issues

    return len(issues) == 0, issues

def store_backup_metadata(backup_path, metadata):
    """
    Store verification metadata alongside the backup file.
    This helps us track backup integrity over time.
    """
    metadata_path = backup_path.with_suffix('.meta')
    try:
        with open(metadata_path, 'w') as f:
            for key, value in metadata.items():
                f.write(f"{key}={value}\n")
    except Exception as e:
        click.echo(f"Warning: Could not save backup metadata: {str(e)}")

@click.command()
@click.argument('backup_file', required=False)
def cli(backup_file=None):
    """Verify the integrity of OP-1 backup files"""
    try:
        backups.assert_environment()
        
        # List available backups if no specific file is provided
        if not backup_file:
            backup_files = sorted(
                Path(backups.BACKUPS_DIR).glob("*.tar.xz"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if not backup_files:
                click.echo("No backups found to verify.")
                return
            
            click.echo("Available backups:")
            for i, backup in enumerate(backup_files):
                size_mb = backup.stat().st_size / (1024 * 1024)
                click.echo(f"{i}. {backup.name} ({size_mb:.1f}MB)")
            
            choice = click.prompt("Choose a backup to verify", type=int)
            if choice < 0 or choice >= len(backup_files):
                click.echo("Invalid selection.")
                return
            
            backup_path = backup_files[choice]
        else:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                click.echo(f"Backup file not found: {backup_path}")
                return

        click.echo(f"\nVerifying backup: {backup_path.name}")
        
        # Verify backup structure
        click.echo("\nChecking backup structure...")
        is_valid, issues = verify_backup_structure(backup_path)
        
        if not is_valid:
            click.echo("\n Backup verification failed!")
            for issue in issues:
                click.echo(f" - {issue}")
            return

        # Calculate and store backup metadata
        click.echo("\nCalculating backup checksums...")
        backup_hash = calculate_file_hash(backup_path)
        
        metadata = {
            'last_verified': datetime.now().isoformat(),
            'size_bytes': backup_path.stat().st_size,
            'sha256': backup_hash.hex(),
            'structure_verified': 'true'
        }
        
        store_backup_metadata(backup_path, metadata)
        
        click.echo("\n  Backup verification successful!")
        click.echo(f"Backup size: {metadata['size_bytes'] / (1024*1024):.1f}MB")
        click.echo(f"SHA-256: {metadata['sha256']}")
        click.echo(f"Verified: {metadata['last_verified']}")

    except Exception as e:
        click.echo(f"\n  Error during verification: {str(e)}")
        return 1

if __name__ == '__main__':
    cli()