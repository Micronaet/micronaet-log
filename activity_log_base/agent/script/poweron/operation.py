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
    try:
        os.remove(result)
        print('[INFO] Remove proxmox result file')
    except:
        print('[ERROR] Cannot remove proxmox result file')

# -----------------------------------------------------------------------------
#                                Parameters
# -----------------------------------------------------------------------------
# Extract config file name from current name
path, name = os.path.split(os.path.abspath(__file__))
fullname = os.path.join(path, 'operation.cfg')
log_folder = os.path.join(path, 'log') # log folder path (always in this folder)
os.system('mkdir -p %s' % log_folder)

# TODO syslog file? (now no log)
config = ConfigParser.ConfigParser()
config.read([fullname])

# Read from config file:
script = config.get('operation', 'backup')
result = config.get('operation', 'result')

# Clean previous file:
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
        print('[INFO] File log reset: %s' % log[mode])
    except:
        print('[WARNING] File log not found: %s' % log[mode])

# -----------------------------------------------------------------------------
# Launch script:
# -----------------------------------------------------------------------------
print('[INFO] Start backup script: %s' % script)
os.system(script)
print('[INFO] End backup script: %s' % script)

# -----------------------------------------------------------------------------
#                              PARSE 3 LOG FILE:
# -----------------------------------------------------------------------------
task_ok = False
print('[INFO] Parse proxmox result file: %s' % result)
try:
    result_f = open(result, 'r')
    for row in result_f:
        # ---------------------------------------------------------------------
        # Information:
        # ---------------------------------------------------------------------
        row = row.lower()
        if 'finished backup' in row:
            # Finish backup VM:
            log_f['info'].write('%s\n' % row)
        elif ' transferred ' in row:
            # Transfer performance:
            log_f['info'].write('%s\n' % row)
        elif 'creating archive' in row:
            # Archive info
            log_f['info'].write('%s\n' % row)

        # ---------------------------------------------------------------------
        # Warning:
        # ---------------------------------------------------------------------

        # ---------------------------------------------------------------------
        # Error:
        # ---------------------------------------------------------------------
        elif 'error' in row:
            # Archive info
            log_f['error'].write('%s\n' % row)

        # ---------------------------------------------------------------------
        # Check elements:
        # ---------------------------------------------------------------------
        elif 'finished successfully' in row:
            task_ok = True
    result_f.close()
except:
    print('[ERROR] No proxmox result file: %s' % result)
    log_f['error'].write('Error reading result file\n')
print('[INFO] End parse proxmox result file: %s' % result)

if not task_ok:
    print('[ERROR] Task esit is KO')
    log_f['error'].write('Task KO\n')

# Close log file:
for mode in log_f:
    log_f[mode].close()

# -----------------------------------------------------------------------------
# Remove proxmox result file:
# -----------------------------------------------------------------------------
clean_result_file(result)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
