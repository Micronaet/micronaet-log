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
import csv
import erppeek
import ConfigParser

# ----------------
# Read parameters:
# ----------------
config = ConfigParser.ConfigParser()
config.read(['odoo.cfg'])

# -----------------------------------------------------------------------------
# Erpeek client ODOO:
# -----------------------------------------------------------------------------
erp = {}
for mode in ['in', 'out']:
    server = config.get(mode, 'server')
    port = config.get(mode, 'port')
    dbname = config.get(mode, 'dbname')
    user = config.get(mode, 'user')
    password = config.get(mode, 'pwd')
    
    erp[mode] = erppeek.Client(
        'http://%s:%s' % (
            server, port),
        db=dbname,
        user=user,
        password=password,
        )
    print 'Connect with ODOO %s: %s' % (mode, erp[mode])    

# -----------------------------------------------------------------------------
#                             Manual importation:
# -----------------------------------------------------------------------------
company_id = 1 # Micronaet
country_id = 109 # Italy

# -----------------------------------------------------------------------------
#                             Automatic migration:
# -----------------------------------------------------------------------------
# -------
# Partner
# -------
print 'Import Partner'
partner_db = {}
pool_in = erp['in'].ResPartner
pool_out = erp['out'].ResPartner
record_ids = pool_in.search([('log_code', '!=', False)])
print 'Tot selected %s' % len(record_ids)

i = 0
for record in pool_in.browse(record_ids):
    i += 1
    
    # Input:
    name = record.name
    log_code = record.log_code
    
    item_ids = pool_out.search([
        '|',
        ('name', '=', name),
        ('log_code', '=', log_code)])
        
    data = {
        'active': True,
        'is_company': True,
        'name': name,
        'log_code': log_code,
        'customer': True,
        'email': record.email,
        'lang': 'it_IT',
        'country_id': country_id,
        }

    if item_ids:
        item_id = item_ids[0]
        pool_out.write(item_id, data)
        print '%s. Update record: %s (%s > %s)' % (i, name, record.id, item_id)
    else:        
        item_id = pool_out.create(data).id
        print '%s. Create record: %s (%s > %s)' % (i, name, record.id, item_id)
    partner_db[record.id] = item_id

# --------
# Category
# --------
print 'Import Category'
category_db = {}
pool_in = erp['in'].LogCategory
pool_out = erp['out'].LogCategory
record_ids = pool_in.search([])
print 'Tot selected %s' % len(record_ids)

i = 0
for record in pool_in.browse(record_ids):
    i += 1
    
    # Input:
    name = record.name
    code = record.code
    
    item_ids = pool_out.search([
        ('code', '=', code),
        ])
        
    data = {
        'is_active': record.is_active,
        'name': name,
        'code': code,
        'note': record.note,
        }

    if item_ids:
        item_id = item_ids[0]
        pool_out.write(item_id, data)
        print '%s. Update record: %s' % (i, name)
    else:        
        item_id = pool_out.create(data).id
        print '%s. Create record: %s' % (i, name)
    category_db[record.id] = item_id

# --------
# Activity
# --------
print 'Import activity'
activity_db = {}
pool_in = erp['in'].LogActivity
pool_out = erp['out'].LogActivity
record_ids = pool_in.search([])
print 'Tot selected %s' % len(record_ids)

i = 0
for record in pool_in.browse(record_ids):
    i += 1
    
    # Input:
    name = record.name
    code = record.code
    partner_id = record.partner_id.id
    category_id = record.category_id.id
    
    new_partner_id = partner_db.get(partner_id, False)
    if not new_partner_id:
        print 'Error no partner_id: %s (jumped)' % partner_id
        continue
    item_ids = pool_out.search([
        ('code', '=', code),
        ('partner_id', '=', new_partner_id),
        ])
        
    data = {
        'is_active': record.is_active,
        'monitor': record.monitor,
        'name': name,
        'code': code,
        
        'partner_id': new_partner_id, # XXX always present
        'category_id': category_db.get(category_id, False), # XXX always present
        
        'from_date': record.from_date,
        'to_date': record.to_date,        
        'duration': record.duration,
        'auto_duration': record.auto_duration,
        'check_duration': record.check_duration,
        'duration_warning_range': record.duration_warning_range,
        'duration_error_range': record.duration_error_range,
        
        'log_mode': record.log_mode,
        'log_check_every': record.log_check_every,
        'log_check_count': record.log_check_count,
        'log_check_unwrited_html': record.log_check_unwrited_html,

        'script': record.script,
        'origin': record.origin,

        'server': record.server,
        'uptime': record.uptime,
        'config': record.config,
        'cron': record.cron,
        
        # cron_daily_exec,
        
        'note': record.note,
        
        # o2m Telegram
        # o2m Partner        
        }

    if item_ids:
        item_id = item_ids[0]
        pool_out.write(item_id, data)
        print '%s. Update record: %s' % (i, name)
    else:   
        item_id = pool_out.create(data).id
        print '%s. Create record: %s' % (i, name)
    activity_db[record.id] = item_id

# -----
# Event
# -----
print 'Import activity event'
event_db = {}
pool_in = erp['in'].LogActivityEvent
pool_out = erp['out'].LogActivityEvent
record_ids = pool_in.search([])
print 'Tot selected %s' % len(record_ids)

i = 0
for record in pool_in.browse(record_ids):
    i += 1
    
    # Input:
    datetime = record.datetime
    activity_id = record.activity_id.id
    partner_id = record.partner_id.id
    
    new_activity_id = activity_db.get(activity_id, False)
    new_partner_id = partner_db.get(partner_id, False)
    
    if not new_activity_id:
        print 'Error no activity_id: %s (jumped)' % activity_id
        continue
        
    if not new_partner_id:
        print 'Error no partner_id: %s (jumped)' % partner_id
        continue

    item_ids = pool_out.search([
        ('datetime', '=', datetime),
        ('activity_id', '=', new_activity_id),
        ])
        
    data = {
        'datetime': datetime,
        'activity_id': new_activity_id,
        'partner_id': new_partner_id,
        'start': record.start,
        'end': record.end,
        'duration': record.duration,
        'error_comment': record.error_comment,
        'mark_ok': record.mark_ok,
        'log_info': record.log_info,
        'log_warning': record.log_warning,
        'log_error': record.log_error,
        'mark_ok_comment': record.mark_ok_comment,
        'origin': record.origin,
        }

    if item_ids:
        item_id = item_ids[0]
        pool_out.write(item_id, data)
        print '%s. Update record: %s' % (i, datetime)
    else:   
        item_id = pool_out.create(data).id
        print '%s. Create record: %s' % (i, datetime)
    event_db[record.id] = item_id

# -------
# History
# -------
print 'Import activity history'
event_db = {}
pool_in = erp['in'].LogActivityHistory
pool_out = erp['out'].LogActivityHistory
record_ids = pool_in.search([])
print 'Tot selected %s' % len(record_ids)

i = 0
for record in pool_in.browse(record_ids):
    i += 1
    
    # Input:
    create_date = record.create_date
    activity_id = record.activity_id.id
    
    new_activity_id = activity_db.get(activity_id, False)
    
    if not new_activity_id:
        print 'Error no activity_id: %s (jumped)' % activity_id
        continue
        
    item_ids = pool_out.search([
        ('create_date', '=', create_date),
        ('activity_id', '=', new_activity_id),
        ])
        
    data = {
        'create_date': create_date,
        'activity_id': new_activity_id,
        'mode': record.mode,
        'old': record.old,
        }

    if item_ids:
        item_id = item_ids[0]
        pool_out.write(item_id, data)
        print '%s. Update record: %s' % (i, create_date)
    else:   
        item_id = pool_out.create(data).id
        print '%s. Create record: %s' % (i, create_date)
    event_db[record.id] = item_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
