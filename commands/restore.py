import os
import sys
import click
import platform
from datetime import datetime
from pathlib import Path
from helpers import u, op1, backups

description = "Choose a backup file and restore it to a plugged-in OP-1"

def list_backups(backup_dir):
    """
    Lists available backup files in a cross-platform manner.
    
    This function uses pathlib to handle paths consistently across operating systems
    and sorts backups by modification time so the most recent appears first.
    
    Args:
        backup_dir (str): Directory containing backup files
        
    Returns:
        list: Sorted list of backup files (most recent first)
    """
    backup_path = Path(backup_dir)
    
    # Get all visible backup files and sort by modification time
    try:
        backups = [f for f in backup_path.glob("*.tar.xz") 
                if not f.name.startswith('.')]
        return sorted(backups, 
                    key=lambda x: x.stat().st_mtime,
                    reverse=True)
    except Exception as e:
        raise RuntimeError(f"Error accessing backup directory: {str(e)}")

def verify_backup_file(backup_path):
    """
    Verifies that the selected backup file is valid and readable.
    
    Args:
        backup_path (Path): Path to the backup file
        
    Raises:
        ValueError: If the backup file is invalid or corrupted
    """
    if not backup_path.exists():
        raise ValueError(f"Backup file not found: {backup_path}")
    
    if not backup_path.is_file():
        raise ValueError(f"Selected path is not a file: {backup_path}")
    
    if backup_path.stat().st_size == 0:
        raise ValueError(f"Backup file is empty: {backup_path}")

def format_backup_info(backup_file):
    """
    Formats backup file information in a user-friendly way.
    
    Args:
        backup_file (Path): Path to backup file
        
    Returns:
        str: Formatted string with backup information
    """
    # Get file modification time and size
    mtime = backup_file.stat().st_mtime
    size = backup_file.stat().st_size
    
    # Format time based on platform preferences
    if platform.system() == 'Windows':
        time_format = "%#m/%#d/%Y %#I:%M %p"
    else:
        time_format = "%-m/%-d/%Y %-I:%M %p"
    
    modified = datetime.fromtimestamp(mtime).strftime(time_format)
    size_mb = size / (1024 * 1024)
    
    return f"{backup_file.name} ({size_mb:.1f}MB, modified {modified})"

@click.command()
def cli():
    """
    Command-line interface for restoring OP-1 backups.
    
    This function handles the entire backup restoration process:
    1. Checks the environment and lists available backups
    2. Lets the user choose a backup
    3. Verifies the chosen backup file
    4. Connects to the OP-1
    5. Performs the restoration with progress monitoring
    """
    try:
        # Ensure backup environment exists
        backups.assert_environment()
        
        # Get sorted list of backup files
        backup_files = list_backups(backups.BACKUPS_DIR)
        
        if not backup_files:
            click.echo("\nNo backups found in {backups.BACKUPS_DIR}")
            click.echo("Please create a backup first using the 'backup' command.")
            return

        # Display available backups with detailed information
        click.echo(f"\nAvailable backups in {backups.BACKUPS_DIR}:")
        for i, backup in enumerate(backup_files):
            click.echo(f"{i}. {format_backup_info(backup)}")

        # Get user selection with input validation
        while True:
            try:
                choice = click.prompt('\nChoose a backup number', type=int)
                if 0 <= choice < len(backup_files):
                    break
                click.echo(f"Please enter a number between 0 and {len(backup_files)-1}")
            except click.Abort:
                click.echo("\nOperation cancelled by user")
                return
            except ValueError:
                click.echo("Please enter a valid number")

        selected_backup = backup_files[choice]
        click.echo(f"\nSelected backup: {format_backup_info(selected_backup)}")

        # Verify backup file
        verify_backup_file(selected_backup)

        click.echo("\nVerifying backup integrity...")
        is_valid, issues = backups.verify_backup_before_restore(str(selected_backup))
        
        if not is_valid:
            click.echo("\n Backup verification failed!")
            for issue in issues:
                click.echo(f" - {issue}")
            if not click.confirm("\nWarning: This backup may be corrupted or incomplete. "
                            "Do you want to proceed with restoration anyway?"):
                click.echo("Operation cancelled")
                return
            click.echo("\nProceeding with restoration despite verification warnings...")
        else:
            click.echo(" Backup verification passed!")

        # Connect to OP-1
        click.echo("\nConnecting to OP-1...")
        mount = op1.get_mount_or_die_trying()
        click.echo(f"OP-1 found at {mount}")

        # Confirm before proceeding
        if not click.confirm("\nThis will overwrite all data on your OP-1. Continue?"):
            click.echo("Operation cancelled")
            return

        # Perform restore with progress bar
        click.echo(f"\nRestoring {selected_backup.name} to OP-1...")
        with click.progressbar(length=100, label="Restoring backup") as bar:
            def update_progress(progress):
                bar.update(progress - bar.pos)  # Update relative to current position
            
            try:
                backups.restore_archive(str(selected_backup), mount, 
                                    progress_callback=update_progress)
            except Exception as e:
                raise RuntimeError(f"Restore failed: {str(e)}")

        click.echo("\n✓ Restore completed successfully!")
        click.echo("\nPlease safely eject your OP-1 using the 'eject' command.")
        
        click.pause("\nPress any key to return to OP-1 REpacker")

    except Exception as e:
        click.echo(f"\n✗ Error: {str(e)}", err=True)
        click.echo("\nRestore failed. Please try again with a fresh backup.")
        sys.exit(1)

if __name__ == "__main__":
    cli()