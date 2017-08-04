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
import erppeek
from datetime import datetime

# -----------------------------------------------------------------------------
# Utility:
# -----------------------------------------------------------------------------
def get_erp_pool(URL, database, username, password):
    ''' Connect to log table in ODOO
    '''
    erp = erppeek.Client(
        URL,
        db=database,
        user=username,
        password=password,
        )   
    return erp.LogActivityEvent   

def log_event(log_f, event, mode='info'):
    ''' Log event on file
    '''    
    event = '[%s] %s - %s\n' % (
        mode.upper(),
        datetime.now(),
        event,
        )
    log_f.write(event)
    return True

# -----------------------------------------------------------------------------
#                                PARAMETERS:
# -----------------------------------------------------------------------------
# Extract config file name from current name
path, name = os.path.split(os.path.abspath(__file__))
fullname = os.path.join(path, 'logger.cfg')
master_config = ConfigParser.ConfigParser()
master_config.read([fullname])

# -----------------------------------------------------------------------------
# MASTER PARAMETER:
# -----------------------------------------------------------------------------
# Master configuration file:
hostname = master_config.get('XMLRPC', 'host') 
port = eval(master_config.get('XMLRPC', 'port'))
database = master_config.get('XMLRPC', 'database')
username = master_config.get('XMLRPC', 'username')
password = master_config.get('XMLRPC', 'password')
code_partner = master_config.get('XMLRPC', 'partner')

log_activity = master_config.get('log', 'activity')

# Open log file:    
log_f = open(log_activity, 'a')

# Link to activity data:
argv = sys.argv
if len(argv) != 2: # No parameters:
    log_event(
        log_f, 'Launch logger.py PARAM (code of operation mandatory!', 'error')

# Passed parameter [operation code, also folder name]:
code_activity = argv[1]

# -----------------------------------------------------------------------------
# OPERATION PARAMETER:
# -----------------------------------------------------------------------------
fullname = os.path.join(path, code_activity, 'operation.cfg')
scriptname = os.path.join(path, code_activity, 'operation.py')
operation_config = ConfigParser.ConfigParser()
operation_config.read([fullname])

log_start = eval(operation_config.get('operation', 'log_start'))
origin = operation_config.get('operation', 'origin')

script = 'python %s' % scriptname # always this command to launch

# Log data:
log = {
    'log_info': os.path.join(path, code_activity, 'log', 'info.log'),
    'log_warning': os.path.join(path, code_activity, 'log', 'warning.log'),
    'log_error': os.path.join(path, code_activity, 'log', 'error.log'),
    }

# -----------------------------------------------------------------------------
# ERPPEEK Client connection:
# -----------------------------------------------------------------------------
log_event(log_f, 'Start launcher, log file: %s' % log_activity)
URL = 'http://%s:%s' % (hostname, port) 
#erp_pool = get_erp_pool(URL, database, username, password)
log_event(log_f, 'Access to URL: %s' % URL)

# -----------------------------------------------------------------------------
# Log start operation:
# -----------------------------------------------------------------------------
data = {
    'code_partner': code_partner,
    'code_activity': code_activity,
    'start': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
    'end': False, # if False is consider as start event in ODOO
    'origin': origin,
    'log_info': '',
    'log_warning': '',
    'log_error': '',
    }

if log_start:
    update_id = erp_pool.log_event(data) # Create start event
    log_event(
        log_f, 'Log the start of operation: event ID: %s' % update_id)
        
log_event(log_f, 'Closing ERP connection')
#del(erp_pool) # For close connection
    
# -----------------------------------------------------------------------------
# Launch script:
# -----------------------------------------------------------------------------
if script:
    log_event(log_f, 'Launch script: %s' % script)
    os.system(script)
    log_event(log_f, 'End script: %s' % script)
else:    
    log_event(log_f, 'Script not present, not launched')
    sys.exit()

# -----------------------------------------------------------------------------
# Log end operation:
# -----------------------------------------------------------------------------
# End time:
data['end'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Log status from file:
log_text = {}
for mode in log:
    f = open(log[mode], 'r')
    for row in f:
        data[mode] += row
    f.close()
    log_event(log_f, 'Get log esit mode: %s' % mode)
    
# -----------------------------------------------------------------------------
# Log activity:
# -----------------------------------------------------------------------------
# Reconnect for timeout problem:
erp_pool = get_erp_pool(URL, database, username, password)
log_event(log_f, 'Reconnect ERP: %s' % erp_pool)

if log_start: 
    # Update event:
    erp_pool.log_event(data, update_id)
    log_event(log_f, 'Update started event: %s' % update_id)
else: 
    # Normal creation of start stop event:
    erp_pool.log_event(data)
    log_event(log_f, 'Create start / stop event: %s' % (data, ))
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
