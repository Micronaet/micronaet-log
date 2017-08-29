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
# Library:
import os
import sys
import ConfigParser
import erppeek
from datetime import datetime

# Constant:
DEFAULT_SERVER_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

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

def change_datetime_gmt(timestamp):
    ''' Change datetime removing gap from now and GMT 0
        passed a datetime object
    '''
    extra_gmt = datetime.now() - datetime.utcnow()
    #ts = datetime.strptime(timestamp, DEFAULT_SERVER_DATETIME_FORMAT) 
    return (timestamp - extra_gmt).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

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

try:
    git_folder = master_config.get('git', 'folder')
except:
    git_folder = '/backup/git/micronaet-log'    

# Open log file:    
log_f = open(log_activity, 'a')

# Link to activity data:
argv = sys.argv
if len(argv) != 2: # No parameters:
    log_event(
        log_f, 'Launch logger.py PARAM (code of operation mandatory!', 'error')

# Passed parameter [operation code, also folder name]:
code_activity = argv[1]

# Update GIT module data before all operations
log_update_git = 'Update Git module folder: %s' % git_folder
log_event(log_f, log_update_git)
os.system('cd %s; git pull' % git_folder)

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
erp_pool = get_erp_pool(URL, database, username, password)
log_event(log_f, 'Access to URL: %s' % URL)

# -----------------------------------------------------------------------------
# Log start operation:
# -----------------------------------------------------------------------------
data = {
    'code_partner': code_partner,
    'code_activity': code_activity,
    'start': change_datetime_gmt(datetime.now()),
    'end': False, # if False is consider as start event in ODOO
    'origin': origin,
    'log_info': '%s\n' % log_update_git,
    'log_warning': '',
    'log_error': '',
    }

if log_start:
    update_id = erp_pool.log_event(data) # Create start event
    log_event(
        log_f, 'Log the start of operation: event ID: %s %s' % (
            update_id,
            data, 
            ))

log_event(log_f, 'Closing ERP connection')
del(erp_pool) # For close connection
    
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
data['end'] = change_datetime_gmt(datetime.now())

# Log status from file:
log_text = {}
for mode in log:
    f = open(log[mode], 'r')
    for row in f:
        data[mode] += row
    f.close()
    log_event(log_f, 'Get log result mode: %s' % mode)
    
# -----------------------------------------------------------------------------
# Log activity:
# -----------------------------------------------------------------------------
# Reconnect for timeout problem:
erp_pool = get_erp_pool(URL, database, username, password)
log_event(log_f, 'Reconnect ERP: %s' % erp_pool)
if log_start: # Update event:
    for i in range(1, 5): # For timout problems:
        try:
            erp_pool.log_event(data, update_id)
            log_event(log_f, 'Update started event: %s' % update_id)
            break 
        except:
            log_event(log_f, 'Timeout try: %s ' % i)
            continue    
else: # Normal creation of start stop event:
    for i in range(1, 5): # For timout problems:
        try:
            erp_pool.log_event(data)
            log_event(log_f, 'Create start / stop event: %s' % (data, ))
            break 
        except:
            log_event(log_f, 'Timeout try: %s ' % i)
            continue    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
