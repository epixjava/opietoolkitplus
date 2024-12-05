import os
import sys
import time
import opie
import click
import shutil
import tarfile
import platform
from helpers import u
from datetime import datetime
from os import path
from subprocess import check_call, PIPE, STDOUT, CalledProcessError

# Define constants in a cross-platform way
RIPS_DIR = os.path.join(u.HOME, "rips")

def assert_environment():
    """
    Ensure the rips directory exists and is properly configured.
    Creates the directory if it doesn't exist, handling potential permission issues.
    """
    try:
        os.makedirs(RIPS_DIR, exist_ok=True)
    except Exception as e:
        raise EnvironmentError(f"Failed to create rips directory at {RIPS_DIR}: {e}")

def get_ffmpeg_binary():
    """
    Find the appropriate audio processing binary (ffmpeg or avconv) for the system.
    Handles different naming conventions across platforms.
    
    Returns:
        str: Path to the ffmpeg or avconv binary
        
    Raises:
        EnvironmentError: If neither ffmpeg nor avconv is found
    """
    # On Windows, also check common installation paths
    if platform.system() == 'Windows':
        common_paths = [
            os.path.join(os.getenv('ProgramFiles'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.getenv('ProgramFiles(x86)'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.getenv('LOCALAPPDATA'), 'ffmpeg', 'bin', 'ffmpeg.exe')
        ]
        
        # Check if ffmpeg is in PATH or common locations
        ffmpeg_path = shutil.which("ffmpeg.exe") or next((p for p in common_paths if os.path.exists(p)), None)
        if ffmpeg_path:
            return ffmpeg_path
            
    else:
        # Unix systems typically have these in PATH
        if shutil.which("ffmpeg"):
            return "ffmpeg"
        if shutil.which("avconv"):
            return "avconv"
    
    raise EnvironmentError(
        "Neither ffmpeg nor avconv found. Please install ffmpeg:\n"
        "- Windows: run 'winget install FFmpeg' in terminal\n"
        "- macOS: Use 'brew install ffmpeg'\n"
        "- Linux: Use your package manager (e.g., 'apt install ffmpeg')"
    )

def transcode(input_file, codec, output_file, codec_flags=None):
    """
    Transcode an audio file using ffmpeg/avconv with proper error handling.
    
    Args:
        input_file (str): Path to input audio file
        codec (str): Target audio codec
        output_file (str): Path for output file
        codec_flags (list): Optional additional codec parameters
    """
    if codec_flags is None:
        codec_flags = []

    try:
        # Get appropriate binary
        binary = get_ffmpeg_binary()
        
        # Normalize paths for cross-platform compatibility
        input_file = os.path.normpath(input_file)
        output_file = os.path.normpath(output_file)
        
        # Construct command with proper path handling
        base_command = [
            binary,
            "-loglevel", "warning",
            "-stats",
            "-i", input_file,
            "-c:a", codec
        ]
        
        # Build final command
        command = base_command + codec_flags + [output_file]
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Execute transcoding command
        check_call(command, stderr=STDOUT)
        
    except CalledProcessError as e:
        raise RuntimeError(f"Transcoding failed: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error during transcoding: {str(e)}")

def create_rip(mount, name):
    """
    Create a complete set of audio rips in various formats.
    
    Args:
        mount (str): Path to the mounted OP-1
        name (str): Name for the rip directory
    """
    try:
        # Normalize paths for cross-platform compatibility
        fullpath = os.path.normpath(os.path.join(RIPS_DIR, name))
        albums = os.path.normpath(os.path.join(mount, "album"))
        sides = ["side_a", "side_b"]
        
        # Create rip directory, failing if it already exists to prevent overwrites
        try:
            os.makedirs(fullpath)
        except FileExistsError:
            raise ValueError(f"Rip directory already exists: {fullpath}")
            
        click.echo(f"Writing rips to {fullpath}")
        
        # Process each side
        for side in sides:
            input_file = os.path.join(albums, f"{side}.aif")
            
            # Verify source file exists
            if not os.path.exists(input_file):
                raise FileNotFoundError(f"Source file not found: {input_file}")
            
            # Initial transcode to lossless format
            click.echo(f"Transcoding {side}")
            flac_output = os.path.join(fullpath, f"{side}.flac")
            transcode(input_file, "flac", flac_output)
            
            # Create additional formats
            click.echo("Creating additional formats...")
            
            # ALAC (Apple Lossless) conversion
            click.echo(f"Transcoding {side} to ALAC")
            transcode(flac_output, "alac", os.path.join(fullpath, f"{side}.m4a"))
            
            # MP3 conversion
            click.echo(f"Transcoding {side} to MP3 V0")
            transcode(flac_output, "libmp3lame", 
                     os.path.join(fullpath, f"{side}.mp3"), 
                     ["-q:a", "0"])
        
        click.echo("\nRipping completed successfully!")
        click.pause("Press any key to return to op1-REpacker")
        
    except Exception as e:
        click.echo(f"Error during ripping process: {str(e)}", err=True)
        sys.exit(1)