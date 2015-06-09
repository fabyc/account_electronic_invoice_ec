#! -*- coding: utf8 -*-
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from decimal import Decimal
import barcode
from barcode.writer import ImageWriter
import StringIO
from trytond.model import Workflow, fields, ModelView
from trytond.report import Report
from trytond.pyson import Eval, And
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta


__all__ = ['Invoice', 'ElectronicInvoiceReport']
__metaclass__ = PoolMeta

# GTA = Goverment Tax Authority 
# For example for Ecuador GTA is SRI, for Colombia GTA is DIAN


_STATES = {
    'readonly': Eval('state') != 'draft',
}

_DEPENDS = ['state']

_BILLING_STATES = _STATES.copy()
_BILLING_STATES.update({
        'required': (Eval('pygtaws_concept') == '2')
                    | (Eval('pygtaws_concept') == '3')
})

_POS_STATES = _STATES.copy()
_POS_STATES.update({
        'required': And(
                Eval('type').in_(['out_invoice', 'out_credit_note']), 
                ~Eval('state').in_(['draft'])),
        'invisible': Eval('type').in_(['in_invoice', 'in_credit_note']),
            })

# Default customer GTA for tests:
#    PRUEBAS SERVICIO DE IMPUESTOS


class Invoice:
    __name__ = 'account.invoice'
    pos = fields.Many2One('account.pos', 'Point of Sale', 
        states=_POS_STATES, depends=_DEPENDS)
    electronic_vouchers = fields.One2Many('account.electronic_voucher',
           'invoice', 'Electronic Invoice', readonly=True)
    send_sms = fields.Boolean('Send SMS', states={
            'readonly': True,
            'invisible': Eval('type') != 'out_invoice',
            })
    barcode = fields.Char('Barcode', states={
            'readonly': True,
            })
    barcode_img = fields.Binary('Barcode Image', states={
            'readonly': True,
            })

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls._buttons.update({
            'sri_post': {
                'invisible': ~Eval('state').in_(['draft', 'validated']),
                },
            })
        cls._error_messages.update({
            'missing_pos': 'The Pos is missing or pos sequence.',
            'missing_sequence': 'There is not sequence for invoces type: %s',
            'too_many_sequences':
                'Too many sequences for invoices type: %s',
            'missing_pysriws_billing_date':
                'Debe establecer los valores "Fecha desde" y "Fecha hasta" ' \
                'en el Diario, correspondientes al servicio que se esta facturando',
            'invalid_invoice_number':
                'El numero de la factura (%d), no coincide con el que espera ' \
                'la GTA (%d). Modifique la secuencia del diario',
            'not_cae':
                'No fue posible obtener el CAE. Revise las Transacciones ' \
                'para mas informacion',
            'invalid_journal':
                'Este diario (%s) no tiene establecido los datos necesarios para ' \
                'facturar electronicamente',
            'missing_company_regime_tax': ('The iva condition on company '
                    '"%(company)s" is missing.'),
            'missing_party_regime_tax': ('The iva condition on party '
                    '"%(party)s" is missing.'),
            })
    
    def set_number(self):
        if self.number:
            return
        super(Invoice, self).set_number()

        if self.type == 'out_invoice' or self.type == 'out_credit_note':
            vals = {}
            Sequence = Pool().get('ir.sequence')
            if not self.pos or not self.pos.pos_sequence:
                self.raise_user_error('missing_pos',)
            vals['number'] = Sequence.get_id(self.pos.pos_sequence.id)
            self.write([self], vals)

    @classmethod
    @ModelView.button
    @Workflow.transition('validated')
    def validate_invoice(cls, invoices):
        for invoice in invoices:
            if invoice.type in ('in_invoice', 'in_credit_note'):
                invoice.set_number()
                invoice.create_move()
            else:
                invoice.set_number()
                if not invoice.pos or invoice.pos.pos_type != 'electronic':
                    continue
                response_ok = invoice._create_electronic_voucher()
                if response_ok:
                    print "Response was ok by GTA..."
                    approved = invoice._send_key_gta()
                    if approved:
                        print "Invoice approved por GTA!"
                        invoice._set_barcode()

    def _send_key_gta(self):
        print "sending key to gta..."
        return False

    """
    @classmethod
    @ModelView.button
    @Workflow.transition('posted')
    def post(cls, invoices):
        Move = Pool().get('account.move')

        moves = []
        for invoice in invoices:
            invoice.set_number()
            moves.append(invoice.create_move())
        Move.post(moves)
    """

    def _set_barcode(self):
        if self.type in ('out_invoice', 'out_credit_note'):
            barcode = '9782212110708'
            barcode_img = self._create_img_barcode(barcode)
            self.write([self], {
                'state': 'posted',
                'barcode': barcode,
                'barcode_img': barcode_img,
                })

    def _create_img_barcode(self, number):
        fp = StringIO.StringIO()
        barcode.generate('CODE128', number, writer=ImageWriter(), output=fp)
        img_buffer = fp.getvalue()
        fp.close()
        return img_buffer

    def _create_electronic_voucher(self):
        Evoucher = Pool().get('account.electronic_voucher')
        return Evoucher.create_electronic_voucher(self)

    @classmethod
    def copy(cls, invoices, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['electronic_vouchers'] = []
        return super(Invoice, cls).copy(invoices, default=default)


class ElectronicInvoiceReport(Report):
    __name__ = 'account.electronic_invoice_report'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        User = pool.get('res.user')
        user = User(Transaction().user)
        localcontext['company'] = user.company
        #localcontext['barcode_img'] = cls._get_pysriws_barcode_img(Invoice, invoice)
        """
        #FIXME
        localcontext['condicion_iva'] = cls._get_condicion_iva(user.company)
        localcontext['iibb_type'] = cls._get_iibb_type(user.company)
        localcontext['vat_number'] = cls._get_vat_number(user.company)
        localcontext['tipo_comprobante'] = cls._get_tipo_comprobante(Invoice, invoice)
        localcontext['nombre_comprobante'] = cls._get_nombre_comprobante(Invoice, invoice)
        localcontext['codigo_comprobante'] = cls._get_codigo_comprobante(Invoice, invoice)
        localcontext['condicion_iva_cliente'] = cls._get_condicion_iva_cliente(Invoice, invoice)
        localcontext['vat_number_cliente'] = cls._get_vat_number_cliente(Invoice, invoice)
        localcontext['invoice_impuestos'] = cls._get_invoice_impuestos(Invoice, invoice)
        localcontext['show_tax'] = cls._show_tax(Invoice, invoice)
        localcontext['get_line_amount'] = cls.get_line_amount
        """
        return super(ElectronicInvoiceReport, cls).parse(report, objects,
                data, localcontext=localcontext)

    @classmethod
    def get_line_amount(self, type_voucher, line_amount, line_taxes):
        total = line_amount
        if type_voucher != 'A':
            for tax in line_taxes:
                total = tax.amount + total
        return total

    @classmethod
    def _show_tax(cls, Invoice, invoice):
        tipo_comprobante = cls._get_tipo_comprobante(Invoice, invoice)
        if tipo_comprobante == 'A':
            return True
        else:
            return False

    @classmethod
    def _get_invoice_impuestos(cls, Invoice, invoice):
        tipo_comprobante = cls._get_type_voucher(Invoice, invoice)
        if tipo_comprobante == 'A':
            return invoice.tax_amount
        else:
            return Decimal('00.00')

    @classmethod
    def _get_barcode_image(cls, Invoice, invoice):
        "Generate the required barcode Interleaved of 7 image using PIL"
        if not invoice.gtaws_barcode:
            return
        try:
            import barcode
        except:
            print "Warning: pyBarcode module not found...!"
            return

        EAN = barcode.get_barcode_class('code128')
        ean = EAN(u'9782212110708')

        # create the helper:
        fullname = ean.save('ean128_barcode')
        return fullname
