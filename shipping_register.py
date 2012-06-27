# -*- coding: utf-8 -*-
"""
    Shipping register

    :copyright: (c) 2010-2011, Open Labs Business Solution
    :copyright: (c) 2011 by Openlabs Technologies & Consulting (P) Ltd.

    :license: AGPL, see LICENSE for more details.
"""
import base64
from ups import ShipmentConfirm, ShipmentAccept, ShipmentVoid, PyUPSException
from osv import osv, fields
from lxml import etree

STATE_SELECTION = [
    ('draft', 'Draft (Not Processed)'),
    ('confirmed', 'Confirmed'),
    ('accepted', 'Accepted'),
    ('cancelled', 'Cancelled'),
]

MESSAGE_TYPE_SELECTION = [
    ('request', 'Request'),
    ('response', 'Response')
]


# pylint: disable-msg=E1101
class UpsCodes(osv.osv):
    '''
    Model to store the UPS Service Types and Packaging Types
    '''
    _name = 'ups.codes'
    _description = __doc__
    _rec_name = 'description'

    _columns = {
        'code': fields.char('Code', size=3, required=True,),
        'description': fields.char('Description', size=50,
            required=True, select="1",),
        'type': fields.selection([
            ('service', 'Service'),
            ('package', 'Package'),
            ], 'Package Type', required=True,),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': lambda *a: True,
    }

UpsCodes()


class UpsMessage(osv.osv):
    """Model to record all UPS XML messages.
    """

    _name = 'ups.message'
    _description = __doc__

    def _text2bin(self, cursor, user, ids, field_name, arg, context):
        """Create a binary representation of the xml message so that we can be
        able to download it"""

        res = {}
        for message in self.browse(cursor, user, ids, context):
            res[message.id] = base64.b64encode(message.message)

        return res

    _columns = {
        'name': fields.char('Message name', size=50, readonly=True),
        'type': fields.selection(MESSAGE_TYPE_SELECTION,
                                 string='Message type',
                                 type='selection',
                                 readonly=True),
        'message': fields.text('XML Message', readonly=True),
        'message_bin': fields.function(_text2bin, string='XML Message',
                                   type='binary', method=True, readonly=True),
        'shipping_register_rel': fields.many2one('ups.shippingregister',
                                                 'Relation Field',
                                                 readonly=True)
    }

UpsMessage()


class UpsShippingRegister(osv.osv):
    """General register to record all shipments and keep track of it."""

    _name = 'ups.shippingregister'
    _description = __doc__[0:60]

    def on_change_shipper(self, cursor, user, ids,
        shipper_address, from_address, context=None):
        """
        Sets from address as shipper address if nothing is specified
        """
        if shipper_address and not from_address:
            return {
                'value': {
                    'from_address': shipper_address
                    }
                }
        return {}

    def get_ups_api(self, cursor, user, call='confirm', context=None):
        """
        Returns API with credentials set
        """
        company_obj = self.pool.get('res.company')
        ups_credentials = company_obj.get_ups_credentials(
            cursor, user, context)
        if not ups_credentials[0] or not ups_credentials[1] or \
            not ups_credentials[2]:
            raise osv.except_osv(('Error : '),
                ('''Please check your license details for UPS account.
                    \nSome details may be missing.'''))
        if call == 'confirm':
            call_method = ShipmentConfirm
        elif call == 'accept':
            call_method = ShipmentAccept
        elif call == 'void':
            call_method = ShipmentVoid
        else:
            call_method = None

        if call_method:
            try:
                return call_method(ups_credentials[0],
                                   ups_credentials[1],
                                   ups_credentials[2],
                                   ups_credentials[3],
                                   ups_credentials[4])
            except TypeError:
                ## Older PyUPS version
                return call_method(ups_credentials[0],
                                   ups_credentials[1],
                                   ups_credentials[2],
                                   ups_credentials[3])

    def _add_packages(self, cursor, user, register_id, context=None):
        """
        Adds the UPS style packages and return the XML element

        :param cursor: Database Cursor
        :param user: ID of User
        :param register_id: Shipment Register ID
        :param context: Context directly uses active id.
        """
        company_obj = self.pool.get('res.company')

        packages = []
        ups_uoms = company_obj.get_ups_uoms(cursor, user, context)
        register_record = self.browse(cursor, user, register_id, context)

        for package in register_record.package_det:
            package_type = ShipmentConfirm.packaging_type(
                Code=package.package_type.code)
            package_weight = ShipmentConfirm.package_weight_type(
                Weight=str(package.weight), Code=ups_uoms[0],
                Description=package.description or 'None')
            package_service_options = \
                ShipmentConfirm.package_service_options_type(
                    ShipmentConfirm.insured_value_type(
                        MonetaryValue=str(package.insured_value) or ''))
            if package.length and package.height and package.width:
                package_dimension = ShipmentConfirm.dimensions_type(
                    Code=ups_uoms[1], Length=str(package.length),
                    Height=str(package.height), Width=str(package.width),
                    Description=package.description or 'None')
            else:
                raise osv.except_osv(('Error : '),
                    ("Package Dimensions are required"))
            package_container = ShipmentConfirm.package_type(
                package_type,
                package_weight,
                package_dimension,
                package_service_options)
            packages.append(package_container)
        shipment_service = ShipmentConfirm.shipment_service_option_type(
            SaturdayDelivery=1 if register_record.saturday_delivery \
            else 'None')
        return (packages, shipment_service)

    def _add_addresses(self, cursor, user, register_id, context=None):
        """
        Adds the UPS style addresses to the ShipmentConfirm

        :param cursor: Database Cursor
        :param user: ID of User
        :param register_id: ID of Shipment Register
        :param context: Context directly uses active id.
        """
        address_obj = self.pool.get('res.partner.address')
        company_obj = self.pool.get('res.company')

        ups_shipper = company_obj.get_ups_shipper(cursor, user, context)
        register_record = self.browse(cursor, user, register_id, context)
        #Fetch Addresses
        to_address = address_obj.address_to_ups_dict(
            cursor, user, register_record.to_address.id, context)
        from_address = address_obj.address_to_ups_dict(
            cursor, user, register_record.from_address.id, context)
        shipper_address = address_obj.address_to_ups_dict(
            cursor, user, register_record.shipper_address.id, context)

        # Generating the XML Elements

        # Ship to address
        ship_to_address_elem = ShipmentConfirm.address_type(
            AddressLine1=to_address['line1'],
            AddressLine2=to_address['line2'],
            City=to_address['city'],
            PostalCode=to_address['postal_code'],
            StateProvinceCode=to_address['state_code'],
            CountryCode=to_address['country_code'],)

        # Ship from address
        ship_from_address_elem = ShipmentConfirm.address_type(
            AddressLine1=from_address['line1'],
            AddressLine2=from_address['line2'],
            City=from_address['city'],
            PostalCode=from_address['postal_code'],
            StateProvinceCode=from_address['state_code'],
            CountryCode=from_address['country_code'])

        # Shipper address
        shipper_address_elem = ShipmentConfirm.address_type(
            AddressLine1=shipper_address['line1'],
            AddressLine2=shipper_address['line2'],
            City=shipper_address['city'],
            PostalCode=shipper_address['postal_code'],
            StateProvinceCode=from_address['state_code'],
            CountryCode=shipper_address['country_code'])

        # Shipper
        shipper = ShipmentConfirm.shipper_type(
            shipper_address_elem,
            Name=shipper_address['company_name'],
            AttentionName=shipper_address['attention_name'],
            TaxIdentificationNumber=shipper_address['tin'],
            PhoneNumber=shipper_address['phone'],
            FaxNumber=shipper_address['fax'],
            EMailAddress=shipper_address['email'],
            ShipperNumber=ups_shipper)

        # Ship to
        ship_to = ShipmentConfirm.ship_to_type(
            ship_to_address_elem,
            CompanyName=to_address['company_name'],
            AttentionName=to_address['attention_name'],
            TaxIdentificationNumber=to_address['tin'],
            PhoneNumber=to_address['phone'],
            FaxNumber=to_address['fax'],
            EMailAddress=to_address['email'],
            LocationId='None')

        # Ship from
        ship_from = ShipmentConfirm.ship_from_type(
            ship_from_address_elem,
            CompanyName=from_address['company_name'],
            AttentionName=from_address['attention_name'],
            TaxIdentificationNumber=from_address['tin'],
            PhoneNumber=from_address['phone'],
            FaxNumber=from_address['fax'],
            EMailAddress=from_address['email'])

        return (shipper, ship_to, ship_from)

    def do_shipping_request(self, cursor, user, ids, context=None):
        """
        This method calls the UPS API, sends the ShipmentConfirm Request
        to the API and gets the total cost of shipment and tracking number.

        :param cursor: Database Cursor
        :param user: ID of User
        :param context: Context directly uses active id.
        """
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        packages_obj = self.pool.get('ups.shippingregister.package')
        company_obj = self.pool.get('res.company')
        ups_shipper = company_obj.get_ups_shipper(cursor, user, context)
        ups_message_obj = self.pool.get('ups.message')

        payment_info_prepaid = \
            ShipmentConfirm.payment_information_prepaid_type(
                AccountNumber=ups_shipper)
        payment_info = ShipmentConfirm.payment_information_type(
            payment_info_prepaid)

        for shipment_record in self.browse(cursor, user, ids, context):
            (shipper, ship_to, ship_from) = self._add_addresses(cursor, user,
                shipment_record.id, context)
            service = ShipmentConfirm.service_type(
                Code=shipment_record.service_type.code)

            (packages, shipment_service) = self._add_packages(cursor, user,
                shipment_record.id, context)
            ship_confirm = ShipmentConfirm.shipment_confirm_request_type(
                shipper, ship_to, ship_from, service, payment_info,
                shipment_service, *packages,
                Description=shipment_record.description or 'None')

            shipment_confirm_instance = self.get_ups_api(cursor, user,
                'confirm', context)

            try:
                response = shipment_confirm_instance.request(
                    ship_confirm)
                if isinstance(response, tuple):
                    request = response[0]
                    response = response[1]

            except PyUPSException, error:
                if company_obj.get_ups_save_xml(cursor, user, context):
                    # TODO: We need a better error exception here.
                    xml_messages = [(0, 0, {'name': 'ConfirmShipmentRequest',
                                            'type': 'request',
                                            'message': error[1]}),
                                    (0, 0, {'name': 'ConfirmShipmentResponse',
                                            'type': 'response',
                                            'message': etree.tostring(
                                                error[2], pretty_print=True)})]

                    self.write(cursor, user, shipment_record.id,
                               {'xml_messages': xml_messages}, context)

                raise osv.except_osv(('Error : '), ('%s' % error[0]))
            # Now store values in the register

            currency_id = currency_obj.search(cursor, user,
                [('symbol', '=', \
                    response.ShipmentCharges.TotalCharges.CurrencyCode)])
            uom_id = uom_obj.search(cursor, user, [
                ('name', '=', \
                    response.BillingWeight.UnitOfMeasurement.Code.pyval)])

            before = ShipmentConfirm.extract_digest(response)

            if company_obj.get_ups_save_xml(cursor, user, context):
                xml_messages = [(0, 0, {'name': 'ConfirmShipmentRequest',
                                        'type': 'request',
                                        'message': request}),
                                (0, 0, {'name': 'ConfirmShipmentResponse',
                                        'type': 'response',
                                        'message': etree.tostring(
                                            response, pretty_print=True)})]
            else:
                xml_messages = []

            self.write(cursor, user, shipment_record.id,
                {
                    'name': response.ShipmentIdentificationNumber,
                    'billed_weight': response.BillingWeight.Weight,
                    'billed_weight_uom': uom_id and uom_id[0] or False,
                    'total_amount': response.ShipmentCharges.\
                        TotalCharges.MonetaryValue,
                    'total_amount_currency': currency_id and \
                                                currency_id[0] or False,
                    'digest': ShipmentConfirm.extract_digest(response),
                    'xml_messages': xml_messages,
                    'state': 'confirmed'
                    }, context)

            after = self.browse(cursor, user, shipment_record.id).digest

            packages_obj.write(cursor, user,
                [pkg.id for pkg in shipment_record.package_det],
                {'state': 'confirmed'}, context)
        return True

    def set_to_draft(self, cursor, user, ids, context=None):
        """
        This method will set this record back to draft and editable mode
        """
        self.write(cursor, user, ids,
            {'state': 'draft', 'name': 'Not Processed'}, context)
        package_obj = self.pool.get('ups.shippingregister.package')
        package_ids = package_obj.search(
            cursor, user, [('shipping_register_rel', 'in', ids)],
            context=context)
        package_obj.write(
            cursor, user, package_ids, {'state': 'draft'}, context)
        return True

    def accept_price(self, cursor, user, ids, context=None):
        '''
        This method calls the Accept Price function of the wizard .
        :param cursor: Database Cursor
        :param user: ID of User
        :param ids: ID of Current record.
        :param context: Context(no direct use).
        :return: True
        '''
        packages_obj = self.pool.get('ups.shippingregister.package')
        company_obj = self.pool.get('res.company')

        for shipping_register_record in self.browse(cursor, user, ids,
                                                    context):
            # writing image to digest so that it can be used.
            shipment_accept = ShipmentAccept.shipment_accept_request_type(\
                shipping_register_record.digest)

            shipment_accept_instance = self.get_ups_api(cursor, user,
                                                        'accept', context)

            try:
                response = shipment_accept_instance.request(
                    shipment_accept)
                if isinstance(response, tuple):
                    request = response[0]
                    response = response[1]

            except PyUPSException, error:
                if company_obj.get_ups_save_xml(cursor, user, context):
                    # TODO: We need a better error exception here.
                    xml_messages = [(0, 0, {'name': 'AcceptShipmentRequest',
                                            'type': 'request',
                                            'message': error[1]}),
                                    (0, 0, {'name': 'AcceptShipmentResponse',
                                            'type': 'response',
                                            'message': etree.tostring(
                                                error[2], pretty_print=True)})]

                    self.write(cursor, user, shipping_register_record.id,
                               {'xml_messages': xml_messages}, context)

                raise osv.except_osv(('Error : '), ('%s' % error[0]))

            packages = []
            for package in response.ShipmentResults.PackageResults:
                packages.append(package)
            # UPS does not give the information as to which package
            # got which label, Here we are just assuming that they
            # came in order to assign the label
            package_record_ids = [pkg.id for pkg in \
                shipping_register_record.package_det]
            assert len(package_record_ids) == len(packages)
            for package in packages:
                register_vals = {
                    'tracking_no': package.TrackingNumber.pyval,
                    'label_image': package.LabelImage.GraphicImage.pyval,
                    'state': 'accepted'
                }
                packages_obj.write(
                    cursor, user, package_record_ids[packages.index(package)],
                    register_vals, context)
            # changing state to accepted of shipping register record...
            if company_obj.get_ups_save_xml(cursor, user, context):
                xml_messages = [(0, 0, {'name': 'AcceptShipmentRequest',
                                        'type': 'request',
                                        'message': request}),
                                (0, 0, {'name': 'AcceptShipmentResponse',
                                        'type': 'response',
                                        'message': etree.tostring(
                                            response, pretty_print=True)})]
            else:
                xml_messages = []

            self.write(cursor, user, shipping_register_record.id,
                {'state': 'accepted',
                 'xml_messages': xml_messages}, context)
        return True

    def do_shipping_void(self, cursor, user, ids, context=None):
        '''
        This method calls the Cancel Shipping function of the wizard .
        :param cursor: Database Cursor
        :param user: ID of User
        :param ids: ID of Current record.
        :param context: Context(no direct use).
        :return: True
        '''

        packages_obj = self.pool.get('ups.shippingregister.package')
        company_obj = self.pool.get('res.company')

        for shipping_register_record in self.browse(cursor, user, ids,
                                                    context):
            # writing image to digest so that it can be used.
            shipment_void = ShipmentVoid.void_shipment_request_type(
                shipping_register_record.name,
                [p.tracking_no for p in shipping_register_record.package_det]
                )

            shipment_void_instance = self.get_ups_api(cursor, user, 'void',
                                                      context)

            try:
                response = shipment_void_instance.request(
                    shipment_void)
                if isinstance(response, tuple):
                    request = response[0]
                    response = response[1]

            except PyUPSException, error:
                if company_obj.get_ups_save_xml(cursor, user, context):
                    # TODO: We need a better exception handling here.
                    xml_messages = [(0, 0, {'name': 'VoidShipmentRequest',
                                            'type': 'request',
                                            'message': error[1]}),
                                    (0, 0, {'name': 'VoidShipmentResponse',
                                            'type': 'response',
                                            'message': etree.tostring(
                                                error[2], pretty_print=True)})]

                    self.write(cursor, user, shipping_register_record.id,
                               {'xml_messages': xml_messages}, context)

                raise osv.except_osv(('Error : '), ('%s' % error[0]))

            try:
                packages = []
                for package in response.PackageLevelResults:
                    packages.append(package)
                # UPS does not give the information as to which package
                # got which label, Here we are just assuming that they
                # came in order to assign the label
                package_record_ids = [pkg.id for pkg in \
                                          shipping_register_record.package_det]
                assert len(package_record_ids) == len(packages)
                for package in packages:
                    register_vals = {
                        'state': 'cancelled'
                        }
                    packages_obj.write(
                        cursor, user,
                        package_record_ids[packages.index(package)],
                        register_vals, context)
            except AttributeError:
                pass

            # changing state to accepted of shipping register record...
            if company_obj.get_ups_save_xml(cursor, user, context):
                xml_messages = [(0, 0, {'name': 'VoidShipmentRequest',
                                        'type': 'request',
                                        'message': request}),
                                (0, 0, {'name': 'VoidShipmentResponse',
                                        'type': 'response',
                                        'message': etree.tostring(
                                            response, pretty_print=True)})]
            else:
                xml_messages = []

            self.write(cursor, user, shipping_register_record.id,
                       {'state': 'cancelled',
                 'xml_messages': xml_messages}, context)
        return True

    _columns = {
        'name': fields.char(string='Name', select="1", size=150,
            readonly=True),
        'service_type': fields.many2one('ups.codes', 'Service Type',
            domain=[('type', '=', 'service')], select="1"),
        'package_det': fields.one2many('ups.shippingregister.package',
            'shipping_register_rel', string='Packages',),
        'to_address': fields.many2one('res.partner.address',
            'Shipping Address', required=True),
        'from_address': fields.many2one('res.partner.address',
            'From Address', required=True),
        'shipper_address': fields.many2one('res.partner.address',
            'Shipper Address', required=True),
        'saturday_delivery': fields.boolean('Saturday Delivery?'),
        'description': fields.text('Description'),
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True,),
        'xml_messages': fields.one2many('ups.message',
                                        'shipping_register_rel',
                                        'XML Messages'),
        # The following are UPS filled information
        'billed_weight': fields.float('Billed Weight', digits=(10, 4),
            readonly=True, help=(
                'The billed weght may be different from the actual weight.'
                'This is computed by UPS.')),
        'billed_weight_uom': fields.many2one('product.uom',
                                             'Billed Weight UOM',
                                             readonly=True),
        'total_amount': fields.float('Total Amount', digits=(14, 4),
            select="1", readonly=True),
        'total_amount_currency': fields.many2one('res.currency',
            'Total Amount Currency', select="2", readonly=True,),
        'digest': fields.binary('Information digest for DIGEST'),
        'notificationemailaddr': fields.char('Notification eMail Addresses',
            size=255, help='Separated by commas(,).'),
    }

    _defaults = {
        'name': lambda *a: 'Not Processed',
        'state': lambda *a: 'draft'
    }

UpsShippingRegister()


class UpsShippingRegisterPackage(osv.osv):
    """
    Model to record all packages corresponding
    to a shipment record and keep track of it.
    """
    _name = 'ups.shippingregister.package'
    _description = __doc__[0:60]

    def _make_name(self, cursor, user, ids, name, unknown, context=None):
        '''
        It makes a name by joining tracking_no generated by UPS and state.

        :param cursor: Database Cursor
        :param user: ID of User
        :param ids: ID of Current Record
        :param context: Context from parent method.(no direct use)
        :return: returns name in format 'tracking_no+state'
        '''
        result = {}
        shipping_register_obj = self.pool.get('ups.shippingregister')
        record_id = self.browse(cursor, user, ids)[0].shipping_register_rel
        record = shipping_register_obj.browse(cursor, user, record_id, context)
        for each in ids:
            data = self.browse(cursor, user, each, context)
            name = (data.tracking_no or '') + (record.state or '')
            result[each] = "%s.gif" % name
        return result

    _columns = {
        'name': fields.function(_make_name, type="char",
            method=True, string='Name', select="1", size=150),
        'tracking_no': fields.char('Tracking No.', size=100),
        'label_image': fields.binary('Label Image',),
        'package_type': fields.many2one('ups.codes', 'Package Type',
            domain=[('type', '=', 'package')], select="1"),
        'weight': fields.float('Weight', digits=(10, 4),),
        'length': fields.float('Length', digits=(10, 2)),
        'height': fields.float('Height', digits=(10, 2)),
        'width': fields.float('Width', digits=(10, 2)),
        'shipping_register_rel': fields.many2one('ups.shippingregister',
            'Relation Field',),
        'state': fields.selection(STATE_SELECTION,
            string='State', type='selection', readonly=True),
        'description': fields.text('Description'),
        'insured_value': fields.float('Insured Value', digits=(10, 2))
    }

    _defaults = {
        'state': lambda * a: 'draft'
    }

UpsShippingRegisterPackage()
