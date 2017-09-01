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
import ConfigParser
from datetime import datetime

# -----------------------------------------------------------------------------
#                                UTILITY:
# -----------------------------------------------------------------------------
def closing_operations(log_f):
    ''' Operation that will be done at the end of the script
    '''
    # Close log file:
    for mode in log_f:
        log_f[mode].close()
    # Exit
    sys.exit()

# -----------------------------------------------------------------------------
#                                Parameters
# -----------------------------------------------------------------------------
# Extract config file name from current name
path, name = os.path.split(os.path.abspath(__file__))
fullname = os.path.join(path, 'operation.cfg')

# Log folder:
log_folder = os.path.join(path, 'log') # log folder path
os.system('mkdir -p %s' % log_folder)

config = ConfigParser.ConfigParser()
config.read([fullname])

# Read from config file:
path = config.get('operation', 'path') 
os.system('mkdir -p %s' % path) # Create mount poing if not exist
mount_command = config.get('operation', 'mount')
umount_command = 'umount %s' % path
error = config.get('operation', 'error')

# File check:
check_file = eval(config.get('operation', 'check'))
if type(check_file) not in (tuple, list):
    check_file = (check_file, )
check_file = os.path.join(path, *check_file)

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
        print '[INFO] File log reset: %s' % log[mode]
    except:
        print '[WARNING] File log not found: %s' % log[mode]

# -----------------------------------------------------------------------------
# Check mount procedure:
# -----------------------------------------------------------------------------
# 2. Mount operation:
try:
    print '[INFO] A. Mount server folder: %s' % mount_command
    os.system(mount_command)
except:
    log_f['error'].write('Mount error: %s\n' % mount_command)
    closing_operations(log_f)
    
# 3. Check file for get mount information:
print '[INFO] B. Check file reveal the mount: %s' % check_file
if os.path.exists(check_file):
    log_f['info'].write('Correttamente montato\n')
else:    
    log_f['error'].write('%s\n' % error)
    
# 4. Umount operation:
try:
    print '[INFO] C. Umount server folder: %s' % umount_command
    os.system(umount_command)
except:
    log_f['warning'].write('Unmount problems: %s\n' % path)
    closing_operations(log_f)

# CLosing operations:
closing_operations(log_f)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
