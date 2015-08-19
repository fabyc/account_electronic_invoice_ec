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
            ], 'Pos Type')

    @classmethod
    def __setup__(cls):
        super(Pos, cls).__setup__()
        cls._sql_constraints += [
            ('pos_sequence', 'UNIQUE(pos_sequence)',
                'Pos Sequence is already used by another POS!'),
        ]


class PosSequence(ModelSQL, ModelView):
    'Point of Sale Sequences'
    __name__ = 'account.pos.sequence'
    _rec_name = 'name'
    name = fields.Char('Name', required=False)
    invoice_type = fields.Selection(EVOUCHER_TYPE.items(),
        'Invoice Type', required=True)
    invoice_sequence = fields.Property(fields.Many2One('ir.sequence',
            'Sequence', required=True,
            domain=[('code', '=', 'account.invoice')],
            context={'code': 'account.invoice'}))

    @classmethod
    def __setup__(cls):
        super(PosSequence, cls).__setup__()
