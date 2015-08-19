from trytond.pool import Pool

from .invoice import *
from .company import *
from .sale import *
from .pos import *
from .electronic_voucher import *

def register():
    Pool.register(
        Company,
        PosSequence,
        Pos,
        Invoice,
        ElectronicVoucher,
        WsTransaction,
        AddKeysStart,
        Sale,
        module='account_electronic_invoice_ec', type_='model')
    Pool.register(
        ElectronicInvoiceReport,
        module='account_electronic_invoice_ec', type_='report')
    Pool.register(
        AddKeys,
        module='account_electronic_invoice_ec', type_='wizard')
