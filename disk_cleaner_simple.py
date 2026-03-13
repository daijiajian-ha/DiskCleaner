# -*- coding: utf-8 -*-
"""
DiskCleaner - Simple GUI Version
Using PySimpleGUI for better compatibility
"""

import os
import sys
import threading
import ctypes
from pathlib import Path

# PySimpleGUI - simpler and more reliable
import PySimpleGUI as sg

# Get disk info using ctypes
def get_drives():
    """Get list of available drives"""
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i in range(26):
        if bitmask & (1 << i):
            drive = chr(ord('A') + i) + ':'
            try:
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                total_free = ctypes.c_ulonglong(0)
                if ctypes.windll.kernel32.GetDiskFreeSpaceExW(drive, ctypes.byref(free_bytes), ctypes.byref(total_bytes), ctypes.byref(total_free)):
                    total_gb = total_bytes.value / (1024**3)
                    free_gb = free_bytes.value / (1024**3)
                    used_pct = int((total_bytes.value - free_bytes.value) * 100 / total_bytes.value)
                    drives.append((drive, f"{drive} ({free_gb:.1f}GB free, {used_pct}% used)"))
            except:
                drives.append((drive, f"{drive}"))
    return drives

def scan_directory(root_path, file_pattern, max_results=500):
    """Scan directory for files matching pattern"""
    results = []
    patterns = {
        'junk': ['.tmp', '.log', '.bak', '.temp', '.old', '.cache'],
        'large': [],  # Will filter by size
        'im': ['WeChat', '微信']
    }
    
    min_size = 1024 * 1024 * 1024 if file_pattern == 'large' else 0
    
    try:
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Skip system directories
            dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in ['Windows', 'Program Files', 'Program Files (x86)']]
            
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(filepath)
                    
                    if file_pattern == 'junk':
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in patterns['junk']:
                            results.append((filepath, filename, size))
                    elif file_pattern == 'large':
                        if size >= min_size:
                            results.append((filepath, filename, size))
                    elif file_pattern == 'im':
                        if 'WeChat' in dirpath or '微信' in dirpath:
                            results.append((filepath, filename, size))
                except:
                    pass
                
                if len(results) >= max_results:
                    return results
    except:
        pass
    
    return results

def format_size(size):
    """Format file size"""
    if size > 1024**3:
        return f"{size / (1024**3):.1f} GB"
    elif size > 1024**2:
        return f"{size / (1024**2):.1f} MB"
    elif size > 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size} B"

def main():
    # Get available drives
    drives = get_drives()
    drive_options = [d[1] for d in drives]
    
    # Layout
    layout = [
        [sg.Text('DiskCleaner', font=('Arial', 16, 'bold'))],
        [sg.Text('Select Drive:'), sg.Combo(drive_options, key='-DRIVE-', default_value=drive_options[0] if drive_options else '')],
        [sg.Radio('Junk Files (.tmp, .log, .bak, .temp, .old)', 'SCAN', default=True, key='-JUNK-'),
         sg.Radio('Large Files (>1GB)', 'SCAN', key='-LARGE-'),
         sg.Radio('WeChat Files', 'SCAN', key='-IM-')],
        [sg.Button('Scan', key='-SCAN-', size=(10, 1)), sg.Button('Delete Selected', key='-DELETE-', size=(15, 1), disabled=True)],
        [sg.Text('Files found:', key='-COUNT-')],
        [sg.Listbox(values=[], key='-FILELIST-', size=(80, 20), select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE, enable_events=True)],
        [sg.StatusBar('Ready', key='-STATUS-')]
    ]
    
    window = sg.Window('DiskCleaner', layout, finalize=True)
    
    files_found = []
    
    while True:
        event, values = window.read()
        
        if event in (sg.WIN_CLOSED, 'Exit'):
            break
        
        elif event == '-SCAN-':
            # Get selected drive
            selected = values['-DRIVE-']
            if not selected:
                continue
            
            drive_letter = selected.split(':')[0] + ':'
            window['-STATUS-'].update('Scanning...')
            window['-DELETE-'].update(disabled=True)
            
            # Determine scan type
            if values['-JUNK-']:
                scan_type = 'junk'
            elif values['-LARGE-']:
                scan_type = 'large'
            else:
                scan_type = 'im'
            
            # Run scan in background
            files_found = scan_directory(drive_letter, scan_type)
            
            # Update list
            display_list = [f"{os.path.basename(f)} ({format_size(s)}) - {f}" for f, n, s in files_found]
            window['-FILELIST-'].update(values=display_list)
            window['-COUNT-'].update(f'Files found: {len(files_found)}')
            window['-STATUS-'].update(f'Scan complete. Found {len(files_found)} files.')
            
            if files_found:
                window['-DELETE-'].update(disabled=False)
        
        elif event == '-DELETE-':
            selected_indices = values['-FILELIST-']
            if not selected_indices:
                continue
            
            confirm = sg.popup_yes_no(f'Delete {len(selected_indices)} files?')
            if confirm == 'Yes':
                deleted = 0
                for idx in selected_indices:
                    filepath = files_found[idx][0]
                    try:
                        os.remove(filepath)
                        deleted += 1
                    except:
                        pass
                
                sg.popup(f'Deleted {deleted} files')
                
                # Refresh scan
                window['-SCAN-'].click()
        
        elif event == '-FILELIST-':
            # Enable delete when files selected
            selected = values['-FILELIST-']
            window['-DELETE-'].update(disabled=len(selected) == 0)
    
    window.close()

if __name__ == '__main__':
    main()
