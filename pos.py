#! -*- coding: utf8 -*-

from trytond.model import ModelView, ModelSQL, fields

__all__ = ['Pos', 'PosSequence']

EVOUCHER_TYPE = {
        'out_invoice': 'Out Invoice',
        'out_credit_note': 'Credit Note',
        'out_debit_note': 'Debit Note',
        'reference_guide': 'Reference Guide',
        'withholding': 'Withholding',
}


class Pos(ModelSQL, ModelView):
    'Point of Sale'
    __name__ = 'account.pos'
    name = fields.Char('Name', required=True)
    code = fields.Char('Point of Sale GTA', required=False,
        help="Sequence of Point of Sale location for GTA")
    pos_sequence = fields.Many2One('account.pos.sequence', 
        'Point of Sale Sequence', select=True)
    pos_type = fields.Selection([
            ('manual', 'Manual'),
            ('electronic', 'Electronic'),
            ('fiscal_printer', 'Fiscal Printer'),
            ], 'Pos Type')

    @classmethod
    def __setup__(cls):
        super(Pos, cls).__setup__()
        cls._sql_constraints += [
            ('pos_sequence', 'UNIQUE(pos_sequence)',
                'Pos Sequence is already used by another POS!'),
        ]

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
    _rec_name = 'invoice_type'
    invoice_type = fields.Selection(EVOUCHER_TYPE.items(),
        'Invoice Type', required=True)
    invoice_sequence = fields.Property(fields.Many2One('ir.sequence',
            'Sequence', required=True,
            domain=[('code', '=', 'account.invoice')],
            context={'code': 'account.invoice'}))

    @classmethod
    def __setup__(cls):
        super(PosSequence, cls).__setup__()

    def get_rec_name(self, name):
        type2name = {}
        for type, name in self.fields_get(fields_names=['invoice_type']
                )['invoice_type']['selection']:
            type2name[type] = name
        return type2name[self.invoice_type][3:]
