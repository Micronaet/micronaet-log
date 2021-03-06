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

{
    'name': 'Log Activity',
    'version': '0.1',
    'category': 'Log',
    'description': '''        
        Log database for partner server activity, like:
         - ETL operations
         - Backup operations
         - Mount operation
         - Hardware status
         - RAID status 
         etc.
        ''',
    'author': 'Micronaet S.r.l. - Nicola Riolini',
    'website': 'http://www.micronaet.it',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'excel_export', # For reporting
        ],
    'init_xml': [],
    'demo': [],
    'data': [
        'security/ir.model.access.csv',    
        'activity_view.xml',
        'scheduler.xml',
        
        # Data:
        'data/category.xml'
        ],
    'active': False,
    'installable': True,
    'auto_install': False,
    'application': True,
    }
