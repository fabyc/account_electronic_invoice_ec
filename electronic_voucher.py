#! -*- coding: utf8 -*-
import lxml.etree
import lxml.builder

from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval
from trytond.pool import Pool

try:
    import bcrypt
except ImportError:
    bcrypt = None


__all__ = ['ElectronicVoucher']

VOUCHER_TYPE_SRI = {
        'out_invoice': '01',
        'out_credit_note': '04',
        'out_debit_note': '05',
        'reference_guide': '06',
        'withholding': '07',
        }

ENVIROMENT_TYPE_SRI = [
        ('1', 'Test'),
        ('2', 'Production'),
]

BROADCAST_TYPE_SRI = [
        ('1', 'Normal'),
        ('2', 'Indisponibilidad del Sistema'),
]

class ElectronicVoucher(ModelSQL, ModelView):
    'Electronic Voucher'
    __name__ = 'account.electronic_voucher'
    number = fields.Char('Reference', help='Sequence Document', size=9)
    release_date = fields.Date('Release Date', required=True,
        select=True)
    serie = fields.Integer('Serie SRI', size=6, required=True)
    enviroment_type = fields.Selection(ENVIROMENT_TYPE_SRI,
        'Enviroment Type', required=False)
    broadcast_type = fields.Selection(BROADCAST_TYPE_SRI, 'Broadcast Type', 
        required=False)
    evoucher_type = fields.Selection(VOUCHER_TYPE_SRI, 'E-Voucher Type',
        required=True)
    check_digit = fields.Integer('Check Digit', size=1)
    signature_token = fields.Char('Sign Token')
    xml_file = fields.Binary('Xml File')
    state = fields.Selection([
           ('draft', 'Draft'),
           ('submitted', 'Submitted'),
           ('rejected', 'Rejected'),
           ('waiting', 'Waiting'),
           ('accepted', 'Accepted'),
       ], 'State', select=True)

    @classmethod
    def set_token(cls, value):
        if value == 'x' * 10:
            return
        to_write = []
        for company in companies:
            to_write.extend([[company], {
                        'signature_token': cls.hash_password(value),
                        }])
        cls.write(*to_write)

    """
    @classmethod
    def get_name(cls, account_electronic_voucher, name):
        res = {}
        for electronic_voucher in cls.browse(account_electronic_voucher):
            res[electronic_voucher.id] = str(electronic_voucher.number)+ ' - '+\
            dict(electronic_voucher.fields_get(fields_names=['electronic_voucher_type'])\
            ['electronic_voucher_type']['selection'])[electronic_voucher.electronic_voucher_type]
        return res


class ElectronicVoucherSequence(ModelSQL, ModelView):
    'Point of Sale Sequences'
    __name__ = 'account.electronic_voucher.sequence'

    electronic_voucher = fields.Many2One('account.electronic_voucher', 'Point of Sale')
    invoice_type = fields.Selection([
            ('', ''),
            ('1', u'Factura A'),
            ('2', u'Nota de Débito A'),
            ('3', u'Nota de Crédito A'),
            ('4', u'Recibos A'),
            ], 'Tipo Comprobante SRI', required=True,
        help="Tipo de Comprobante SRI")
    invoice_sequence = fields.Property(fields.Many2One('ir.sequence',
            'Sequence', required=True,
            domain=[('code', '=', 'account.invoice')],
            context={'code': 'account.invoice'}))

    def get_rec_name(self, name):
        type2name = {}
        for type, name in self.fields_get(fields_names=['invoice_type']
                )['invoice_type']['selection']:
            type2name[type] = name
        return type2name[self.invoice_type][3:]
    """
