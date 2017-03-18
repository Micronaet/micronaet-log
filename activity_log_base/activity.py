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
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class LogCategory(orm.Model):
    """ Model name: Log Category
    """    
    _name = 'log.category'
    _description = 'Log category'
    _rec_name = 'name'
    _order = 'name'
    
    _columns = {
        'active': fields.boolean('Active'),
        'code': fields.char('Code', size=15),
        'name': fields.char('Category', size=64, required=True),
        'note': fields.text('Note'),
        }
    
class LogEvent(orm.Model):
    """ Model name: Log event
    """
    
    _name = 'log.event'
    _description = 'Log event'
    _rec_name = 'name'
    _order = 'name'
    
    _columns = {
        'active': fields.boolean('Active'),
        'code': fields.char('Code', size=15),
        'monitor': fields.boolean(
            'Monitor', help='Monitored event are represented in dashboard'),
        'name': fields.char('Event', size=64, required=True),
        'from_date': fields.date(
            'From date', 
            help='For period event, time was the current start time'),
        'to_date': fields.date('To date', help='End period for timed event'),
        'duration': fields.float(
            'Duration', digits=(16, 3), help='Normal duration of operation'),
        'duration_warning_range': fields.float(
            'Warning range', digits=(16, 3), 
            help='-/+ perc. time for raise warning'),
        'duration_error_range': fields.float(
            'Warning error', digits=(16, 3), 
            help='-/+ perc. time for raise error'),
        'auto_duration': fields.boolean(
            'Autoduration', 
            help='If checked duration will be update automatically'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'category_id': fields.many2one('log.category', 'Category'),
        'email_alert': fields.boolean('Email alert'),
        'email_error': fields.char('Email error', size=180),
        'email_warning': fields.char('Email warning', size=180),
        'script': fields.text('Script'),
        'origin': fields.text(
            'Origin', help='Info of origin server for the activity'),
        
        'note': fields.text('Note'),
        'state': fields.selection([
            ('unactive', 'Unactive'), # not working
            ('active', 'Active'), # Working
            ('pause', 'Pause'), # Currently not work butt soon yes
            ('timed', 'Out of time'), # Out of date period            
            ], 'State',
            )
        }
    
    _defaults = {
        # Default value for state:
        'state': lambda *x: 'active',
        }

class LogActivityEvent(orm.Model):
    """ Model name: LogActivityEvent
    """
    
    _name = 'log.activity.event'
    _description = 'Event'
    _rec_name = 'datetime'
    _order = 'datetime'
    
    _columns = {
        'datetime': fields.date('Date', required=True),
        'activity_id': fields.many2one(
            'log.activity', 'Activity'),
        'start': fields.date('Start'),
        'end': fields.date('End'),
        'duration': fields.float(
            'Duration', digits=(16, 3), help='Duration of operation'),
            
        'origin': fields.text('Origin', help='Server info (log origin)'),
        'log': fields.text('Log'),
        'log_warning': fields.text('Log warning'),
        'log_error': fields.text('Log error'),
        'mark_ok': fields.boolean('Mark as OK' 
            help='For error / warning message', 
        'state': fields.selection([
            ('correct', 'Correct'),
            ('warning', 'Warning'),
            ('error', 'Error'),
            ], 'State'),
        }
    
    _defaults = {
       'datetime': lambda *a: datetime.now(
            DEFAULT_SERVER_DATETIME_FORMAT).strftime(),
        'state': lambda *x: 'correct',
        }

class LogCategory(orm.Model):
    """ Model name: Log Category
    """    
    _inherit = 'log.category'

    _columns = {
        'activity_ids': fields.one2many(
            'log.activity', 'category_id', 'Activity'),
    }

class ResUser(orm.Model):
    """ Model name: ResUser
    """    
    _inherit = 'res.users'
    
    _columns = {
        'log_partner_id': fields.many2one('res.partner', 'Log partner'),
    }

class ResPartner(orm.Model):
    """ Model name: Res partner
    """    
    _inherit = 'res.partner'
    
    _columns = {
        'log_users_ids': fields.one2many(
            'res.users', 'log_partner_id', 'Log user'),
        'log_activity_ids': fields.one2many(
            'log.activity', 'partner_id', 'Log activity'),
    }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
