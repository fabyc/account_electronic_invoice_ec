from trytond.pool import Pool

from .invoice import *
from .company import *
from .pos import *
from .address import *
from .electronic_voucher import *

def register():
    Pool.register(
        Address,
        Company,
        Pos,
        PosSequence,
        Invoice,
        ElectronicVoucher,
        WsTransaction,
        module='account_electronic_invoice_ec', type_='model')
    Pool.register(
        InvoiceReport,
        module='account_electronic_invoice_ec', type_='report')
