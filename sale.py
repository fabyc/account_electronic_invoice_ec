#This file is part of Tryton.  The COPYRIGHT file at the top level
#of this repository contains the full copyright notices and license terms.
import datetime
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['Sale']
__metaclass__ = PoolMeta



class Sale:
    __name__ = 'sale.sale'
    pos = fields.Many2One('account.pos', 'Point of Sale',
        states={'readonly': Eval('state') != 'draft'})

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()

    def _get_invoice_sale(self, invoice_type):
        new_invoice = super(Sale, self)._get_invoice_sale(invoice_type)
        if self.pos:
            new_invoice.pos = self.pos
            new_invoice.invoice_type = self.pos.pos_sequence
        if self.sale_date:
            new_invoice.invoice_date = self.sale_date
        else:
            new_invoice.invoice_date = datetime.date.today()
        return new_invoice
