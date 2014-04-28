#! -*- coding: utf8 -*-

from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval
from trytond.pool import Pool

__all__ = ['Pos', 'PosSequence']


class Pos(ModelSQL, ModelView):
    'Point of Sale'
    __name__ = 'account.pos'
    name = fields.Function(fields.Char('Name'), 'get_name')
    number = fields.Integer('Punto de Venta SRI', required=True,
        help=u"Prefijo de emisión habilitado en SRI")
    pos_sequences = fields.One2Many('account.pos.sequence', 'pos',
        'Point of Sale')
    pos_type = fields.Selection([
            ('manual', u'Manual'),
            ('electronic', u'Electronic'),
            ('fiscal_printer', u'Fiscal Printer'),
            ], 'Pos Type')
    """
    pysriws_electronic_invoice_service = fields.Selection([
            ('', ''),
            ('wsfe', u'Mercado interno -sin detalle- RG2485 (WSFEv1)'),
            ('wsmtxca',u'Mercado interno -con detalle- RG2904 (WSMTXCA)'),
            ('wsbfe', u'Bono Fiscal -con detalle- RG2557 (WSMTXCA)'),
            ('wsfex', u'Exportación -con detalle- RG2758 (WSFEXv1)'),
        ], u'SRI Web Service',
        states={
            'invisible': Eval('pos_type') != 'electronic',
            'required': Eval('pos_type') == 'electronic',
            }, depends=['pos_type'],
        help=u"Habilita la facturación electrónica por webservices SRI")

    @staticmethod
    def default_pos_type():
        return 'manual'

    @classmethod
    def get_name(cls, account_pos, name):
        res = {}
        for pos in cls.browse(account_pos):
            res[pos.id] = str(pos.number)+ ' - '+\
            dict(pos.fields_get(fields_names=['pos_type'])\
            ['pos_type']['selection'])[pos.pos_type]
        return res
    """

class PosSequence(ModelSQL, ModelView):
    'Point of Sale Sequences'
    __name__ = 'account.pos.sequence'
    pos = fields.Many2One('account.pos', 'Point of Sale')
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
