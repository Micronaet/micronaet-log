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
import ConfigParser
from datetime import datetime

# -----------------------------------------------------------------------------
#                                Utility:
# -----------------------------------------------------------------------------
def clean_result_file(result):
    ''' Clean result file used
    '''
    try:
        os.remove(result)
        print '[INFO] Remove rsync result file'
    except:
        print '[ERROR] Cannot remove rsync result file'
       
def closing_operations(log_f, result):
    ''' Operation that will be done at the end of the script
    '''
    # Close log file:
    for mode in log_f:
        log_f[mode].close()

    # Remove rsync result file:
    clean_result_file(result)
    
    # Exit
    sys.exit()
    
# -----------------------------------------------------------------------------
#                                Parameters
# -----------------------------------------------------------------------------
# Extract config file name from current name
path, name = os.path.split(os.path.abspath(__file__))
fullname = os.path.join(path, 'operation.cfg')
log_folder = os.path.join(path, 'log') # log folder path
os.system('mkdir -p %s' % log_folder)

# Config parameter:
config = ConfigParser.ConfigParser()
config.read([fullname])

# Folder:
path = config.get('operation', 'path') 
folders = eval(config.get('operation', 'folders'))
exclude = eval(config.get('operation', 'exclude'))
history = eval(config.get('operation', 'history'))
from_folder = os.path.join(path, 'mount')
to_folder = os.path.join(path, '0')

# Mount parameters:
mount_command = config.get('operation', 'mount')
umount_command = 'umount %s' % from_folder
check_file = config.get('operation', 'check')
check_file = os.path.join(from_folder, check_file) # fullname for check file 

result = os.path.join(log_folder, 'rsync.log')
script_mask = 'rsync -avh \'%s/\' \'%s\' --log-file=%s'

# Remove rsync result file:    
clean_result_file(result)

# -----------------------------------------------------------------------------
# Log event:
# -----------------------------------------------------------------------------
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
# Operation scripts:
# -----------------------------------------------------------------------------
print '[INFO] 1. Mount linked resource: %s' % mount_command
os.system(mount_command)

print '[INFO] 2. Check correct mount with file: %s' % check_file
if not os.path.isfile(check_file):
    log_f['error'].write('Cannot mount linked server\n')
    closing_operations(log_f, result) # END HERE

# Remove folder:
# TODO use subprocess for get result of operation
command = 'rm -r %s' % os.path.join(path, str(history)) # Last folder
print '[INFO] 3. Remove command: %s' % command
os.system(command)

# Move folder number:
print '[INFO] 4. History operations, # folder: [1 - %s]' % history
for h_folder in range(history, 1, -1):
    command = 'mv %s %s' % (
        os.path.join(path, str(h_folder - 1)),
        os.path.join(path, str(h_folder)),
        )
    print '[INFO] 4a. Move history command: %s' % command
    os.system(command)

# Hard link copy:    
if history >= 1:
    command = 'cp -lr %s %s' % (
        os.path.join(path, '0'),
        os.path.join(path, '1'),
        )
    print '[INFO] 5. Hard link copy: %s' % command
    os.system(command)

print '[INFO] 6. Start rsync operations, folders: %s' % folders
if folders:
    for f in folders:
        script_multi = script_mask % (
            os.path.join(from_folder, f),
            os.path.join(to_folder, f),
            result, # always in append mode
            )
        print '[INFO] 6a. Multi rsync operations: %s' % script_multi
        log_f['info'].write('Rsync folder: %s\n' % f)
        os.system(script_multi)
                
else: # no folders all
    script = script_mask % (
        from_folder,
        to_folder,
        result,
        )
    print '[INFO] 6b. Single rsync operations: %s' % script
    log_f['info'].write('Rsync folder all folder')
    os.system(script)

print '[INFO] 7. Umount linked resource: %s' % umount_command
os.system(umount_command)
if os.path.isfile(check_file):
    log_f['warning'].write('Cannot umount linked server\n')    

# -----------------------------------------------------------------------------
#                              PARSE LOG FILE:
# -----------------------------------------------------------------------------
task_ok = True
print '[INFO] 8. Parse rsync result file: %s' % result
try:
    result_f = open(result, 'r')
    for row in result_f:
        # ---------------------------------------------------------------------
        # Information:
        # ---------------------------------------------------------------------
        row = row.lower()
        # Remove exclude file from log row:
        for term in exclude:
            if 'error' in row and term in row: # only warning
                log_f['warning'].write('Exclude %s in row: %s\n' % (term, row))
                continue
                
        # Check other data:
        if ' received ' in row:
            log_f['info'].write('%s\n' % row)
        elif ' total size ' in row:
            log_f['info'].write('%s\n' % row)
            
        # ---------------------------------------------------------------------
        # Warning:
        # ---------------------------------------------------------------------
        
        # ---------------------------------------------------------------------
        # Error: 
        # ---------------------------------------------------------------------
        elif 'error' in row:     
            task_ok = False
            # Archive info
            log_f['error'].write('%s\n' % row)

        # ---------------------------------------------------------------------
        # Check elements:
        # ---------------------------------------------------------------------
        #elif 'finished successfully' in row:
        #    task_ok = True    
    result_f.close()
except:
    print '[ERROR] No rsync result file: %s' % result
    log_f['error'].write('Error reading result file\n')
print '[INFO] 9. End parse rsync result file: %s' % result
    
if not task_ok:
    print '[ERROR] Task esit is KO'
    log_f['error'].write('Task KO\n')

closing_operations(log_f, result)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
