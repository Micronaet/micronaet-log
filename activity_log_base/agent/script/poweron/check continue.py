#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
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
import subprocess
import time
import shutil

ip = '192.168.1.1'
command = 'ping %s' % ip
check_ok = 'from %s' % ip
check_ko = 'Host Unreachable'

sleep = 20.0  # total second to check
ping_ok = 15  # minimum level of right ping
max_check = 5  #24 * 60 / sleep # Total run daily

log_filename = './ping.log'
exit = False
counter = 0
while not exit:
    counter += 1

    # -------------------------------------------------------------------------
    # Run process for collect data:
    # -------------------------------------------------------------------------
    print('\nStart logging on: %s [counter %s max %s]' % (
        log_filename, counter, max_check))

    # Open log file:
    log_file = open(log_filename, 'w')

    # Generate subprocess on log file:
    print('Open subprocess')
    ret_val = subprocess.Popen(
        command,
        stdout=log_file,
        stderr=subprocess.PIPE,
        shell=True)

    # Polling data to file:
    refresh_file = False
    while not ret_val.poll() and not refresh_file:
        # ---------------------------------------------------------------------
        # Poll data:
        # ---------------------------------------------------------------------
        print('Start collect data: %s' % ret_val)
        log_file.flush()
        print('Flush data and sleep %s sec.' % sleep)
        time.sleep(sleep) # sec.

        # ---------------------------------------------------------------------
        # Read data recorded:
        # ---------------------------------------------------------------------
        print('\nCheck collected data...')
        log_file.close()
        statinfo = os.stat(log_filename)
        dimension = statinfo.st_size
        if dimension: # file present:
            log_file = open(log_filename, 'r')
            correct = 0
            last_ok = True
            for line in log_file:
                #print line
                if check_ok in line:
                    correct += 1
                    last_ok = True
                else:
                    last_ok = False

            # -----------------------------------------------------------------
            # Read esit status:
            # -----------------------------------------------------------------
            log_file.close()
            if not last_ok and correct < ping_ok:
                fail = True
                status = 'KO Server min reply not reached: %s/%s (%s sec.)' % (
                    correct,
                    ping_ok,
                    sleep,
                    )
            else:
                fail = False # override if count restart
                status = 'OK Server [Reply %s in %s sec.]%s' % (
                    correct,
                    sleep,
                    '<<< GAP' if correct < ping_ok else '',
                    )
        else:
            fail = True # no file = no reply
            status = 'KO Server never reply in this block %s sec' % sleep

        print(status)
        if fail:
            print('DO Fail action!') # TODO

        print('Remove %s' % log_filename)
        os.remove(log_filename)
        refresh_file = True
        print('Cleaning file...')

    if counter >= max_check:
        exit = True

print('Total check raised: counter %s / %s' % (counter, max_check))
