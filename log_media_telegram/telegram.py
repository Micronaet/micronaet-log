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
import telepot
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)


class TelegramBot(orm.Model):
    """ Model name: TelegramBot
    """
    
    _name = 'telegram.bot'
    _description = 'Telegram BOT'
    _rec_name = 'name'
    _order = 'name'
    
    _columns = {
        'name': fields.char('Description', size=80, required=True),
        'bot': fields.char('BOT Name', size=64, required=True),
        'token': fields.char('Token', size=64, required=True, 
            help='Format like: 495865748:ABFPw_3D1NpLo5xPWdv1vpTZZ8j1pQYo3Xk'),
        }

class TelegramGroup(orm.Model):
    """ Model name: TelegramGroup
    """
    
    _name = 'telegram.group'
    _description = 'Telegram Group'
    _rec_name = 'name'
    _order = 'name'
    
    _columns = {
        'name': fields.char('Description', size=80, required=True),
        'code': fields.char('Group ID', size=24, required=True, 
            help='Group ID, line: -123431251'),
        }

class TelegramBot(orm.Model):
    """ Model name: TelegramBot
    """
    
    _inherit = 'telegram.bot'

    _columns = {
        'group_ids': fields.many2many(
            'telegram.group', 'telegram_bot_group_rel', 
            'bot_id', 'group_id', 'Groups'),
        }

class TelegramBotLog(orm.Model):
    """ Model name: TelegramBotLog
    """
    
    _name = 'telegram.bot.log'
    _description = 'Telegram BOT log'
    _rec_name = 'telegram_id'
    
    _columns = {
        'telegram_id': fields.many2one('telegram.bot', 'BOT', required=True),
        'group_id': fields.many2one('telegram.group', 'Group', required=True),
        'activity_id': fields.many2one('log.activity', 'Activity'),
        'log_info': fields.boolean('Log info'),
        'log_warning': fields.boolean('Log warning'),
        'log_error': fields.boolean('Log error'),
        'message': fields.char('Message', size=80, 
            help='Extra message used append to Event'),
        }
        
    _defaults = {
        'log_error': lambda *x: True,
        }

class LogActivity(orm.Model):
    """ Model name: Log event
    """
    
    _inherit = 'log.activity'

    # -------------------------------------------------------------------------
    # Override event:
    # -------------------------------------------------------------------------
    def raise_extra_media_comunication(self, cr, uid, activity_id, event_id, 
            context=None):
        ''' Override procedure for raise extra event like: 
            Mail, SMS, Telegram Message, Whatsapp message etc.
            All override procedure will be introduced by a new module
        '''
        # ---------------------------------------------------------------------    
        # Utility:
        # ---------------------------------------------------------------------    
        def log_event(telegram, event_text):
            ''' Utility for log event on telegram using bot and group ID
            '''
            # -----------------------------------------------------------------
            # Telegram setup:
            # -----------------------------------------------------------------
            telegram_token = telegram.telegram_id.token
            telegram_group = telegram.group_id.code

            # -----------------------------------------------------------------
            # Comunicate Telegram message:
            # -----------------------------------------------------------------
            bot = telepot.Bot(telegram_token)
            bot.getMe()
            bot.sendMessage(telegram_group, event_text)
            return True

        # ---------------------------------------------------------------------    
        # Raise overrided list of event:
        # ---------------------------------------------------------------------    
        res = super(LogActivity, self).raise_extra_media_comunication(
            cr, uid, activity_id, event_id, context==context)
        
        # ---------------------------------------------------------------------    
        # Launch Telegram event if needed:
        # ---------------------------------------------------------------------
        activity = self.browse(cr, uid, activity_id, context=context)
        bar_list = '-' * 50

        if event_id:
            event_pool = self.pool.get('log.activity.event')
            event_proxy = event_pool.browse(cr, uid, event_id, context=context)
            if event_proxy.state in ('error', 'warning'):
                event_state = event_proxy.state
            else:
                event_state = 'info'
                    
            event_mask = _(
                '%s\n%s\n%s\n%%s\nActivity %s: [%s] %s (%s)\n\n'
                'Start: %s\nEnd: %s\n'
                'Info: %s\nWarning: %s\nError: %s\n%s' % (
                    bar_list,
                    event_state.upper(),
                    bar_list,
                    activity.category_id.name,
                    activity.code,
                    activity.name,
                    activity.partner_id.name,
                    
                    event_proxy.start,
                    event_proxy.end,
                    
                    (event_proxy.log_info or '').strip(),
                    (event_proxy.log_warning or '').strip(),
                    (event_proxy.log_error or '').strip(),
                    bar_list,
                    ))
        else: # Not present:
            event_state = 'error'
            event_mask = _(
                '%s\n%s\n%s\n%%s\nActivity %s: [%s] %s (%s)\n'
                'Event not present (or not created)\n%s') % (
                    bar_list,
                    event_state.upperr(),
                    bar_list,
                    activity.category_id.name,
                    activity.code,
                    activity.name,
                    activity.partner_id.name,
                    bar_list,
                    )
            
        for telegram in activity.telegram_ids:
            event_text = event_mask % (telegram.message or '')
            if event_state == 'info' and telegram.log_info:
                # Info log:
                log_event(telegram, event_text)
            elif event_state == 'warning' and telegram.log_warning:
                # Warning log:
                log_event(telegram, event_text)
            elif event_state == 'error' and telegram.log_error:
                # Error log:
                log_event(telegram, event_text)
        return res
    
    
    _columns = {
        'telegram_ids': fields.one2many(
            'telegram.bot.log', 'activity_id', 'Telegram log'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
