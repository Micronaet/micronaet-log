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
    _order = 'name'
    
    _columns = {
        'active': fields.boolean('Active'),
        'code': fields.char('Code', size=15),
        'name': fields.char('Category', size=64, required=True),
        'note': fields.text('Note'),
        }
    
class LogActivity(orm.Model):
    """ Model name: Log event
    """
    
    _name = 'log.activity'
    _description = 'Log activity'
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
        'check_duration':fields.boolean(
            'Check duration', help='Check duration period of operation'),
        'duration_warning_range': fields.float(
            'Warning range', digits=(16, 3), 
            help='-/+ perc. time for raise warning'),
        'duration_error_range': fields.float(
            'Error range', digits=(16, 3), 
            help='-/+ perc. time for raise error'),
        'auto_duration': fields.boolean(
            'Autoduration', 
            help='If checked duration will be update automatically'),
        'partner_id': fields.many2one(
            'res.partner', 'Partner', required=True),
        'category_id': fields.many2one(
            'log.category', 'Category', required=True),
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
    
    # -------------------------------------------------------------------------
    # XMLRPC Procedure:
    # -------------------------------------------------------------------------
    def log_event(self, cr, uid, data, update_id=False, context=None):
        ''' ERPEEK procedure called for create event from remote scripts
            data dict contain:
                code_partner: Key field for reach partner, inserad use copmany
                code_activity: Key field for reach activity, instead create ERR
                start: datetime start
                end: datetime stop
                origin: note for origin server
                log: log text
                log_warning: warning text
                log_error: error text
        '''
        # Pool used:
        category_pool = self.pool.get('log.category')
        activity_pool = self.pool.get('log.activity')
        partner_pool = self.pool.get('res.partner')
        
        # Read key field:
        code_partner = data.get('code_partner', False) # default company
        code_activity = data.get('code_activity', False)

        # ---------------------------------------------------------------------
        # Search foreign keys:
        # ---------------------------------------------------------------------
        # partner_id    
        if code_partner:
            partner_ids = partner_pool.search(cr, uid, [
                ('log_code', '=', code_partner),
                ], context=context)
            if partner_ids:
                partner_id = partner_ids[0]    
            else:
                _logger.error('Code partner not present %s (take company)!' % (
                    code_partner))
                partner_id = 1 # Use default     
        else: 
            _logger.error('Code partner present (take company)!')
            partner_id = 1 # Use detault company address

        # activity_id
        if not code_activity:
            _logger.error('Code activity not present (take ERR)!')
            code_activity = 'ERR'

        activity_ids = activity_pool.search(cr, uid, [
            ('partner_id', '=', partner_id),
            ('code', '=', code_activity),
            ], context=context)
            
        if activity_ids:
            # Find:
            activity_id = activity_ids[0]    
        else:
            # Create new (to compile after on ODOO:
            # Get error category:
            category_ids = category_pool.search(cr, uid, [
                ('code', '=', code_activity), # use same code (cat.-act.)
                ], context=context)
            if category_ids:
                category_id = category_ids[0]    
            else:
                _logger.error('Code category not present (take ERR)!')
                category_id = category_pool.create(cr, uid, {
                    'code': code_activity,
                    'name': 'Error',
                    'note': 'Log error activity of the system (admin purpose)'
                    }, context=context)
            
            # Get activity:
            activity_id = activity_pool.create(cr, uid, {
                'code': code_activity,
                'name': 'Error',
                'partner_id': partner_id,
                'category_id': category_id,
                #'from_date': Fa,
                #'to_date': ,
                #'duration': ,
                #'active'
                #'monitor' 
                #'check_duration':
                #'duration_warning_range': 
                #'duration_error_range': 
                #'auto_duration': 
                #'email_alert': 
                #'email_error': 
                #'email_warning': 
                #'script': 
                #'origin': 
                #'note': 
                #'state': 
                }, context=context)
            _logger.error('Code activity not present %s create empty!' % (
                code_activity))

        # ---------------------------------------------------------------------
        # Create event:
        # ---------------------------------------------------------------------
        # Get data passed
        start = data.get('start', False)
        end = data.get('end', False)
        origin = data.get('origin', '')
        log_info = data.get('log_info', '')
        log_warning = data.get('log_warning', '')
        log_error = data.get('log_error', '')
        duration = 0 # TODO
        
        record = {
            #'datetime': now
            #'mark_ok': False,
            'activity_id': activity_id,
            'start': start,
            'end': end,
            'duration': duration,
            'origin': origin,
            'log_info': log_info,
            'log_warning': log_warning,
            'log_error': log_error,
            }
            
        if update_id:
            return self.write(cr, uid, update_id, record, context=context)
        else:
            return self.create(cr, uid, record, context=context)                
        
    _columns = {
        'datetime': fields.date('Date', required=True),
        'activity_id': fields.many2one(
            'log.activity', 'Activity'),
        'partner_id': fields.related(
            'activity_id', 'partner_id', 
            type='many2one', relation='res.partner', 
            string='Partner', store=True),    

        'start': fields.datetime('Start'),
        'end': fields.datetime('End'),
        'duration': fields.float(
            'Duration', digits=(16, 3), help='Duration of operation'),
            
        'origin': fields.text('Origin', help='Server info (log origin)'),
        
        'log_info': fields.text('Log info'),
        'log_warning': fields.text('Log warning'),
        'log_error': fields.text('Log error'),
        
        'mark_ok': fields.boolean('Mark as OK',
            help='For error / warning message'), 
        'state': fields.selection([
            ('started', 'Started'), # Start
            ('correct', 'Correct'), # End 
            ('warning', 'Warning'), # End with warning
            ('error', 'Error'), # End with error
            ], 'State', help='State info, not workflow management here'),
        }
    
    _defaults = {
        'datetime': lambda *a: datetime.now().strftime(
            DEFAULT_SERVER_DATETIME_FORMAT),
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
        'log_code': fields.char('Partner log code', size=64,
            help='Partner code for link activity'),
        'log_users_ids': fields.one2many(
            'res.users', 'log_partner_id', 'Log user'),
        'log_activity_ids': fields.one2many(
            'log.activity', 'partner_id', 'Log activity'),
    }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
