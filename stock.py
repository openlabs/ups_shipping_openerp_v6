# -*- coding: UTF-8 -*-
"""
Inherits stock.picking to create a new page for 'Shipping Information'
which appears only in 'done' state.
"""
#########################################################################
#                                                                       #
# Copyright (c) 2010 Open Labs Business Solutions                       #
# Copyright (c) 2010-2011 Openlabs Technologies & Consulting (P) LTD    #
#                                                                       #
# This program is free software: you can redistribute it and/or modify  #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 3 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# This program is distributed in the hope that it will be useful,       #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
# GNU General Public License for more details.                          #
#                                                                       #
# You should have received a copy of the GNU General Public License     #
# along with this program.  If not, see <http://www.gnu.org/licenses/>. #
#########################################################################

from osv import osv, fields


# pylint: disable-msg=E1101
class StockPicking(osv.osv):
    '''
    Inherits stock.picking to integrate UPS API with OpenERP.
    '''
    _inherit = "stock.picking"

    def _get_move_line_weights(self, cursor, user, rec_id, context=None):
        """
        Return weight for individual lines
        """
        product_uom_obj = self.pool.get('product.uom')
        weight_matrix = {}
        data = self.browse(cursor, user, rec_id, context)
        for move in data.move_lines:
            if move.product_packaging:
                #If packaging exist for a move_line
                weight = move.product_packaging.weight
            else:
                #if packaging does not exist for a move line
                product_weight = move.product_id.weight_net
                if move.product_uom.id != move.product_id.uom_id.id :
                    quantity = product_uom_obj._compute_qty(
                        cursor, user, move.product_uom.id, 
                        move.product_qty, move.product_id.uom_id.id)
                else:
                    quantity = move.product_qty
                weight = product_weight * quantity
            weight_matrix[move.id] = weight
        return weight_matrix
        
    def _total_weight(self, cursor, user, ids, 
                      something, unknown, context=None):
        '''
        The weight for each line is product_packaging.weight
        if packaging exists for a move line or (product.weight * qty)
        if theres no packaging. The field should display
         a sum of all such weights independently computed.

        :param cursor: Database Cursor
        :param user: ID of User
        :param ids: ID of Current Record
        :param context: Context from parent method.(no direct use)
        :return: returns total weight of all the move line.
        '''
        result = {}
        for rec_id in ids:
            weight_matrix = self._get_move_line_weights(
                cursor, user, rec_id, context)
            result[rec_id] = sum(weight_matrix.values())
        return result

    def onchange_existing(self, cursor, user, ids,
            is_existing, required_packing, context=None):
        """
        On change of shipping of existing set the packings
        """
        if ids:
            if not (is_existing and required_packing):
                weight_matrix = self._get_move_line_weights(
                    cursor, user, ids[0], context)
                weight_list = ["%.3f" % weight \
                               for weight in weight_matrix.values()]
                return dict(value = {
                    'required_packing': ",".join(weight_list)
                    })
        return { }

    _columns = {
        'has_shipping': fields.boolean('Use UPS Shipping'),
        'is_existing': fields.boolean('Use Existing Shipment record'),
        'total_weight': fields.function(_total_weight,
            method=True, string="Total Weight"),
        'required_packing': fields.char(
            'Packing weights', size=20,
            help="Enter packings sep, by ',' Eg. 2,3.5,4"),
        'shipping_register': fields.many2one(
            'ups.shippingregister', 'UPS Shipment Record',),
        'service_type': fields.many2one(
            'ups.codes', 'Service Type', domain=[('type', '=', 'service')]),
        'saturday_delivery': fields.boolean('Saturday Delivery'),
        'package_type': fields.many2one(
            'ups.codes', 'Package Type', domain=[('type', '=', 'package')]),
        'shipping_state': fields.related(
            'shipping_register', 'state', type="char", readonly=True)
    }

    def generate_shipping(self, cursor, user, ids, context=None):
        """
        Generates shipping record from given information
        """
        ship_register_obj = self.pool.get('ups.shippingregister')
        ship_package_obj = self.pool.get('ups.shippingregister.package')

        for picking_record in self.browse(cursor, user, ids, context):
            if not picking_record.required_packing:
                weight_matrix = self._get_move_line_weights(
                    cursor, user, ids[0], context)
                weights_list = weight_matrix.values()
            else:
                try:
                    weights_list = [float(wt) \
                        for wt in picking_record.required_packing.split(",")]
                except:
                    raise osv.except_osv('Error in validation',
                        'Invalid package splitting. Ensure format is correct')

            # Step 0: Workarounds
            # There is no location for picking
            # So take location as from address in 1st stock move line
            location = picking_record.move_lines[0].location_id
            if not location.address_id.id:
                raise osv.except_osv(
                    'Error in validation',
                    'The Selected stock location has no address'\
                    '\nAdd an address for location "%s"' % location.name)

            # Step 1: Create shipping register
            ship_id = ship_register_obj.create(cursor, user, 
                {
                'service_type': picking_record.service_type.id,
                'to_address': picking_record.address_id.id,
                'from_address': location.address_id.id,
                'shipper_address': location.address_id.id,
                'saturday_delivery': picking_record.saturday_delivery,
                }, context)

            # Step 2: Create packing items
            for weight in weights_list:
                ship_package_obj.create(cursor, user, 
                    {
                    'package_type': picking_record.package_type.id,
                    'weight': weight,
                    'shipping_register_rel': ship_id,
                    'description': picking_record.note,
                    }, context)
            self.write(cursor, user, picking_record.id, 
                {'shipping_register': ship_id}, context)
        return True

StockPicking()
