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
#import shutil
import ConfigParser
import pickle
#import erppeek

# Ilo management:
import hpilo

# Telegram bot:
import telepot
#from pprint import pprint

from datetime import datetime

# -----------------------------------------------------------------------------
#                                Parameters
# -----------------------------------------------------------------------------
# Extract config file name from current name
fullname = './ilo.cfg' # same folder
pickle_file = './temperature_history.pickle'
notification_info = 24 * 60 * 60 # seconds

config = ConfigParser.ConfigParser()
config.read([fullname])

# Ilo access:
hostname = config.get('ilo', 'hostname')
port = eval(config.get('ilo', 'port'))
username = config.get('ilo', 'username')
password = config.get('ilo', 'password')
timeout = eval(config.get('ilo', 'timeout'))

# Alarm:
warning = eval(config.get('temperature', 'warning'))
error = eval(config.get('temperature', 'error'))

# Telegram:
telegram_token = config.get('telegram', 'token')
telegram_group = config.get('telegram', 'group')

# -----------------------------------------------------------------------------
#                                Access Ilo
# -----------------------------------------------------------------------------
ilo = hpilo.Ilo(
    hostname=hostname, 
    login=username, 
    password=password, 
    timeout=timeout, 
    port=port,
    #protocol=None,
    #delayed=False, 
    #ssl_version=None
    )

# -----------------------------------------------------------------------------
#                          Get temperature status
# -----------------------------------------------------------------------------
temperature = ilo.get_embedded_health()['temperature']

# Echo temperature check:
status = temperature['01-Inlet Ambient']['status']
degree = temperature['01-Inlet Ambient']['currentreading'][0]

error_status = 0
if degree >= error: 
    status_text = \
        '[ERROR] Rilevato %s°C, passato il range massimo: %s' % (
            degree, error)
    error_status = 2        
elif degree >= warning: 
    status_text = \
        '[WARNING] Rilevato %s°C, passato il range di allerta: %s' % (
            degree, warning)
    error_status = 1         
else:
    status_text = '[INFO]: Rilevato %s°C, nel range corretto < %s' % (
        degree, warning)
print status_text        

# -----------------------------------------------------------------------------
#                      Get comunication info (historty)
# -----------------------------------------------------------------------------
now = datetime.now()

# Read previous notification:
try: 
    pickle_f = open(pickle_file, 'rb')
    history = pickle.load(pickle_f) or {}
except: 
    history = {} # no file empty dict
    
last = history.get('last', False)
notification = False
gap = now - last
gap_seconds = gap.days * 24 * 60 * 60 + gap.seconds
if not last or gap_seconds  > notification_info:
    notification = True    
    history = {
        'last': now,
        }
        
    # Write history file:    
    try:
        pickle_f = open(pickle_file, 'wb')
        pickle.dump(history, pickle_f)
    except:
        print '[ERROR] Pickle file inaccessibile: %s' % pickle_file

# -----------------------------------------------------------------------------
#                              Comunicate Telegram
# -----------------------------------------------------------------------------
# Notifcation if info time out or error:
if notification or error_status > 0:
    bot = telepot.Bot(telegram_token)
    bot.getMe()
    bot.sendMessage(telegram_group, status_text)
else:
    print '[INFO] No comunication in telegram'
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
