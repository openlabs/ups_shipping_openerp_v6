#-*- coding: utf-8 -*-
#    UPS Shipping Integration
#        
#    :copyright: (c) 2010-2011, Open Labs Business Solution
#    :copyright: (c) 2011 by Openlabs Technologies & Consulting (P) Ltd.
#    
#    :license: AGPL, see LICENSE for more details.
{
    'name': 'Shipping Integration with UPS',
    'version': '1.0.1',
    'author': '''Open Labs Business Solutions,
        Openlabs Technologies & Consulting (P) Ltd.''',
    'website': 'http://openlabs.co.in',
    'category': 'Customised Modules',
    'depends': [
                 "base",
                 "stock",
                 ],
    'init_xml': [],
    'demo_xml': [],
    'description': """
    Integrates United Parcel Service of America Shipping services
    = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
    Features:
      1. Allows shipping records to be created within Open ERP
      2. Fetches rates and billed quantity for the same
      3. On confirmation the images for label are fetched
      4. Integrated with stock picking for easy generation
         directly from stock

    """,
    'update_xml': [
                   'company_view.xml',
                   'shipping_register_view.xml',
                   'stock_view.xml',
                   'shipment_sequence.xml',
                   'product_view.xml',
                   'data/ups.codes.csv',
                   'security/ir.model.access.csv',
                ],
    'installable': True,
    'active': False,
}
