# -*- coding: utf-8 -*-
"""
    test_shipping_package

    Test the shipping integration with openerp

    :copyright: (c) 2011 by Openlabs Technologies & Consulting (P) Limited
    :license: GPL, see LICENSE for more details.
"""
import os

import unittest2 as unittest


class TestShippingPackage(unittest.TestCase):
    """Test the :class:`ShipmentConfirm` and :class:`ShipmentAccept` classes
    for various cases originating from GB.
    """

    @classmethod
    def setUpClass(cls):
        """Check if the variables for initialising the test case is available
        in the environment"""
        assert 'UPS_LICENSE_NO' in os.environ, \
            "UPS_LICENSE_NO not given. Hint:Use export UPS_LICENSE_NO=<number>"
        assert 'UPS_SHIPPER_NO' in os.environ, \
            "UPS_SHIPPER_NO not given. Hint:Use export UPS_SHIPPER_NO=<number>"
        assert 'UPS_USER_ID' in os.environ, \
            "UPS_USER_ID not given. Hint:Use export UPS_USER_ID=<user_id>"
        assert 'UPS_PASSWORD' in os.environ, \
            "UPS_PASSWORD not given. Hint:Use export UPS_PASSWORD=<password>"

        #TODO: Create the database
        #TODO: Install the OpenERP Module

    def setUp(self):
        """Load the models
        """
        pass

    @classmethod
    def tearDownClass(cls):
        """Drop the DB
        """
        pass

    def create_settings(self, company):
        """Update the company settings of company ID company

        .. note::

            This is just a helper method

        .. warning::

            A transaction must already be started when calling this method 
        """
        #TODO: Read the settings from os.environ and save it to company


    def test_0010_simple_shipping_gb_gb(self):
        """GB to GB Shipping test"""
        # Initialise a transaction
            # TODO: Call create_settings and update comapny settings
            # Update company address as a from GB address
            # Create a new shipping register record with required address
            # Create the packages
            # Do Confirm and Do Accept and ensure labels are saved.
            #

def suite():
    """Return a reusable suite obj with all the tests"""
    pass


if __name__ == '__main__':
    # Run the tests
    pass
