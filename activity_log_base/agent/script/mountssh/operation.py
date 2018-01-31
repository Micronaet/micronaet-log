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

# Check file parameter:
hostname = config.get('operation', 'hostname') # Host access
check = config.get('operation', 'check') # File to check
esit = config.get('operation', 'esit') # Result in command return (start)
mask = config.get('operation', 'mask').replace('|', '\n') # pipe means return
check_command = mask % (hostname, check)

# Read from config file:
origin = config.get('operation', 'origin') # XXX not used
error = config.get('operation', 'error')

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
import pdb; pdb.set_trace()
res = os.popen(check_command).read()
if res.startswith(esit):
    log_f['info'].write('Correttamente montato\n')
else:    
    log_f['error'].write('Non montato\n')
    
# CLosing operations:
closing_operations(log_f)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
