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
import time


_logger = logging.getLogger(__name__)


class TelegramBot(orm.Model):
    """ Model name: TelegramBot
    """
    
    _name = 'telegram.bot'
    _description = 'Telegram BOT'
    _order = 'name'
    
    def get_message_url(self, cr, uid, ids, context=None):
        """ Open URL for API message list
        """
        url = 'https://api.telegram.org/bot%s/getUpdates'
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        url = url % current_proxy.token
        return {
            'name': 'Telegram messages',
            'res_model': 'ir.actions.act_url',
            'type': 'ir.actions.act_url',
            'target': 'current',
            'url': url
            } 
    
    _columns = {
        'name': fields.char('Descrizione', size=80, required=True),
        'bot': fields.char('Nome BOT', size=64, required=True),
        'token': fields.char('Token', size=64, required=True, 
            help='Format like: 495865748:ABFPw_3D1NpLo5xPWdv1vpTZZ8j1pQYo3Xk'),
        }

class TelegramGroup(orm.Model):
    """ Model name: TelegramGroup
    """
    
    _name = 'telegram.group'
    _description = 'Telegram Group'
    _order = 'name'
    
    _columns = {
        'name': fields.char('Description', size=80, required=True),
        'code': fields.char('Group ID', size=24, required=True, 
            help='Group ID, line: -123431251'),
        }


class TelegramBotChannel(orm.Model):
    """ Model name: Telegram Bot Channel
        BOT + Group where to send message
    """

    _name = 'telegram.bot.channel'
    _description = 'Telegram BOT Channel'

    # ---------------------------------------------------------------------
    # Utility:
    # ---------------------------------------------------------------------
    def get_channel_with_code(self, cr, uid, code, context=None):
        """ Search BOT with code and send message with for it
        """
        channel_ids = self.search(cr, uid, [
            ('code', '=', code),
        ], context=context)
        if len(channel_ids) > 1:
            raise
        return self.browse(cr, uid, channel_ids, context=context)[0]

    def send_message_test(self, cr, uid, ids, context=None):
        """ Send test message
        """
        channel = self.browse(cr, uid, ids, context=context)[0]
        return self.send_message(channel, message='Test message')

    def send_message(
            self, channel, message, item_id=18965, reference='OCXXX'):
        """ Utility for log event on telegram using bot and group ID
        """
        # Parameters:
        raise_error = False
        max_loop = channel.max_loop
        wait = channel.wait  # sec.

        # -----------------------------------------------------------------
        # Telegram setup:
        # -----------------------------------------------------------------
        telegram = channel.telegram_id
        group = channel.group_id
        telegram_token = telegram.token
        telegram_group = group.code
        message_mask = channel.odoo_mask

        # -----------------------------------------------------------------
        # Send Telegram message:
        # -----------------------------------------------------------------
        try:
            bot = telepot.Bot(telegram_token)
            bot.getMe()
        except:
            error = 'Error opening Telegram BOT'
            _logger.error(error)
            if raise_error:
                pass # raise

        while max_loop > 0:
            try:
                if item_id and message_mask:
                    # Add link:
                    link = message_mask.format(item_id=item_id)
                    message += '\n[%s](%s)' % (reference, link)

                bot.sendMessage(
                    telegram_group,
                    message,
                    parse_mode='Markdown'
                )
                return True
            except:
                _logger.error(
                    'Error sending message, wait and retry\n{}'.format(
                        sys.exc_info(),))
                max_loop -= 1
                time.sleep(wait)
        _logger.error('Error sending message after {} catch'.format(
            max_loop
        ))
        return False

    _columns = {
        'code': fields.char('Codice', required=True, size=15),
        'name': fields.char('Nome', required=True, size=50),

        'max_loop': fields.integer(
            'Tentativi', required=True,
            help='Per limiti di telegram in caso di errore di spedizione '
                 'la procedura proverà il numero di tentativi indicati.'),
        'wait': fields.integer(
            'Attesa', required=True,
            help='Attesa tra un tentativo e l\'altro'),

        'telegram_id': fields.many2one('telegram.bot', 'BOT', required=True),
        'group_id': fields.many2one('telegram.group', 'Group', required=True),
        'odoo_mask': fields.char(
            'ODOO Mask',
            help='Maschera utilizzata per creare il link a ODOO, usare come '
                 'placeholder dell''ID risorsa {item_id}, es: '
                 'https://erp.micronaet.it/web/resource?ID={item_id}'),
        }
    _defaults = {
        'max_loop': lambda *x: 50,
        'wait': lambda *x: 3,
    }


class TelegramBotInherit(orm.Model):
    """ Model name: Telegram Bot
    """

    _inherit = 'telegram.bot'

    _columns = {
        'channel_ids': fields.one2many(
            'telegram.bot.channel', 'telegram_id', 'Canali'),
    }
