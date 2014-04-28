from trytond.pool import Pool

from .invoice import *
from .company import *
from .pos import *
from .party import *
from .address import *
from .electronic_voucher import *

def register():
    Pool.register(
        Pos,
        PosSequence,
        Invoice,
        Company,
        SriWsTransaction,
        Party,
        Address,
        ElectronicVoucher,
        module='account_invoice_ar', type_='model')
    Pool.register(
        InvoiceReport,
        module='account_invoice_ar', type_='report')
