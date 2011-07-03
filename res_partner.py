# -*- coding: UTF-8 -*-
"""
    Customizes Address to return UPS API style address
        
    :copyright: (c)2010-2011, Open Labs Business Solution
    :copyright: (c) 2011 by Openlabs Technologies & Consulting (P) Ltd.
    
    :license: AGPL, see LICENSE for more details.
"""
import string
from osv import osv, fields

class ResPartnerAddress(osv.osv):
    """
    Add method to return address in UPS format
    """
    _inherit = "res.partner.address"
    
    def address_to_ups_dict(self, cursor, user, id, context=None):
        """
        This method creates the dictionary of all the
        details of the recipient of the package.
        These details are to be used by the UPS integration API.
        
        :param cursor: Database Cursor
        :param user: ID of User
        :param id: ID of the Record sent by the calling statement
        :param context: Context from parent method.(no direct use)
        
        :return: Returns the dictionary comprising of the details
                of the package recipient.
        """
        if type(id)==list:
            id = id[0]
        address = self.browse(cursor, user, id, context)
        phone = address.phone
        if phone:
            phone = "".join([char for char in phone if char in string.digits])
        return {
            'line1' : address.street or 'None',
            'line2' : address.street2 or 'None',
            'city' : address.city or 'None',
            'postal_code' : address.zip or 'None',
            'country_code' : address.country_id and \
                                address.country_id.code or 'None',
            'state_code' : address.state_id and \
                                address.state_id.code or 'None',
            'phone' : phone or 'None',
            'company_name' : address.partner_id and \
                                address.partner_id.name or 'None',
            'attention_name' : address.name or 'None',
            'tin' : address.partner_id and address.partner_id.vat or 'None',
            'email' : address.email or 'None',
            'fax' : address.fax or 'None', 
        }

ResPartnerAddress()
