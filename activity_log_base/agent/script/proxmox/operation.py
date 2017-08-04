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

import pdb; pdb.set_trace()
# -----------------------------------------------------------------------------
#                                Parameters
# -----------------------------------------------------------------------------
# Extract config file name from current name
path, name = os.path.split(os.path.abspath(__file__))
fullname = os.path.join(path, 'operation.cfg')
log_folder = os.path.join(path, 'log') # log folder path (always in this folder)
# syslog file? (now no log)
config = ConfigParser.ConfigParser()
config.read([fullname])

# Read from config file:
script = config.get('operation', 'backup') 
result = config.get('operation', 'result')

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
# Launch script:
# -----------------------------------------------------------------------------
os.system(script)

# -----------------------------------------------------------------------------
# Parse log file (save in log file info, warning, error):
# -----------------------------------------------------------------------------
task_ok = False
for row in open(result, 'r'):
    # -------------------------------------------------------------------------
    # Information:
    # -------------------------------------------------------------------------
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
        
    # -------------------------------------------------------------------------
    # Warning:
    # -------------------------------------------------------------------------
    
    # -------------------------------------------------------------------------
    # Error: 
    # -------------------------------------------------------------------------
    elif 'error' in row:     
        # Archive info
        log_f['error'].write('%s\n' % row)

    # -------------------------------------------------------------------------
    # Check elements:
    # -------------------------------------------------------------------------
    elif 'finished successfully' in row:
        task_ok = True    

if not task_ok:
    log_f['error'].write('Task KO\n')

# Close log file:
for mode in log_f:
    log_f[mode].close()    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
