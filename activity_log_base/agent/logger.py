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
#                                Parameters
# -----------------------------------------------------------------------------
# Extract config file name from current name
name = __file__
fullname = '%scfg' % name[:-2] # remove py # XXX BETTER!!! (also pyw)

config = ConfigParser.ConfigParser()
config.read([fullname])

# -----------------------------------------------------------------------------
# Read from config file:
# -----------------------------------------------------------------------------
# XMLRPC connection data:
hostname = config.get('XMLRPC', 'host') 
port = eval(config.get('XMLRPC', 'port'))
database = config.get('XMLRPC', 'database')
username = config.get('XMLRPC', 'username')
password = config.get('XMLRPC', 'password')
log_start = eval(config.get('XMLRPC', 'log_start'))

# Link to activity data:
code_partner = config.get('code', 'partner')
code_activity = config.get('code', 'activity')
origin = config.get('code', 'origin')

# Script data:
script = config.get('script', 'command')

# Log data:
log_activity = config.get('log', 'activity')
log_folder = config.get('log', 'folder')
log = {
    'log_info': os.path.join(
        log_folder, config.get('log', 'info')),
    'log_warning': os.path.join(
        log_folder, config.get('log', 'warning')),
    'log_error': os.path.join(
        log_folder, config.get('log', 'error')),
    }

# Open log file:    
log_f = open(log_activity, 'a')

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
    
# -----------------------------------------------------------------------------
# Launch script:
# -----------------------------------------------------------------------------
if script:
    log_event(log_f, 'Launch script: %s' % script)
    os.system(script)
    log_event(log_f, 'End script: %s' % script)

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
