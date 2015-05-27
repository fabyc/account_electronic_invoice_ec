from trytond.pool import Pool

from .invoice import *
from .company import *
from .sale import *
from .pos import *
from .address import *
from .electronic_voucher import *
from .contingency_keys import *

def register():
    Pool.register(
        Company,
        PosSequence,
        Pos,
        Invoice,
        ElectronicVoucher,
        WsTransaction,
        ContingencyKeys,
        Sale,
        module='account_electronic_invoice_ec', type_='model')
    Pool.register(
        ElectronicInvoiceReport,
        module='account_electronic_invoice_ec', type_='report')
