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
from openerp import SUPERUSER_ID#, api
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
        'is_active': fields.boolean('Is active'),
        'code': fields.char('Code', size=15),
        'name': fields.char('Category', size=64, required=True),
        'note': fields.text('Note'),
        }

class LogActivityMedia(orm.Model):
    """ Model name: Log media, manage all method for send log events
        (mail, sms, chat message etc)
        Every media will be add with a module
        Only mail is created here for default situation for logging
    """
    
    _name = 'log.activity.media'
    _description = 'Log media'
    _order = 'name'
    
    _columns = {
        'is_active': fields.boolean('Is active'),
        'name': fields.char('Media', size=64, required=True),
        'partner_id': fields.many2one(
            'res.partner', 'Partner', required=True),
        'address': fields.char('Address', size=64, 
            help='Sometimes is the reference of sender (mail, chat ref.)'),
        }
    _defaults = {
        'is_active': lambda *x: True,
        }    
    
class LogActivityHistory(orm.Model):
    """ Model name: Log event history
    """
    
    _name = 'log.activity.history'
    _description = 'Log activity history'
    _order = 'mode,create_date'
    _rec_name = 'mode'
    
    _columns = {
        'mode': fields.selection([
            ('cron', 'Cron job'),
            ('config', 'Config file'),
            ], 'Mode'),
        'activity_id': fields.many2one(
            'log.activity', 'Activity', 
            required=False),    
        'create_date': fields.datetime('History data'),
        'old': fields.text('Old value'),
        }
                    
class LogActivity(orm.Model):
    """ Model name: Log event
    """
    
    _name = 'log.activity'
    _description = 'Log activity'
    _order = 'name'
    
    def save_history_mode(self, cr, uid, ids, vals, context=None):
        ''' History before insert data value in particular fields
        '''
        history_pool = self.pool.get('log.activity.history')
        
        fields = ['cron', 'config']
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        for field in fields:
            if field in vals:
                # If field is different:
                old_value = current_proxy.__getattr__(field)
                if vals[field] != old_value:
                    # History operation:
                    history_pool.create(cr, uid, {
                        'activity_id': current_proxy.id,
                        'mode': field,
                        'old': old_value,
                        }, context=context)
                else: # if same not update:                       
                    del(vals[mode])
        return True                        

    def write(self, cr, uid, ids, vals, context=None):
        """ Update redord(s) comes in {ids}, with new value comes as {vals}
            return True on success, False otherwise
            @param cr: cursor to database
            @param uid: id of current user
            @param ids: list of record ids to be update
            @param vals: dict of new values to be set
            @param context: context arguments, like lang, time zone
            
            @return: True on success, False otherwise
            
            Note: only updated the next change of monitored values
        """    
        import pdb; pdb.set_trace()
        # Put in history cron or config value:    
        self.save_history_mode(cr, uid, ids, vals, context=context)

        return super(LogActivity, self).write(
            cr, uid, ids, vals, context=context)
        
    _columns = {
        'is_active': fields.boolean('Is active'),
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
        
        # Info about server:
        'cron': fields.text('Cron job'),
        'config': fields.text('Config file'),
        
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
        'is_active': lambda *x: True,
        'state': lambda *x: 'active',
        }

class LogActivityEvent(orm.Model):
    """ Model name: LogActivityEvent
    """
    
    _name = 'log.activity.event'
    _description = 'Event'
    _rec_name = 'datetime'
    _order = 'datetime desc'
    
    def get_duration_hour(self, start, end):
        ''' Diference from 2 date in hours
        '''
        if not start or not end:
            return 0.0
            
        start = datetime.strptime(
            start, DEFAULT_SERVER_DATETIME_FORMAT)
        end = datetime.strptime(
            end, DEFAULT_SERVER_DATETIME_FORMAT)
        gap = end - start
        return (gap.days * 24) + (gap.seconds / 3660)

    # -------------------------------------------------------------------------
    # Schedule procedure:
    # -------------------------------------------------------------------------
    def scheduled_log_activity_check_activity_duration(
            self, cr, uid, context=None):
        ''' Check activity for mark and validate:
            1. check if started are in duration range (if needed)
            2. check if closed are in duration range else mark as OK
        '''
        # Read started / closed (check duration activity)
        _logger.info('Start check activity duration')
        event_ids = self.search(cr, uid, [
            ('state', 'in', ('started', 'closed')),
            ('activity_id.check_duration', '=', True),
            ('mark_ok', '=', False),
            ], context=context) 
        now = datetime.now()  

        i = 0
        for event in self.browse(cr, uid, event_ids, context=context):
            # Read parameters:
            duration = event.activity_id.duration * 60.0 # min
            warning_range = event.activity_id.duration_warning_range # %
            error_range = event.activity_id.duration_error_range # %
            
            # Calculate parameters:
            warning_duration = duration * (100.0 + warning_range) / 100.0 # min
            error_duration = duration * (100.0 + error_range) / 100.0 # min
            start = datetime.strptime(
                event.start, DEFAULT_SERVER_DATETIME_FORMAT)
            if event.state == 'started':
                stop = now
            else: # closed  
                stop = datetime.strptime(
                    event.end, DEFAULT_SERVER_DATETIME_FORMAT)
            
            gap = stop - start
            gap_min = (gap.days * 24 * 60) + (gap.seconds / 60) # min
            
            # Check range:
            if gap_min > error_duration:
                i += 1
                self.write(cr, uid, event.id, {
                    'error_comment': _('Over max duration') \
                        if event.state == 'closed' \
                        else _('Started but not closed'),
                    'state': 'error',
                    }, context=context)
            elif event.state == 'closed' and gap_min > warning_duration:
                self.write(cr, uid, event.id, {
                    'error_comment': _('Duration in warning period'),
                    'state': 'warning',
                    }, context=context)
            elif event.state == 'closed': # correct range
                self.write(cr, uid, event.id, {
                    'mark_ok': True,
                    }, context=context)
        
        # Read closed (no check duration activity)
        _logger.info('Mark ok closed record without check duration')
        event_ids = self.search(cr, uid, [
            ('state', '=', 'closed'),
            ('activity_id.check_duration', '=', False),
            ('mark_ok', '=', False),
            ], context=context) 
        self.write(cr, uid, event_ids, {
            'mark_ok': True,
            }, context=context)
        _logger.info(
            'Mark ok closed record without check duration, tot.: %s' % (
                len(event_ids)))

        _logger.info('End check activity duration (error: %s)' % i)
        return True

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
        _logger.info('Register data event: [ID %s] %s' % (
            update_id,
            data, 
            ))

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
            # Create new (to compile after on ODOO):
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
                #'is_active'
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
        duration = self.get_duration_hour(start, end)

        if not end:
            state = 'started'
        elif log_error:
            state = 'error'
        elif log_warning:
            state = 'warning'
        else:
            state = 'closed'
            
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
            'state': state,
            }
            
        if update_id:
            return (
                self.write(cr, uid, update_id, record, context=context),
                record,
                )
        else:
            return (
                self.create(cr, uid, record, context=context),
                record,
                )
        
    _columns = {
        'datetime': fields.datetime('Date', required=True),
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
        'error_comment': fields.char('Error comment', size=80, readonly=True),
        
        'mark_ok': fields.boolean('Mark as OK',
            help='Scheduled masked as OK or manually with button'), 
        'state': fields.selection([
            ('started', 'Started'), # Start (new event)
            ('closed', 'Closed'), # End (closed from activity with end time)
            ('warning', 'Warning'), # End with warning (scheduled check)
            ('error', 'Error'), # End with error (scheduled check)
            ], 'State', help='State info, not workflow management here'),
        }
    
    _defaults = {
        'datetime': lambda *a: datetime.now().strftime(
            DEFAULT_SERVER_DATETIME_FORMAT),
        'state': lambda *x: 'started',
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
        'log_media_ids': fields.one2many(
            'log.activity.media', 'partner_id', 'Log media'),
    }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
