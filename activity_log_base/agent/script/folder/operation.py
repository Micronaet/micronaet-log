#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import pickle
try:
    import ConfigParser
except:  # Pytohn 3 compatibility:
    import configparser as ConfigParser
from datetime import datetime

# -----------------------------------------------------------------------------
#                                UTILITY:
# -----------------------------------------------------------------------------
def closing_operations(log_f):
    ''' Operation that will be done at the end of the script
    '''
    for mode in log_f:
        log_f[mode].close()
    sys.exit()

# -----------------------------------------------------------------------------
#                                Parameters
# -----------------------------------------------------------------------------
# A. Extract config file name from current name
path, name = os.path.split(os.path.abspath(__file__))
fullname = os.path.join(path, 'operation.cfg')

# Log folder:
log_folder = os.path.join(path, 'log') # log folder path
pickle_file = os.path.join(log_folder, 'last.pickle') # Last folder files
os.system('mkdir -p %s' % log_folder)

config = ConfigParser.ConfigParser()
config.read([fullname])

# B. Read from config file:
origin = config.get('operation', 'origin') # XXX not used

# Folder:
folder = config.get('file', 'folder')
extensions = config.get('file', 'extensions')
with_subfolder = eval(config.get('file', 'subfolder'))
log_events = eval(config.get('file', 'log'))
time_range = eval(config.get('file', 'time_range'))

# Mount:
mount_command = config.get('operation', 'mount')
umount_command = 'umount -l %s' % folder # Lazy option to force

# -----------------------------------------------------------------------------
# Log event:
# -----------------------------------------------------------------------------
# 1. Clean log file and create new:
log = {
    'info': os.path.join(log_folder, 'info.log'),
    'warning': os.path.join(log_folder, 'warning.log'),
    'error': os.path.join(log_folder, 'error.log'),
    }

# Remove log file and create new:
log_f = {}
for mode in log:
    try:
        log_f[mode] = open(log[mode], 'w')
        print('[INFO] File log reset: %s' % log[mode])
    except:
        print('[WARNING] File log not found: %s' % log[mode])

# -----------------------------------------------------------------------------
# Operation scripts:
# -----------------------------------------------------------------------------
print('[INFO] 1. Mount linked resource: %s' % mount_command)
os.system(mount_command)

# -----------------------------------------------------------------------------
#                              Read folder content:
# -----------------------------------------------------------------------------
print('[INFO] 2. Check root folder: %s' % folder)

current = set()
for root, folders, files in os.walk(folder):
    for filename in files:
        extension = filename.split('.')[-1].lower()
        if extensions and extension not in extensions:
            print('Extension not used: %s' % filename)
            continue

        current.add(os.path.join(root, filename))

    if not with_subfolder:
        print('Check only root folder: %s' % root)
        break

# -----------------------------------------------------------------------------
#                                   Check operation:
# -----------------------------------------------------------------------------
if os.path.isfile(pickle_file):
    print('[INFO] 3. Compare with pickle file: %s' % pickle_file)

    pickle_f = open(pickle_file, 'rb')
    previous = pickle.load(pickle_f)
    pickle_f.close()

    removed = previous - current
    created = current - previous

    total_removed = len(removed)
    total_created = len(created)

    # -------------------------------------------------------------------------
    # Info log:
    # -------------------------------------------------------------------------
    log_f['info'].write('New files: %s, Removed files: %s' % (
        total_created,
        total_removed,
        ))

    # -------------------------------------------------------------------------
    # Error log:
    # -------------------------------------------------------------------------
    if removed and 'remove' in log_events:
        log_f['error'].write('Removed files present! #%s' % total_removed)

    if not removed and 'no_remove' in log_events:
        log_f['error'].write('No remove file error!')

    if created and 'create' in log_events:
        log_f['error'].write('New files present! #%s' % total_created)

    if not created and 'no_create' in log_events:
        log_f['error'].write('No new file error!')

# Write pickle with current (of first time):
print('[INFO] 4. Save pickle file: %s' % pickle_file)
pickle_f = open(pickle_file, 'wb')
pickle.dump(current, pickle_f)
pickle_f.close()

# -----------------------------------------------------------------------------
# Server data umount:
# -----------------------------------------------------------------------------
print('[INFO] 5. Umount linked resource: %s' % umount_command)
os.system(umount_command)

# Closing operations:
closing_operations(log_f)
