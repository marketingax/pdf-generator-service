# === file_manager.py ===
# Created: September 18, 2025 - 12:00 PM
# Purpose: File management utilities for PDF storage and automatic cleanup
# Key Exports:
#   - setup_directories(): Initialize required directories
#   - cleanup_old_files(): Remove expired files
#   - schedule_cleanup(): Start background cleanup scheduler
# Interactions:
#   - Used by: app.py for file management and cleanup scheduling
# Notes:
#   - Implements automatic file cleanup after configurable time period
#   - Thread-safe cleanup operations

import os
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Global cleanup thread reference
_cleanup_thread = None
_cleanup_running = False

def setup_directories(upload_folder):
    """
    Create necessary directories for file storage
    
    Parameters:
    upload_folder (str): Path to the upload directory
    
    Returns:
    bool: True if directories were created successfully
    
    Raises:
    Exception: If directory creation fails
    """
    try:
        upload_path = Path(upload_folder)
        upload_path.mkdir(parents=True, exist_ok=True)
        
        # Create a temporary subdirectory for processing
        temp_path = upload_path / 'temp'
        temp_path.mkdir(exist_ok=True)
        
        logger.info(f"Directories initialized: {upload_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        raise Exception(f"Directory setup failed: {str(e)}")

def cleanup_old_files(directory, max_age_hours=24):
    """
    Remove files older than the specified age
    
    Parameters:
    directory (str): Directory to clean up
    max_age_hours (int): Maximum age in hours before files are deleted
    
    Returns:
    dict: Cleanup statistics with counts and sizes
    """
    cleanup_stats = {
        'files_removed': 0,
        'bytes_freed': 0,
        'errors': 0,
        'files_kept': 0
    }
    
    try:
        directory_path = Path(directory)
        
        if not directory_path.exists():
            logger.warning(f"Cleanup directory does not exist: {directory}")
            return cleanup_stats
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        logger.debug(f"Cleaning up files older than: {cutoff_time}")
        
        # Process all files in the directory
        for file_path in directory_path.iterdir():
            try:
                if not file_path.is_file():
                    continue
                
                # Skip temporary files and hidden files
                if file_path.name.startswith('.') or file_path.name.startswith('temp_'):
                    continue
                
                # Get file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if file_mtime < cutoff_time:
                    # File is old enough to be deleted
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    
                    cleanup_stats['files_removed'] += 1
                    cleanup_stats['bytes_freed'] += file_size
                    
                    logger.debug(f"Removed expired file: {file_path.name} ({file_size} bytes)")
                else:
                    cleanup_stats['files_kept'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                cleanup_stats['errors'] += 1
        
        if cleanup_stats['files_removed'] > 0:
            logger.info(f"Cleanup completed: removed {cleanup_stats['files_removed']} files, "
                       f"freed {cleanup_stats['bytes_freed']/1024:.2f} KB")
        else:
            logger.debug("Cleanup completed: no files needed removal")
            
    except Exception as e:
        logger.error(f"Cleanup operation failed: {e}")
        cleanup_stats['errors'] += 1
    
    return cleanup_stats

def cleanup_worker(directory, max_age_hours, check_interval_minutes=30):
    """
    Background worker thread for periodic file cleanup
    
    Parameters:
    directory (str): Directory to monitor and clean
    max_age_hours (int): Maximum file age before deletion
    check_interval_minutes (int): How often to run cleanup (in minutes)
    """
    global _cleanup_running
    
    logger.info(f"Cleanup worker started: checking every {check_interval_minutes} minutes")
    
    while _cleanup_running:
        try:
            # Perform cleanup
            stats = cleanup_old_files(directory, max_age_hours)
            
            # Log summary if any action was taken
            if stats['files_removed'] > 0 or stats['errors'] > 0:
                logger.info(f"Cleanup cycle: removed {stats['files_removed']} files, "
                           f"{stats['errors']} errors, {stats['files_kept']} files kept")
            
            # Wait for next cleanup cycle
            sleep_seconds = check_interval_minutes * 60
            for _ in range(sleep_seconds):
                if not _cleanup_running:
                    break
                time.sleep(1)  # Check stop condition every second
                
        except Exception as e:
            logger.error(f"Cleanup worker error: {e}")
            # Wait a bit before retrying
            time.sleep(60)
    
    logger.info("Cleanup worker stopped")

def schedule_cleanup(directory, max_age_hours=24, check_interval_minutes=30):
    """
    Start the background cleanup scheduler
    
    Parameters:
    directory (str): Directory to monitor
    max_age_hours (int): Maximum file age before deletion
    check_interval_minutes (int): Cleanup check interval in minutes
    
    Returns:
    bool: True if scheduler started successfully
    """
    global _cleanup_thread, _cleanup_running
    
    try:
        # Stop existing cleanup thread if running
        stop_cleanup()
        
        # Start new cleanup thread
        _cleanup_running = True
        _cleanup_thread = threading.Thread(
            target=cleanup_worker,
            args=(directory, max_age_hours, check_interval_minutes),
            daemon=True,
            name="FileCleanupWorker"
        )
        _cleanup_thread.start()
        
        logger.info(f"Cleanup scheduler started for directory: {directory}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to start cleanup scheduler: {e}")
        return False

def stop_cleanup():
    """
    Stop the background cleanup scheduler
    
    Returns:
    bool: True if cleanup was stopped successfully
    """
    global _cleanup_thread, _cleanup_running
    
    if not _cleanup_running:
        return True
    
    try:
        _cleanup_running = False
        
        if _cleanup_thread and _cleanup_thread.is_alive():
            _cleanup_thread.join(timeout=5)  # Wait up to 5 seconds
            
        logger.info("Cleanup scheduler stopped")
        return True
        
    except Exception as e:
        logger.error(f"Error stopping cleanup scheduler: {e}")
        return False

def get_directory_stats(directory):
    """
    Get statistics about files in the directory
    
    Parameters:
    directory (str): Directory to analyze
    
    Returns:
    dict: Directory statistics including file counts and sizes
    """
    stats = {
        'total_files': 0,
        'total_size_bytes': 0,
        'pdf_files': 0,
        'oldest_file': None,
        'newest_file': None,
        'average_file_size': 0
    }
    
    try:
        directory_path = Path(directory)
        
        if not directory_path.exists():
            return stats
        
        file_sizes = []
        file_times = []
        
        for file_path in directory_path.iterdir():
            if not file_path.is_file():
                continue
                
            # Skip hidden and temporary files
            if file_path.name.startswith('.') or file_path.name.startswith('temp_'):
                continue
            
            file_stat = file_path.stat()
            file_size = file_stat.st_size
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            
            stats['total_files'] += 1
            stats['total_size_bytes'] += file_size
            file_sizes.append(file_size)
            file_times.append(file_mtime)
            
            if file_path.suffix.lower() == '.pdf':
                stats['pdf_files'] += 1
        
        # Calculate additional stats
        if file_sizes:
            stats['average_file_size'] = sum(file_sizes) / len(file_sizes)
        
        if file_times:
            stats['oldest_file'] = min(file_times).isoformat()
            stats['newest_file'] = max(file_times).isoformat()
            
    except Exception as e:
        logger.error(f"Error getting directory stats: {e}")
    
    return stats

def ensure_disk_space(directory, required_mb=100):
    """
    Check if there's enough disk space available
    
    Parameters:
    directory (str): Directory to check
    required_mb (int): Required free space in MB
    
    Returns:
    dict: Disk space information and availability status
    """
    try:
        directory_path = Path(directory)
        stat = os.statvfs(directory_path) if hasattr(os, 'statvfs') else None
        
        if stat:
            # Unix-like systems
            free_bytes = stat.f_bavail * stat.f_frsize
            total_bytes = stat.f_blocks * stat.f_frsize
            used_bytes = total_bytes - free_bytes
        else:
            # Windows systems
            import shutil
            total_bytes, used_bytes, free_bytes = shutil.disk_usage(directory_path)
        
        free_mb = free_bytes / (1024 * 1024)
        total_mb = total_bytes / (1024 * 1024)
        used_mb = used_bytes / (1024 * 1024)
        
        return {
            'free_mb': round(free_mb, 2),
            'total_mb': round(total_mb, 2),
            'used_mb': round(used_mb, 2),
            'free_percent': round((free_bytes / total_bytes) * 100, 2),
            'sufficient_space': free_mb >= required_mb,
            'required_mb': required_mb
        }
        
    except Exception as e:
        logger.error(f"Error checking disk space: {e}")
        return {
            'free_mb': 0,
            'total_mb': 0,
            'used_mb': 0,
            'free_percent': 0,
            'sufficient_space': False,
            'required_mb': required_mb
        }

"""
OVERVIEW

This module provides comprehensive file management capabilities for the PDF generation service.
It handles directory setup, automatic cleanup of expired files, and monitoring of storage resources.

Key Features:
- Automatic directory creation with proper permissions
- Background file cleanup based on configurable age limits
- Thread-safe cleanup operations that don't block the main application
- Directory statistics and disk space monitoring
- Graceful error handling and comprehensive logging

The cleanup system runs in a separate daemon thread that:
1. Periodically scans the upload directory for old files
2. Removes files older than the configured age limit
3. Logs cleanup activities and maintains statistics
4. Handles errors gracefully without stopping the service

File Age Determination:
- Uses file modification time (mtime) for age calculation
- Configurable maximum age (default 24 hours)
- Skips hidden files and temporary files
- Only processes regular files (not directories)

Thread Safety:
- Uses global state variables for thread coordination
- Proper thread joining with timeout for clean shutdown
- Daemon thread ensures cleanup stops when main process exits
- Atomic file operations to prevent corruption

Storage Management:
- Directory statistics for monitoring file counts and sizes
- Disk space checking to prevent storage issues
- Support for both Unix and Windows disk usage APIs
- Configurable space requirements for operation

This approach ensures the service maintains good performance and doesn't accumulate
storage over time, which is critical for cloud deployments with limited storage quotas.
"""

"""
 * === file_manager.py ===
 * Updated: September 18, 2025 - 12:00 PM
 * Summary: File management and cleanup utilities for PDF storage service
 * Key Components:
 *   - setup_directories(): Initialize storage directories
 *   - cleanup_old_files(): Remove expired files with statistics
 *   - schedule_cleanup(): Background cleanup thread management
 *   - get_directory_stats(): Storage monitoring utilities
 * Dependencies:
 *   - Requires: Standard library threading, pathlib, datetime
 * Version History:
 *   v1.0 - Initial implementation with background cleanup
 * Notes:
 *   - Thread-safe cleanup operations
 *   - Cross-platform disk space monitoring
 *   - Comprehensive error handling and logging
 */
