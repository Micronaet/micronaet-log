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

# -----------------------------------------------------------------------------
#                                Parameters
# -----------------------------------------------------------------------------
# Extract config file name from current name
import pdb; pdb.set_trace()
name = __file__
fullname = '%s.cfg' % name[:-2]

config = ConfigParser.ConfigParser()
config.read([fullname])

# Read from config file:
hostname = config.get('XMLRPC', 'host') 
port = eval(config.get('XMLRPC', 'port'))
database = eval(config.get('XMLRPC', 'database'))
username = eval(config.get('XMLRPC', 'username'))
password = eval(config.get('XMLRPC', 'password'))

code_partner = eval(config.get('code', 'partner'))
code_activity = eval(config.get('code', 'activity'))

# ERPPEEK CLIENT:
erp = erppeek.Client(
    'http://%s:%s' % (hostname, port),
    db=database,
    user=username,
    password=password,
    )

erp_pool = erp.LogActivityEvent
data = {
    }
erp_pool.log_event(data)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
