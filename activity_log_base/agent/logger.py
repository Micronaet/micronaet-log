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

# Read from config file:
hostname = config.get('XMLRPC', 'host') 
port = eval(config.get('XMLRPC', 'port'))
database = config.get('XMLRPC', 'database')
username = config.get('XMLRPC', 'username')
password = config.get('XMLRPC', 'password')

code_partner = config.get('code', 'partner')
code_activity = config.get('code', 'activity')
origin = config.get('code', 'origin')

script = config.get('script', 'command')

log_folder = config.get('log', 'folder')
log = {
    'log_info': os.path.join(
        log_folder, config.get('log', 'info')),
    'log_warning': os.path.join(
        log_folder, config.get('log', 'warning')),
    'log_error': os.path.join(
        log_folder, config.get('log', 'error')),
    }

# -----------------------------------------------------------------------------
# ERPPEEK Client connection:
# -----------------------------------------------------------------------------
erp = erppeek.Client(
    'http://%s:%s' % (hostname, port),
    db=database,
    user=username,
    password=password,
    )

# -----------------------------------------------------------------------------
# TODO log start operation?
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Launch script:
# -----------------------------------------------------------------------------
data = {
    'code_partner': code_partner,
    'code_activity': code_activity,
    'start': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
    #'end': ,
    'origin': origin,
    'log_info': '',
    'log_warning': '',
    'log_error': '',
    }

if script:
    os.system(script)

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
    
# -----------------------------------------------------------------------------
# Log activity:
# -----------------------------------------------------------------------------
erp_pool = erp.LogActivityEvent    
erp_pool.log_event(data)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
