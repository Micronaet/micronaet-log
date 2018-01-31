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
            ('server', 'Server info'),
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
    
    # -------------------------------------------------------------------------
    # REPORT XLSX:
    # -------------------------------------------------------------------------
    def extract_xlsx_scheduled_status(self, cr, uid, ids, context=None):
        ''' Generate report for current activity, scheduled from date to check
            Usually generate report from check_from parameter to now, 
            if from_date and to_date context is present select this period
        '''
        # Pool used:
        event_pool = self.pool.get('log.activity.event') 
        excel_pool = self.pool.get('excel.writer')
        
        # ---------------------------------------------------------------------
        # Parameter and setup:
        # ---------------------------------------------------------------------
        # TODO
        if context is None:
            context = {}
        context_from_date = context.get('from_date', False)    
        context_to_date = context.get('to_date', False)    

        res = {}
        now = datetime.now()
        now_60 = now - timedelta(days=60)
        to_date = '%s 23:59:59' % now.strftime(DEFAULT_SERVER_DATE_FORMAT)
        min_date = '%s 00:00:00' % now_60.strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        # Excel reference range:
        start_xls = to_date
        end_xls = to_date

        # ---------------------------------------------------------------------
        # Collect data:
        # ---------------------------------------------------------------------
        # Scheduled info data:
        for activity in self.browse(cr, uid, ids, context=context):
            if activity.check_from:
                from_date = '%s 00:00:00' % activity.check_from
            else:    
                from_date = min_date # lower limit 60 gg.
            event_ids = event_pool.search(cr, uid, [
                ('activity_id', '=', activity.id),                
                # Start Period:
                ('start', '>=', from_date),
                ('start', '<=', to_date),
                ], context=context)
            res[activity] = {}
            for event in event_pool.browse(
                    cr, uid, event_ids, context=context):
                date = event.start[:10]

                if date < start_xls: # save min date:
                    start_xls = date 
                if date not in res[activity]:
                    res[activity][date] = [
                        0, # Closed
                        0, # Started, Warning
                        0, # Error (Missed)
                        ]
                        
                if event.state in ('closed', ):
                    res[activity][date][0] += 1
                elif event.state in ('started', 'warning'):
                    res[activity][date][1] += 1
                else: # 'error', missed'
                    res[activity][date][2] += 1
        
        # Header data:
        start_xls_dt = datetime.strptime(
            start_xls[:10], DEFAULT_SERVER_DATE_FORMAT)
        end_xls_dt = datetime.strptime(
            end_xls[:10], DEFAULT_SERVER_DATE_FORMAT)
        header = [u'Attività', u'Cliente', ] 
        dow_header = ['', '', ]
        dow_header_text = ['', '', ]
        iso_text = {
            0: 'Dom', # not needed
            1: 'Lun',
            2: 'Mar',
            3: 'Mer',
            4: 'Gio',
            5: 'Ven',
            6: 'Sab',
            7: 'Dom',
            }
        while start_xls_dt <= end_xls_dt:
            header.append(start_xls_dt.strftime(DEFAULT_SERVER_DATE_FORMAT))
            dow_header.append(start_xls_dt.isoweekday())
            dow_header_text.append(
                iso_text.get(start_xls_dt.isoweekday(), '?'))
            start_xls_dt += timedelta(days=1)            
        
        # Create mapping database for position:    
        col_pos = {}
        for pos, value in enumerate(header):
            col_pos[value] = pos
        
        # ---------------------------------------------------------------------
        # EXCEL:
        # ---------------------------------------------------------------------
        # Create worksheet:
        WS_name = u'Schedulazioni'
        excel_pool.create_worksheet(WS_name)
        excel_pool.set_format()

        # Write header:    
        excel_pool.write_xls_line(WS_name, 0, header)
        excel_pool.write_xls_line(WS_name, 1, dow_header_text)

        # Write data:
        row = 1
        for activity in sorted(res):
            
            # Week list for backup total scheduled (from cron)
            activity_id = activity.id
            daily_backup = self.get_cron_info(
                cr, uid, [activity_id], context=context)[activity_id]
                
            row += 1
            excel_pool.write_xls_data(WS_name, row, 0, activity.name)
            excel_pool.write_xls_data(
                WS_name, row, 1, activity.partner_id.name)
            
            all_xls_day = range(2, len(header)) # check missed days    
            for day in res[activity]:
                col = col_pos.get(day, False)
                dow = dow_header[col] # read DOW from header
                if col in all_xls_day:
                    all_xls_day.remove(col)
                
                total_today = daily_backup[dow]
                total_ok, total_warn, total_ko = res[activity][day]
                
                # Check OK status:
                if total_today <= total_ok: # GREEN
                    excel_pool.write_xls_data(WS_name, row, col, 
                        '[OK %s/%s]' % (total_ok, total_today))
                elif total_warn > 0: # YELLOW
                    excel_pool.write_xls_data(WS_name, row, col, 
                        '[WARN %s/%s]' % (total_warn, total_today))
                elif total_ko > 0: # RED
                    excel_pool.write_xls_data(WS_name, row, col, 
                        '[KO %s/%s]' % (total_warn, total_today))
                # else TODO format with color and check all status if correct        
                    
            for col in all_xls_day: # column check if missed:        
                dow = dow_header[col] # read DOW from header                
                if daily_backup[dow] > 0: # Backup needed!!!                    
                    excel_pool.write_xls_data(WS_name, row, col, 'SALTATO')

        # Return XLSX file generated
        return excel_pool.return_attachment(cr, uid, 
            'Schedulazioni %s' % to_date, 
            'scheduler_check_%s.xlsx' % to_date,
            version='7.0',
            context=context)
        
    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def get_cron_info(self, cr, uid, ids, context=None):
        ''' Try to get cron info about activity code scheduled for get 
            information about running period
            Used as information but also for check daily backup operations
            parameter: browse_keys for setup key of returned dict
        '''
        if context is None:
            context = {}
        browse_keys = context.get('browse_keys', False)        
        
        res = {}
        for activity in self.browse(cr, uid, ids, context=context):        
            code = activity.code
            if browse_keys:
               key = activity
            else:
               key = activity.id
            res[key] = [0, 0, 0, 0, 0, 0, 0, 0] # 0 to 7
            
            cron_file = (activity.cron or '')            
            if not cron_file:
                continue

            for line in cron_file.split('\n'):
                line = line.strip()
                if line.startswith('#'):                  
                    continue # is a comment
                if code in line:
                    line = line.replace('\t', ' ')
                    line_block = line.split()
                    if len(line_block) < 6:
                        _logger.error('Cron activity not correct: %s' % line)
                        continue
                        
                    day = line_block[4]
                    if day == '*': # All day new run
                        for i in range(0, 7):
                            res[key][i] += 1
                    elif '-' in day: # range block
                        range_block = day.split('-')
                        if len(range_block) != 2:
                            _logger.error('Range not correct: %s' % day)
                            continue                           
                        for i in range(
                                int(range_block[0]), 
                                int(range_block[1]) + 1):
                            res[key][i] += 1
                    elif ',' in day: # multi days
                        for i in day.split(','):
                            i = int(i)
                            res[key][i] += 1                            
                    elif day in '01234567': # direct day
                        res[key][int(day)] += 1

            # Sum time for 7 in 0:         
            res[key][0] += res[key][7]
        return res
        
    # -------------------------------------------------------------------------
    # Scheduled events:
    # -------------------------------------------------------------------------
    def check_event_not_started(self, cr, uid, context=None):
        ''' Check scheduled started from today - period and yestertay
            Check 7 day for defaults
        '''
        # ---------------------------------------------------------------------
        # Utility:
        # ---------------------------------------------------------------------
        def get_cron_dow(dow):
            ''' Convert datetime dow number in cron dow number
                Cron: su = 0 (or 7) 
                Datetime: mo = 0
            '''
            if dow == 6:
                return 0
            else:
                return dow +1        
            
        def create_missed_event(self, cr, uid, start, activity, 
                context=context):
            ''' Create a standard event for missed operation:
            '''    
            event_pool = self.pool.get('log.activity.event')
            return event_pool.create(cr, uid, {
                'start': start,
                'datetime': start,                
                'activity_id': activity.id,
                'partner_id': activity.partner_id.id,
                'end': start, # same
                'duration': False,
                'origin': _('Automatic system check'),
                'log_info': '',
                'log_warning': '',
                'log_error': _('Event not reached'),
                'state': 'missed',            
                }, context=context)
        
        _logger.info('Start check missed events')
        if context is None:
            context = {}
            
        # Pool used:    
        event_pool = self.pool.get('log.activity.event')
        
        # From start of day (-7)
        now = datetime.now()
        from_date = now - timedelta(days=7)
        from_date = '%s 00:00:00' % from_date.strftime(
            DEFAULT_SERVER_DATE_FORMAT)

        # To end of previous day (-1)
        to_date_dt = now - timedelta(days=1) # yesterday
        to_date = '%s 23:59:59' % to_date_dt.strftime(
            DEFAULT_SERVER_DATE_FORMAT) # Yesterday
                
        # ---------------------------------------------------------------------
        # Current activity:
        # ---------------------------------------------------------------------
        activity_ids = self.search(cr, uid, [
            ('is_active', '=', True), 
            # TODO  monitor check?
            ], context=context)
        # TODO better for start stop period!    

        event_ids = event_pool.search(cr, uid, [
           ('start', '>=', from_date),
           ('start', '<=', to_date),
           ], context=context)
        
        # Read as cron schedule for week (key = browse)
        context['browse_keys'] = True
        activity_cron = self.get_cron_info(
            cr, uid, activity_ids, context=context)
        context['browse_keys'] = False

        # Create DOW database with this passed week days
        dows = {}
        one_day = timedelta(days=1)
        current = to_date_dt
        for i in range(0, 7):
            dows[current.weekday()] = current
            current -= one_day

        # Generate real database (activity - dow)    
        activity_db = {} # event database system        
        for event in event_pool.browse(cr, uid, event_ids, context=context):
            activity = event.activity_id
            if activity not in activity_cron:
                _logger.error('Activity not monitored, jumped!') # TODO log???
                continue
                
            if activity not in activity_db: # Default week for total recurrency
                activity_db[activity] = dict.fromkeys(range(0, 7), 0)
                
            start = datetime.strptime(
                event.datetime, DEFAULT_SERVER_DATETIME_FORMAT)
            dow = get_cron_dow(start.weekday())
            activity_db[activity][dow] += 1

        # ---------------------------------------------------------------------
        # Compare data:
        # ---------------------------------------------------------------------  
        for activity, planned in activity_cron.iteritems():
            i = -1
            for tot_planned in planned[:-1]: # check every day (last not used):
                i += 1 # start from 0
                # not present or less recursion:
                if activity not in activity_db or \
                        tot_planned > activity_db[activity][i]: 
                    create_missed_event(
                        self, cr, uid, dows[i], activity, context=context)
                    continue
                # TODO log extra backup event?    
        _logger.info('End check missed events')
        return True
        
    # -------------------------------------------------------------------------
    # Button:
    # -------------------------------------------------------------------------    
    def open_history_cron(self, cr, uid, ids, mode, context=None):
        ''' Open cron history
        '''    
        return self.open_history(cr, uid, ids, mode='cron', context=context)
    
    def open_history_config(self, cr, uid, ids, mode, context=None):
        ''' Open config history
        '''    
        return self.open_history(cr, uid, ids, mode='config', context=context)

    def open_history_server(self, cr, uid, ids, mode, context=None):
        ''' Open server history
        '''    
        return self.open_history(cr, uid, ids, mode='server', context=context)
           
    def open_history(self, cr, uid, ids, mode, context=None):
        ''' Search config elements for mode type
        '''
        return {
            'type': 'ir.actions.act_window',
            'name': _('Activity story %s' % mode),
            'view_type': 'form',
            'view_mode': 'tree,form',
            #'res_id': 1,
            'res_model': 'log.activity.history',
            #'view_id': view_id, # False
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [
                ('activity_id', '=', ids[0]),
                ('mode', '=', mode),
                ],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }
            
    def save_history_mode(self, cr, uid, ids, vals, context=None):
        ''' History before insert data value in particular fields
        '''
        history_pool = self.pool.get('log.activity.history')
        
        fields = ['cron', 'config', 'server']
        if type(ids) in (list, tuple):
            ids = ids[0]
        current_proxy = self.browse(cr, uid, ids, context=context)
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
                    del(vals[field])
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
        # Put in history cron or config value:    
        self.save_history_mode(cr, uid, ids, vals, context=context)

        return super(LogActivity, self).write(
            cr, uid, ids, vals, context=context)

    # -------------------------------------------------------------------------
    # Fields function:
    # -------------------------------------------------------------------------
    def _get_cron_daily_execution(self, cr, uid, ids, fields, args, 
            context=None):
        ''' Fields function for calculate 
        '''
        res = {}

        daily = self.get_cron_info(cr, uid, ids, context=context)  
        for item_id, item in daily.iteritems():                    
            res[item_id] = _('''
                <style>
                    .table_bf {
                         border:1px 
                         padding: 3px;
                         solid black;
                     }
                    .table_bf td {
                         border:1px 
                         solid black;
                         padding: 10px;
                         text-align: center;
                     }
                    .table_bf th {
                         border:1px 
                         solid black;
                         padding: 10px;
                         text-align: center;
                         background-color: grey;
                         color: white;
                     }
                </style>
                <table class='table_bf'>
                    <tr>
                        <th>Su</th><th>Mo</th><th>Tu</th><th>We</th><th>Th</th>
                        <th>Fr</th><th>Sa</th>
                    </tr>                    
                    <tr>
                        <td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>
                        <td>%s</td><td>%s</td><!--%s-->
                    </tr>
                </table>    
                ''') % tuple(item)
        return res
        
    def _log_in_html_format(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = '<p>'
            if not item.log_check_unwrited:
                res[item.id] = False
                
            for row in item.log_check_unwrited.split('\n'):
                res_ids = row.split('|')
                try:
                    res[item.id] += '<b>%s: </b> <i>%s</i> %s<br/>' % res_ids
                except:
                    res[item.id] += '%s<br/>' % row 
            res[item.id] += '</p>'
        return res        
                          
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
        'check_from': fields.date('Check from', 
            help='Check log presence from this date, used for mark as read'),
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
        'server': fields.text('Server info'),
        
        'cron_daily_exec': fields.function(
            _get_cron_daily_execution, method=True, 
            type='text', string='Cron execution', 
            store=False), 
        
        'note': fields.text('Note'),
        
        # Log mode:
        'log_mode': fields.selection([
            ('all', 'All (info, warning, error always present)'),
            ('check', 'Check (error and warning always, info every X time')
            ], 'Log mode', required=True,
            ),
        'log_check_every': fields.integer('Log check every', 
            help='When log mode is check raise a message every X times'),
        'log_check_count': fields.integer('Log check now is', 
            help='Total message received till now'),
        'log_check_unwrited': fields.text(
            'Log check unwrited', 
            help='When log mode is check write here the event'),    
        'log_check_unwrited_html': fields.function(
            _log_in_html_format, method=True, 
            type='text', string='Log in HTML format', store=False), 
                        
        'state': fields.selection([
            ('unactive', 'Unactive'), # not working
            ('active', 'Active'), # Working
            ('pause', 'Pause'), # Currently not work butt soon yes
            ('timed', 'Out of time'), # Out of date period            
            ], 'State',
            ),
        }
    
    _defaults = {
        # Default value for state:
        'is_active': lambda *x: True,
        'check_duration': lambda *x: True,
        'log_mode': lambda *x: 'all',
        'state': lambda *x: 'active',
        }

class LogActivityEvent(orm.Model):
    """ Model name: LogActivityEvent
    """
    
    _name = 'log.activity.event'
    _description = 'Event'
    _rec_name = 'datetime'
    _order = 'datetime desc'
    
    def dummy_nothing(self, cr, uid, ids, context=None):
        ''' Dummy button do nothing
        '''
        return True

    def mark_ok_button(self, cr, uid, ids, context=None):
        ''' Mark as OK
        '''
        return self.write(cr, uid, ids, {
            'mark_ok': True,
            }, context=context)

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
                ('code', '=', 'BAK'), # use same code (cat.-act.)
                ], context=context)
            if category_ids:
                category_id = category_ids[0]    
            else:
                _logger.error('Code category not present (create BAK)!')
                category_id = category_pool.create(cr, uid, {
                    'code': 'BAK',
                    'name': 'Backup',
                    'note': 'Log activity for Backup (automatic creation)'
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

        # ---------------------------------------------------------------------
        # Read activity for get log information
        # ---------------------------------------------------------------------
        # If activity don't need log event wil be jumped the notification:
        activity_proxy = activity_pool.browse(
            cr, uid, activity_id, context=context)

        # Jump notification in check mode if not error and warning    
        if activity_proxy.log_mode == 'check' and not log_warning and \
                not log_error:
            # jump in no count info raise:    
            count_current = activity_proxy.log_check_count + 1
            count_max =  activity_proxy.log_check_every
            log_check_unwrited = activity_proxy.log_check_unwrited or ''
            if count_current < count_max:
                # Update count and log partial:
                _logger.info('No notification event received')
                activity_pool.write(cr, uid, activity_id, {
                    'log_info': log_info, # used for IP address
                    'log_check_count': count_current,
                    'log_check_unwrited': '%s|%s|%s\n' % (
                        datetime.now(), 
                        log_info,
                        log_check_unwrited,
                        )
                    }, context=context)                    
                return (True, {}) # nothing to comunicate
            else: # Reset and notificate
                _logger.info('No notification event received, now notificate!')
                activity_pool.write(cr, uid, activity_id, {
                    'log_check_count': 0,
                    'log_check_unwrited': '',
                    }, context=context)                    
            
        record = {
            #'datetime': now
            'mark_ok': False,
            'activity_id': activity_id,
            'start': start,
            'end': end,
            'duration': duration,
            'origin': origin,
            'log_info': log_info,
            'log_warning': log_warning,
            'log_error': log_error,
            }

        # Normal log procedure:
        if not end:
            record['state'] = 'started'
        elif log_error:
            record['state'] = 'error'
        elif log_warning:
            record['state'] = 'warning'
        else:
            record['state'] = 'closed'
            record['mark_ok'] = True            
            
        if update_id:
            try:
                res = self.write(cr, uid, update_id, record, context=context)
            except:
                _logger.error('Error updating event: %s' % update_id)
                res = False                    
            return (res, record)
        else:
            try:
                res = self.create(cr, uid, record, context=context)
            except:
                _logger.error('Error create event')
                res = False    
            return (res, record)
        
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
        'error_comment': fields.char('Error comment', size=180),
       
        'mark_ok': fields.boolean('Mark as OK',
            help='Scheduled masked as OK or manually with button'), 
        'mark_ok_comment': fields.text('Mark as OK comment'),
        
        'state': fields.selection([
            ('started', 'Started'), # Start (new event)
            ('closed', 'Closed'), # End (closed from activity with end time)
            ('missed', 'Missed'), # Missed
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
