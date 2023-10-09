# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import pdb
import sys

import erppeek
import ConfigParser
import smtplib
from datetime import datetime
from email.MIMEMultipart import MIMEMultipart
from email.mime.text import MIMEText

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
cfg_file = os.path.expanduser('./logger.cfg')
now = str(datetime.now())[:19]

config = ConfigParser.ConfigParser()
config.read([cfg_file])

# ERP Connection:
odoo = {
    'database': config.get('odoo', 'database'),
    'user': config.get('odoo', 'user'),
    'password': config.get('odoo', 'pwd'),
    'server': config.get('odoo', 'server'),
    'port': config.get('odoo', 'port'),
    }


def send_mail(to, subject, text, odoo=odoo):
    """ Sent mail using ODOO mailer setup
    """
    # -------------------------------------------------------------------------
    # Connect to ODOO:
    # -------------------------------------------------------------------------
    odoo_erp = erppeek.Client(
        'http://%s:%s' % (odoo['server'], odoo['port']),
        db=odoo['database'],
        user=odoo['user'],
        password=odoo['password'],
        )
    mailer = odoo_erp.model('ir.mail_server')

    # -------------------------------------------------------------------------
    # SMTP Sent:
    # -------------------------------------------------------------------------
    mailer_ids = mailer.search([])
    if not mailer_ids:
        return '[ERR] No mail server configured in ODOO'
    odoo_mailer = sorted(mailer.browse(mailer_ids),
                         key=lambda x: x.sequence)[0]

    # Open connection:
    print('[INFO] Sending using "%s" connection [%s:%s]' % (
        odoo_mailer.name,
        odoo_mailer.smtp_host,
        odoo_mailer.smtp_port,
        ))

    if odoo_mailer.smtp_encryption in ('ssl', 'starttls'):
        smtp_server = smtplib.SMTP_SSL(
            odoo_mailer.smtp_host, odoo_mailer.smtp_port)
    else:
        return '[ERR] Connect only SMTP SSL server!'

    smtp_server.login(odoo_mailer.smtp_user, odoo_mailer.smtp_pass)
    for address in to.replace(' ', '').split(','):
        print('Sending mail to: %s ...' % to)
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = odoo_mailer.smtp_user
        msg['To'] = address
        text = text.replace('\n', '<br/>')
        msg.attach(MIMEText(text, 'html'))

        # Send mail:
        smtp_server.sendmail(odoo_mailer.smtp_user, to, msg.as_string())

    smtp_server.quit()
    return ''  # No error

pdb.set_trace()
if __name__ == '__main__':
    if len(sys.argv) == 3:
        to = sys.argv[0]
        subject = sys.argv[1]
        text = sys.argv[2]
        send_mail(to, subject, text)
    else:
        print('Wrong call send mail')

