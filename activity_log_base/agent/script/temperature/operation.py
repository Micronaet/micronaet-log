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
import hpilo
#import telepot

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
# Extract config file name from current name
path, name = os.path.split(os.path.abspath(__file__))
fullname = os.path.join(path, 'operation.cfg')

# Log folder:
log_folder = os.path.join(path, 'log') # log folder path
os.system('mkdir -p %s' % log_folder)

config = ConfigParser.ConfigParser()
config.read([fullname])

# Read from config file:
origin = config.get('operation', 'origin') # XXX not used

# Ilo Parameter:
ilo_hostname = config.get('ilo', 'hostname')
ilo_port = eval(config.get('ilo', 'port'))
ilo_username = config.get('ilo', 'username')
ilo_password = config.get('ilo', 'password')
ilo_timeout = eval(config.get('ilo', 'timeout'))

# Alarm temperature:
warning = eval(config.get('temperature', 'warning'))
error = eval(config.get('temperature', 'error'))

# Telegram setup:
#telegram_token = config.get('telegram', 'token')
#telegram_group = config.get('telegram', 'group')

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
#                                Access Ilo
# -----------------------------------------------------------------------------
ilo = hpilo.Ilo(
    hostname=ilo_hostname, 
    login=ilo_username, 
    password=ilo_password,
    timeout=ilo_timeout,
    port=ilo_port,
    #protocol=None,
    #delayed=False, 
    #ssl_version=None
    )

# Get temperature status
temperature = ilo.get_embedded_health()['temperature']
status = temperature['01-Inlet Ambient']['status']
degree = temperature['01-Inlet Ambient']['currentreading'][0]

# Check temperature range for error:
if degree >= error: 
    log_f['error'].write('<br/>ERRORE Rilevato %s°C, passato: %s°C' % (
            degree, error))
elif degree >= warning: 
    log_f['warnint'].write('<br/>WARNING Rilevato %s°C, passato: %s°C' % (
            degree, warning))
else:
    log_f['info'].write('<br/>INFO Rilevato %s°C, < %s°C' % (
        degree, warning))

# -----------------------------------------------------------------------------
#                              Comunicate Telegram
# -----------------------------------------------------------------------------
# Notifcation if info time out or error:
#bot = telepot.Bot(telegram_token)
#bot.getMe()
#bot.sendMessage(telegram_group, status_text)
    
# CLosing operations:
closing_operations(log_f)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
