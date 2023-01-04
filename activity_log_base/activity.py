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
import pdb
import sys
import odoo
import logging
from odoo import models, fields, api
from odoo.tools.translate import _
from datetime import timedelta # XXX to be removed?

_logger = logging.getLogger(__name__)


class LogCategory(models.Model):
    """ Model name: Log Category
    """
    _name = 'log.category'
    _description = 'Log category'
    _order = 'name'

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    name =  fields.Char('Category', size=64, required=True)
    is_active = fields.Boolean('Is active')
    code = fields.Char('Code', size=15)
    note = fields.Text('Note')

class LogActivityMedia(models.Model):
    """ Model name: Log media, manage all method for send log events
        (mail, sms, chat message etc)
        Every media will be add with a module
        Only mail is created here for default situation for logging
    """

    _name = 'log.activity.media'
    _description = 'Log media'
    _order = 'name'

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    is_active = fields.Boolean('Is active', default=True)
    name = fields.Char('Media', size=64, required=True)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    address = fields.Char('Address', size=64,
        help='Sometimes is the reference of sender (mail, chat ref.)')

class LogActivityHistory(models.Model):
    """ Model name: Log event history
    """

    _name = 'log.activity.history'
    _description = 'Log activity history'
    _order = 'mode,create_date'
    _rec_name = 'mode'

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    mode = fields.Selection([
        ('cron', 'Cron job'),
        ('config', 'Config file'),
        ('server', 'Server info'),
        ], 'Mode')
    activity_id = fields.Many2one('log.activity', 'Activity')
    create_date = fields.Datetime('History data')
    old = fields.Text('Old value')

class LogActivity(models.Model):
    """ Model name: Log event
    """

    _name = 'log.activity'
    _description = 'Log activity'
    _order = 'name'

    # -------------------------------------------------------------------------
    # Overridable event:
    # -------------------------------------------------------------------------
    @api.model
    def raise_extra_media_comunication(self, activity_id, event_id):
        """ Override procedure for raise extra event like:
            Mail, SMS, Telegram Message, Whatsapp message etc.
            All override procedure will be introduced by a new module
        """
        # Do Nothing
        _logger.warning('Log media event comunication')
        return True

    # -------------------------------------------------------------------------
    # REPORT XLSX:
    # -------------------------------------------------------------------------
    @api.model
    def extract_xlsx_scheduled_status(self, ids):
        """ Generate report for current activity, scheduled from date to check
            Usually generate report from check_from parameter to now,
            if from_date and to_date context is present select this period
        """
        # Pool used:
        event_pool = self.env['log.activity.event']
        excel_pool = self.env['excel.writer']

        # ---------------------------------------------------------------------
        # Parameter and setup:
        # ---------------------------------------------------------------------
        # todo
        context_from_date = self.env.context.get('from_date', False)
        context_to_date = self.env.context.get('to_date', False)

        res = {}
        now = fields.Datetime.from_string(fields.Datetime.now())
        now_60 = now - timedelta(days=60)
        to_date = '%s 23:59:59' % fields.Date.to_string(now)
        min_date = '%s 00:00:00' % fields.Date.to_string(now_60)

        # Excel reference range:
        start_xls = to_date
        end_xls = to_date

        # ---------------------------------------------------------------------
        # Collect data:
        # ---------------------------------------------------------------------
        # Scheduled info data:
        for activity in self.browse(ids):
            if activity.check_from:
                from_date = '%s 00:00:00' % activity.check_from
            else:
                from_date = min_date  # lower limit 60 gg.
            events = event_pool.search([
                ('activity_id', '=', activity.id),
                # Start Period:
                ('start', '>=', from_date),
                ('start', '<=', to_date),
                ])
            res[activity] = {}
            for event in events:
                date = event.start[:10]

                if date < start_xls:  # save min date:
                    start_xls = date
                if date not in res[activity]:
                    res[activity][date] = [
                        0,  # Closed
                        0,  # Started, Warning
                        0,  # Error (Missed)
                        ]

                if event.state in ('closed', ):
                    res[activity][date][0] += 1
                elif event.state in ('started', 'warning'):
                    res[activity][date][1] += 1
                else: # 'error', missed'
                    res[activity][date][2] += 1

        # Header data:
        start_xls_dt = fields.Date.from_string(start_xls)  # XXX date
        end_xls_dt = fields.Date.from_string(end_xls)  # XXX date [:10]
        header = [u'Attività', u'Cliente', ]
        dow_header = ['', '', ]
        dow_header_text = ['', '', ]
        iso_text = {
            0: 'Dom',  # not needed
            1: 'Lun',
            2: 'Mar',
            3: 'Mer',
            4: 'Gio',
            5: 'Ven',
            6: 'Sab',
            7: 'Dom',
            }
        while start_xls_dt <= end_xls_dt:
            header.append(fields.Date.to_string(start_xls_dt))
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
        ws_name = u'Schedulazioni'
        excel_pool.create_worksheet(ws_name)
        excel_pool.set_format()

        # Write header:
        excel_pool.write_xls_line(ws_name, 0, header)
        excel_pool.write_xls_line(ws_name, 1, dow_header_text)

        # Write data:
        row = 1
        for activity in sorted(res):

            # Week list for backup total scheduled (from cron)
            daily_backup = activity.get_cron_info()

            row += 1
            excel_pool.write_xls_data(ws_name, row, 0, activity.name)
            excel_pool.write_xls_data(
                ws_name, row, 1, activity.partner_id.name)

            all_xls_day = range(2, len(header))  # check missed days
            for day in res[activity]:
                col = col_pos.get(day, False)
                dow = dow_header[col]  # read DOW from header
                if col in all_xls_day:
                    pdb.set_trace()
                    all_xls_day.remove(col)

                total_today = daily_backup[dow]
                total_ok, total_warn, total_ko = res[activity][day]

                # Check OK status:
                if total_today <= total_ok:  # GREEN
                    excel_pool.write_xls_data(
                        ws_name, row, col,
                        '[OK %s/%s]' % (total_ok, total_today))
                elif total_warn > 0:  # YELLOW
                    excel_pool.write_xls_data(
                        ws_name, row, col,
                        '[WARN %s/%s]' % (total_warn, total_today))
                elif total_ko > 0:  # RED
                    excel_pool.write_xls_data(
                        ws_name, row, col,
                        '[KO %s/%s]' % (total_warn, total_today))
                # else TODO format with color and check all status if correct

            for col in all_xls_day:  # column check if missed:
                dow = dow_header[col]  # read DOW from header
                if daily_backup[dow] > 0:  # Backup needed!!!
                    excel_pool.write_xls_data(ws_name, row, col, 'SALTATO')

        # Return XLSX file generated
        return excel_pool.return_attachment(
            u'Schedulazioni %s' % to_date,
            u'scheduler_check_%s.xlsx' % to_date,
            )

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    @api.multi
    def get_cron_info(self):
        """ Try to get cron info about activity code scheduled for get
            information about running period
            Used as information but also for check daily backup operations
            parameter: browse_keys for setup key of returned dict
        """
        browse_keys = self.env.context.get('browse_keys', False)

        res = {}
        for activity in self:
            code = activity.code
            if browse_keys:
                key = activity
            else:
                key = activity.id
            res[key] = [0, 0, 0, 0, 0, 0, 0, 0]  # 0 to 7

            cron_file = (activity.cron or '')
            if not cron_file:
                continue

            for line in cron_file.split('\n'):
                line = line.strip()
                if line.startswith('#'):
                    continue  # is a comment
                if code in line:
                    line = line.replace('\t', ' ')
                    line_block = line.split()
                    if len(line_block) < 6:
                        _logger.error('Cron activity not correct: %s' % line)
                        continue

                    day = line_block[4]
                    if day == '*':  # All day new run
                        for i in range(0, 7):
                            res[key][i] += 1
                    elif '-' in day:  # range block
                        range_block = day.split('-')
                        if len(range_block) != 2:
                            _logger.error('Range not correct: %s' % day)
                            continue
                        for i in range(
                                int(range_block[0]),
                                int(range_block[1]) + 1):
                            res[key][i] += 1
                    elif ',' in day:  # multi days
                        for i in day.split(','):
                            i = int(i)
                            res[key][i] += 1
                    elif day in '01234567':  # direct day
                        res[key][int(day)] += 1

            # Sum time for 7 in 0:
            res[key][0] += res[key][7]
        return res

    # -------------------------------------------------------------------------
    # Scheduled events:
    # -------------------------------------------------------------------------
    @api.model
    def schedule_update_all(self):
        """ Update event scheduling update of field store
        """
        activities = self.search([])
        _logger.warning('Update %s activity event last' % len(activities))

        # Double update (if some record is not True):
        activities.write({
            'update_event_status': False,
            })
        activities.write({
            'update_event_status': True,
            })

    @api.model
    def check_event_not_started(self):
        """ Check scheduled started from today - period and yestertay
            Check 7 day for defaults
        """
        # ---------------------------------------------------------------------
        # Utility:
        # ---------------------------------------------------------------------
        def get_cron_dow(dow):
            """ Convert datetime dow number in cron dow number
                Cron: su = 0 (or 7)
                Datetime: mo = 0
            """
            if dow == 6:
                return 0
            else:
                return dow + 1

        def create_missed_event(event_pool, start, activity):
            """ Create a standard event for missed operation:
            """
            return event_pool.create({
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
                })

        _logger.info('Start check missed events')

        # Pool used:
        event_pool = self.env['log.activity.event']

        # From start of day (-7)
        now = fields.Datetime.from_string(fields.Datetime.now())
        from_date = now - timedelta(days=7)
        from_date = '%s 00:00:00' % fields.Date.to_string(from_date)

        # To end of previous day (-1)
        to_date_dt = now - timedelta(days=1)  # yesterday
        to_date = '%s 23:59:59' % fields.Date.to_string(to_date_dt)

        # ---------------------------------------------------------------------
        # Current activity:
        # ---------------------------------------------------------------------
        activities = self.search([
            ('is_active', '=', True),
            # todo  monitor check?
            ])
        # TODO better for start stop period!

        events = event_pool.search([
           ('start', '>=', from_date),
           ('start', '<=', to_date),
           ])

        # Read as cron schedule for week (key = browse)
        # self.env.context['browse_keys'] = True  # TODO change context method
        activities_context = activities.with_context(browse_keys=True)
        activity_cron = activities_context.get_cron_info()
        # self.env.context['browse_keys'] = False

        # Create DOW database with this passed week days
        dows = {}
        one_day = timedelta(days=1)
        current = to_date_dt
        for i in range(0, 7):
            dows[current.weekday()] = current
            current -= one_day

        # Generate real database (activity - dow)
        activity_db = {}  # event database system
        for event in events:
            activity = event.activity_id
            if activity not in activity_cron:
                _logger.error('Activity not monitored, jumped!')  # TODO log???
                continue

            if activity not in activity_db: # Default week for total recurrence
                activity_db[activity] = dict.fromkeys(range(0, 7), 0)

            start = fields.Datetime.from_string(event.datetime)
            dow = get_cron_dow(start.weekday())
            activity_db[activity][dow] += 1

        # ---------------------------------------------------------------------
        # Compare data:
        # ---------------------------------------------------------------------
        for activity in activity_cron:
            planned = activity_cron[activity]
            i = -1
            for tot_planned in planned[:-1]:  # check every day (last not used)
                i += 1  # start from 0
                # not present or less recursion:
                if activity not in activity_db or \
                        tot_planned > activity_db[activity][i]:
                    create_missed_event(
                        event_pool, dows[i], activity)
                    continue
                # todo log extra backup event?
        _logger.info('End check missed events')
        return True

    # -------------------------------------------------------------------------
    # Button:
    # -------------------------------------------------------------------------
    @api.multi
    def open_history_cron(self):
        """ Open cron history
        """
        context_extra = self.with_context(history_mode='cron')
        return context_extra.open_history()

    @api.multi
    def open_history_config(self):
        """ Open config history
        """
        context_extra = self.with_context(history_mode='config')
        return context_extra.open_history()

    @api.multi
    def open_history_server(self):
        """ Open server history
        """
        context_extra = self.with_context(history_mode='server')
        return context_extra.open_history()

    @api.model
    def open_history(self):
        """ Search config elements for mode type
        """
        ids = [item.id for item in self]
        mode = self.env.context.get('history_mode', 'cron')

        return {
            'type': 'ir.actions.act_window',
            'name': _('Activity story %s' % mode),
            'view_type': 'form',
            'view_mode': 'tree,form',
            # 'res_id': 1,
            'res_model': 'log.activity.history',
            # 'view_id': view_id, # False
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [
                ('activity_id', '=', ids[0]),
                ('mode', '=', mode),
                ],
            'context': self.env.context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    @api.multi
    def save_history_mode(self, vals):
        """ History before insert data value in particular fields
        """
        # self.ensure_one()
        activity = self[0]

        history_pool = self.env['log.activity.history']
        fields = ['cron', 'config', 'server']
        for field in fields:
            if field in vals:  # XXX all record to write
                # If field is different:
                old_value = activity.__getattribute__(field)
                if vals[field] != old_value:
                    # History operation:
                    history_pool.create({
                        'activity_id': activity.id,
                        'mode': field,
                        'old': old_value,
                        })
                else: # if same not update:
                    del(vals[field])
        return True

    @api.multi
    def write(self, vals):
        """ Update redord(s) comes in {ids}, with new value comes as {vals}
            return True on success, False otherwise
            @param vals: dict of new values to be set

            @return: True on success, False otherwise

            Note: only updated the next change of monitored values
        """
        # Put in history cron or config value:
        self.save_history_mode(vals)

        return super(LogActivity, self).write(vals)

    # -------------------------------------------------------------------------
    # Fields function:
    # -------------------------------------------------------------------------
    @api.multi
    # Independent from fields
    @api.depends()
    def _get_cron_daily_execution(self):
        """ Fields function for calculate
        """
        daily = self.get_cron_info()
        res = {}
        for item_id in daily:
            item = daily[item_id]
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

        for activity in self:
            activity.cron_daily_exec = res.get(activity.id, False)

    @api.multi
    # Use a trigger field to force update:
    @api.depends('update_event_status')
    def _last_event_date(self):
        """ Get last activity event:
        """
        query = '''
            SELECT event.activity_id, max(event.end) 
            FROM log_activity_event event 
            GROUP BY event.activity_id 
            HAVING event.activity_id in (%s);
            ''' % (', '.join([str(item.id) for item in self]))
        _logger.info('Query launched: %s' % query)

        self.env.cr.execute(query)
        today_dt = fields.Datetime.from_string(fields.Datetime.now())

        res = {}
        for activity_id, end in self.env.cr.fetchall():
            try:
                end_dt = fields.Datetime.from_string(end)
                delta = today_dt - end_dt
                days = delta.days  # + delta.seconds / 86400.0
            except:
                end = False
                days = -1
            res[activity_id] = {
                'last_event': end,
                'last_event_days': days,
                }

        # Prepare self updating of 2 fields:
        for activity in self:
            if activity.id in res:
                activity.last_event = res[activity.id].get(
                    'last_event', False)
                activity.last_event_days = res[activity.id].get(
                    'last_event_days', -1)
            else:
                activity.last_event = False
                activity.last_event_days = -1

    @api.multi
    @api.depends()  # 'log_check_unwrited'
    def _log_in_html_format(self):
        """ Fields function for calculate
        """
        for item in self.filtered('log_check_unwrited'):  # only this field
            item.log_check_unwrited_html = '<p>'
            if not item.log_check_unwrited:
                item.log_check_unwrited_html = False
                continue

            for row in item.log_check_unwrited.split('\n'):
                res_ids = row.split('|')
                try:
                    item.log_check_unwrited_html += \
                        '<b>%s: </b> <i>%s</i> %s<br/>' % res_ids
                except:
                    item.log_check_unwrited_html += '%s<br/>' % row
            item.log_check_unwrited_html += '</p>'

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    is_active = fields.Boolean('Is active', default=True)
    code = fields.Char('Code', size=15)
    monitor = fields.Boolean(
        'Monitor', help='Monitored event are represented in dashboard')
    name = fields.Char('Event', size=64, required=True)

    from_date = fields.Date(
        'From date', help='For period event, time was the current start time')
    to_date = fields.Date('To date', help='End period for timed event')
    check_from = fields.Date(
        'Check from',
        help='Check log presence from this date, used for mark as read')
    duration = fields.Float(
        'Duration', digits=(16, 3), help='Normal duration of operation')
    check_duration = fields.Boolean(
        'Check duration', help='Check duration period of operation',
        default=True)
    duration_warning_range = fields.Float(
        'Warning range', digits=(16, 3),
        help='-/+ perc. time for raise warning')
    duration_error_range = fields.Float(
        'Error range', digits=(16, 3),
        help='-/+ perc. time for raise error')
    auto_duration = fields.Boolean(
        'Autoduration',
        help='If checked duration will be update automatically')
    partner_id = fields.Many2one(
        'res.partner', 'Partner', required=True)
    category_id = fields.Many2one(
        'log.category', 'Category', required=True)
    email_alert = fields.Boolean('Email alert')
    email_error = fields.Char('Email error', size=180)
    email_warning = fields.Char('Email warning', size=180)
    script = fields.Text('Script')
    origin = fields.Text(
        'Origin', help='Info of origin server for the activity')

    # Info about server:
    uptime = fields.Text('Uptime job')
    cron = fields.Text('Cron job')
    config = fields.Text('Config file')
    server = fields.Text('Server info')

    note = fields.Text('Note')

    cron_daily_exec = fields.Text(
        string='Cron execution',
        compute='_get_cron_daily_execution',
        store=False,
        )

    # Log mode:
    log_mode = fields.Selection([
        ('all', 'All (info, warning, error always present)'),
        ('check', 'Check (error and warning always, info every X time'),
        ], 'Log mode', required=True, default='all')
    log_check_every = fields.Integer(
        'Log check every',
        help='When log mode is check raise a message every X times')
    log_check_count = fields.Integer('Log check now is',
        help='Total message received till now')
    log_check_unwrited = fields.Text(
        'Log check unwrited',
        help='When log mode is check write here the event')
    log_check_unwrited_html = fields.Html(
        string='Update event command',
        compute='_log_in_html_format',
        # store=False,
        # compute_sudo=False,
        )

    update_event_status = fields.Boolean('Update event command')
    last_event = fields.Datetime(
        string='Last event',
        compute='_last_event_date', multi=True, store=True,
        )
    last_event_days = fields.Integer(
        string='Days',
        compute='_last_event_date', multi=True, store=True,
        )

    state = fields.Selection([
        ('unactive', 'Unactive') , # not working
        ('active', 'Active'),  # Working
        ('pause', 'Pause'),  # Currently not work butt soon yes
        ('timed', 'Out of time'),  # Out of date period
        ], 'State', default='active')


class LogActivityEvent(models.Model):
    """ Model name: LogActivityEvent
    """

    _name = 'log.activity.event'
    _description = 'Event'
    _rec_name = 'datetime'
    _order = 'datetime desc'

    @api.multi
    def dummy_nothing(self):
        """ Dummy button do nothing
        """
        return True

    @api.multi
    def mark_ok_button(self):
        """ Mark as OK
        """
        return self.write({
            'mark_ok': True,
            })

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    @api.model
    def get_duration_hour(self, start, end):
        """ Difference from 2 date in hours
        """
        if not start or not end:
            return 0.0

        start = fields.Datetime.from_string(start)
        end = fields.Datetime.from_string(end)
        gap = end - start
        return (gap.days * 24.0) + (gap.seconds / 3660.0)

    # -------------------------------------------------------------------------
    # Schedule procedure:
    # -------------------------------------------------------------------------
    @api.model
    def scheduled_log_activity_check_activity_duration(self):
        """ Check activity for mark and validate:
            1. check if started are in duration range (if needed)
            2. check if closed are in duration range else mark as OK
        """
        # Read started / closed (check duration activity)
        _logger.info('Start check activity duration')
        events = self.search([
            ('state', 'in', ('started', 'closed')),
            ('activity_id.check_duration', '=', True),
            ('mark_ok', '=', False),
            ])
        now_dt = fields.Datetime.from_string(fields.Datetime.now())

        i = 0
        for event in events:
            # Read parameters:
            duration = event.activity_id.duration * 60.0 # min
            warning_range = event.activity_id.duration_warning_range # %
            error_range = event.activity_id.duration_error_range # %

            # Calculate parameters:
            warning_duration = duration * (100.0 + warning_range) / 100.0 # min
            error_duration = duration * (100.0 + error_range) / 100.0  # min
            start = fields.Datetime.from_string(event.start)
            if event.state == 'started':
                stop = now_dt
            else:  # closed
                stop = fields.Datetime.from_string(event.end)

            gap = stop - start
            gap_min = (gap.days * 24 * 60) + (gap.seconds / 60)

            # Check range:
            if gap_min > error_duration:
                i += 1
                event.write({
                    'error_comment':
                        _('Over max duration') if event.state == 'closed'
                        else _('Started but not closed'),
                    'state': 'error',
                    })
            elif event.state == 'closed' and gap_min > warning_duration:
                self.write({
                    'error_comment': _('Duration in warning period'),
                    'state': 'warning',
                    })
            elif event.state == 'closed':  # correct range
                self.write({
                    'mark_ok': True,
                    })

        # Read closed (no check duration activity)
        _logger.info('Mark ok closed record without check duration')
        events = self.search([
            ('state', '=', 'closed'),
            ('activity_id.check_duration', '=', False),
            ('mark_ok', '=', False),
            ])
        events.write({
            'mark_ok': True,
            })
        _logger.info(
            'Mark ok closed record without check duration, tot.: %s' % (
                len(events)))

        _logger.info('End check activity duration (error: %s)' % i)
        return True

    # -------------------------------------------------------------------------
    # XMLRPC Procedure:
    # -------------------------------------------------------------------------
    @api.model
    def log_event(self, data, update_id=False):
        """ ERPEEK procedure called for create event from remote scripts
            data dict contain:
                code_partner: Key field for reach partner, inserad use company
                code_activity: Key field for reach activity, instead create ERR
                start: datetime start
                end: datetime stop
                origin: note for origin server
                log: log text
                log_warning: warning text
                log_error: error text
        """
        _logger.info('Register data event: [ID %s] %s' % (update_id, data))

        # Pool used:
        category_pool = self.env['log.category']
        activity_pool = self.env['log.activity']
        partner_pool = self.env['res.partner']

        # Read key field:
        code_partner = data.get('code_partner', False) # default company
        code_activity = data.get('code_activity', False)

        # ---------------------------------------------------------------------
        # Search foreign keys:
        # ---------------------------------------------------------------------
        # partner_id
        if code_partner:
            partner_ids = partner_pool.search([
                ('log_code', '=', code_partner),
                ])
            if partner_ids:
                partner_id = partner_ids[0].id
            else:
                _logger.error('Code partner not present %s (take company)!' % (
                    code_partner))
                partner_id = 1  # Use default
        else:
            _logger.error('Code partner present (take company)!')
            partner_id = 1  # Use detault company address

        # activity_id
        if not code_activity:
            _logger.error('Code activity not present (take ERR)!')
            code_activity = 'ERR'

        activities = activity_pool.search([
            ('partner_id', '=', partner_id),
            ('code', '=', code_activity),
            ])

        if activities:
            # Find:
            activity = activities[0]
        else:
            # Create new (to compile after on ODOO):
            # Get error category:
            category_ids = category_pool.search([
                ('code', '=', 'BAK'),  # use same code (cat.-act.)
                ])
            if category_ids:
                category_id = category_ids[0].id
            else:
                _logger.error('Code category not present (create BAK)!')
                category_id = category_pool.create({
                    'code': 'BAK',
                    'name': 'Backup',
                    'note': 'Log activity for Backup (automatic creation)'
                    })

            # Get activity:
            activity = activity_pool.create({
                'code': code_activity,
                'name': 'Error',
                'partner_id': partner_id,
                'category_id': category_id,
                # 'from_date': Fa,
                # 'to_date': ,
                # 'duration': ,
                # 'is_active'
                # 'monitor'
                # 'check_duration':
                # 'duration_warning_range':
                # 'duration_error_range':
                # 'auto_duration':
                # 'email_alert':
                # 'email_error':
                # 'email_warning':
                # 'script':
                # 'origin':
                # 'note':
                # 'state':
                })
            _logger.error(
                'Code activity not present %s create empty!' % code_activity)

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
        # Jump notification in check mode if not error and warning
        if activity.log_mode == 'check' and not log_warning and \
                not log_error:
            # jump in no count info raise:
            count_current = activity.log_check_count + 1
            count_max = activity.log_check_every
            log_check_unwrited = activity.log_check_unwrited or ''
            if count_current < count_max:
                # Update count and log partial:
                _logger.info('No notification event received')
                activity.write({
                    'log_info': log_info, # used for IP address
                    'log_check_count': count_current,
                    'log_check_unwrited': '%s|%s|%s\n' % (
                        fields.Datetime.now(),
                        log_info,
                        log_check_unwrited,
                        )
                    })
                return True, {}  # nothing to comunicate
            else:  # Reset and notificate
                _logger.info('No notification event received, now notificate!')
                activity.write({
                    'log_check_count': 0,
                    'log_check_unwrited': '',
                    })

        record = {
            'mark_ok': False,
            'activity_id': activity.id,
            'start': start,
            'end': end,
            'duration': duration,
            'origin': origin,
            'log_info': log_info,
            'log_warning': log_warning,
            'log_error': log_error,
            'error_comment': False,  # Reset if previous comment
            }

        # ---------------------------------------------------------------------
        # Normal log procedure:
        # ---------------------------------------------------------------------
        if not end:
            record['state'] = 'started'
        elif log_error:
            record['state'] = 'error'
        elif log_warning:
            record['state'] = 'warning'
        else:
            record['state'] = 'closed'
            record['mark_ok'] = True

        # ---------------------------------------------------------------------
        # Update or create event
        # ---------------------------------------------------------------------
        event_id = False
        if update_id:
            try:
                # TODO check if correct!
                res = self.browse(update_id).write(record)
                event_id = update_id
            except:
                _logger.error('Error updating event: %s' % update_id)
                res = False
        else:
            try:
                res = event_id = self.create(record).id
            except:
                _logger.error('Error create event')
                res = False

        # ---------------------------------------------------------------------
        # Manage Extra Media comunication message:
        # ---------------------------------------------------------------------
        activity_pool.raise_extra_media_comunication(activity.id, event_id)

        # Common part:
        return res, record

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    datetime = fields.Datetime(
        'Date', required=True,
        default=lambda self: fields.Datetime.now())
    activity_id = fields.Many2one('log.activity', 'Activity')
    partner_id = fields.Many2one(
        'res.partner', 'Partner',
        related='activity_id.partner_id', store=True)

    start = fields.Datetime('Start')
    end = fields.Datetime('End')
    duration = fields.Float(
        'Duration', digits=(16, 3), help='Duration of operation')

    origin = fields.Text('Origin', help='Server info (log origin)')

    log_info = fields.Text('Log info')
    log_warning = fields.Text('Log warning')
    log_error = fields.Text('Log error')
    error_comment = fields.Char('Error comment', size=180)

    mark_ok = fields.Boolean(
        'Mark as OK',
        help='Scheduled masked as OK or manually with button')
    mark_ok_comment = fields.Text('Mark as OK comment')

    state = fields.Selection([
        ('started', 'Started'),  # Start (new event)
        ('closed', 'Closed'),  # End (closed from activity with end time)
        ('missed', 'Missed'),  # Missed
        ('warning', 'Warning'),  # End with warning (scheduled check)
        ('error', 'Error'),  # End with error (scheduled check)
        ], 'State', default='started',
            help='State info, not workflow management here')


class LogCategory(models.Model):
    """ Model name: Log Category
    """
    _inherit = 'log.category'

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    activity_ids = fields.One2many('log.activity', 'category_id', 'Activity')


class ResUser(models.Model):
    """ Model name: ResUser
    """
    _inherit = 'res.users'

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    log_partner_id = fields.Many2one('res.partner', 'Log partner')


class ResPartner(models.Model):
    """ Model name: Res partner
    """
    _inherit = 'res.partner'

    # -------------------------------------------------------------------------
    # Columns:
    # -------------------------------------------------------------------------
    log_code = fields.Char('Partner log code', size=64,
        help='Partner code for link activity')
    log_users_ids = fields.One2many(
        'res.users', 'log_partner_id', 'Log user')
    log_activity_ids = fields.One2many(
        'log.activity', 'partner_id', 'Log activity')
    log_media_ids = fields.One2many(
        'log.activity.media', 'partner_id', 'Log media')
