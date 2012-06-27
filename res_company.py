# -*- coding: utf-8 -*-
"""
    Customizes company to have UPS API Information

    :copyright: (c) 2010-2011, Open Labs Business Solution
    :copyright: (c) 2011 by Openlabs Technologies & Consulting (P) Ltd.

    :license: AGPL, see LICENSE for more details.
"""
from osv import osv, fields


class ResCompany(osv.osv):
    """
    Company is the highest level of abstraction in open ERP
    This will add four fields for license key, username, password
     and shipper no.
    """
    _inherit = 'res.company'
    _columns = {
        'ups_license_key': fields.char('UPS License Key', size=100),
        'ups_user_id': fields.char('UPS User Name', size=100),
        'ups_password': fields.char('UPS User Password', size=100),
        'ups_shipper_no': fields.char('UPS Shipper Number', size=100),
        'ups_test': fields.boolean('Is Test ?'),

        # Possible Values : KGS/ LBS
        'ups_weight_uom': fields.many2one('product.uom',
                                          'UPS UOM for Weights'),

        #Codes used by UPS are:
        #    IN = Inches, CM = Centimeters, 00 = Metric Units Of
        #    Measurement, 01 = English Units of Measurement.
        #    In Canada-origin shipments no defaulting is performed
        #    and a unit of measurement is required. For shipment
        #    with return service the unit of measure is defaulted to
        #    the shipper's country unit of measure. For all other
        #    shipments the unit of measurement will default to the unit of
        #    measurement for the origin country
        'ups_length_uom': fields.many2one('product.uom',
                                          'UPS UOM for Lengths'),
        # Save the XML Request/Response messages ?
        'ups_save_xml': fields.boolean('Save XML Messages ?'),
    }

    def get_ups_credentials(self, cursor, user, context=None):
        """
        Returns the credentials in tuple
        :param cursor: DB Cursor
        :param User: Integer ID of curr user
        :param context: Context dictionary, no direct usage

        :return: (license_key, user_id, password, ups_test, ups_save_xml)
        """
        user_obj = self.pool.get('res.users')
        company_obj = self.pool.get('res.company')
        user_record = user_obj.browse(cursor, user, user, context)
        company = company_obj.browse(cursor, user,
                                     user_record.company_id.id, context)
        return (
            company.ups_license_key,
            company.ups_user_id,
            company.ups_password,
            company.ups_test,
            company.ups_save_xml,
        )

    def get_ups_uoms(self, cursor, user, context=None):
        """Returns the codes of weight and length UOM used by UPS
        """
        user_obj = self.pool.get('res.users')
        company_obj = self.pool.get('res.company')
        user_record = user_obj.browse(cursor, user, user, context)
        company = company_obj.browse(cursor, user,
                                    user_record.company_id.id, context)

        return (
            company.ups_weight_uom.name,
            company.ups_length_uom.name,
        )

    def get_ups_shipper(self, cursor, user, context=None):
        """Returns the UPS Shipper
        """
        user_obj = self.pool.get('res.users')
        company_obj = self.pool.get('res.company')
        user_record = user_obj.browse(cursor, user, user, context)
        company = company_obj.browse(cursor, user,
                                    user_record.company_id.id, context)

        return company.ups_shipper_no

    def get_ups_save_xml(self, cursor, user, context=None):
        """Returns the UPS Save XML flag
        """
        user_obj = self.pool.get('res.users')
        company_obj = self.pool.get('res.company')
        user_record = user_obj.browse(cursor, user, user, context)
        company = company_obj.browse(cursor, user,
                                    user_record.company_id.id, context)

        return company.ups_save_xml

ResCompany()
