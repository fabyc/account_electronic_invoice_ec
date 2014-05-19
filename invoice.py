#! -*- coding: utf8 -*-
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import Workflow, fields, ModelView
from trytond.report import Report
from trytond.pyson import Eval, And
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta


__all__ = ['Invoice', 'InvoiceReport']
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
    invoice_type = fields.Many2One('account.pos.sequence', 'Invoice Type',
        domain=([('pos', '=', Eval('pos'))]), required=False,
        states=_POS_STATES, depends=_DEPENDS)
    electronic_vouchers = fields.One2Many('account.electronic_voucher',
           'invoice', 'Electronic Invoice', readonly=True)

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls._buttons.update({
            'sri_post': {
                'invisible': ~Eval('state').in_(['draft', 'validated']),
                },
            })
        cls._error_messages.update({
            'not_invoice_type': 'The field Type Invoice is required.',
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
                'Este diario (%s) no tiene establecido los datos necesaios para ' \
                'facturar electronicamente',
            'missing_company_regime_tax': ('The iva condition on company '
                    '"%(company)s" is missing.'),
            'missing_party_regime_tax': ('The iva condition on party '
                    '"%(party)s" is missing.'),
            })

    @classmethod
    def validate(cls, invoices):
        super(Invoice, cls).validate(invoices)
        for invoice in invoices:
            invoice.check_invoice_type()

    def check_invoice_type(self):
        pass
        """
        if not self.company.party.regime_tax:
            self.raise_user_error('missing_company_regime_tax', {
                    'company': self.company.rec_name,
                    })
        if not self.party.regime_tax:
            self.raise_user_error('missing_party_regime_tax', {
                    'party': self.party.rec_name,
                    })
        """

    @fields.depends('pos', 'party', 'type', 'company', 'invoice_type')
    def on_change_pos(self, name=None):
        PosSequence = Pool().get('account.pos.sequence')
        if not self.pos:
            return {'invoice_type': None}
        res = {}
        """
        client_iva = None
        company_iva = None
        if self.party:
            client_iva = self.party.regime_tax
        if self.company:
            company_iva = self.company.party.regime_tax

        if company_iva == 'responsable_inscripto':
            if client_iva is None:
                return res
            if client_iva == 'responsable_inscripto':
                kind = 'A'
            elif client_iva == 'consumidor_final':
                kind = 'B'
            elif self.party.vat_country is None:
                self.raise_user_error('unknown_country')
            elif self.party.vat_country == 'EC':
                kind = 'B'
            else:
                kind = 'E'
        else:
            kind = 'C'
        """
        return res

    def set_number(self):
        super(Invoice, self).set_number()

        if self.type == 'out_invoice' or self.type == 'out_credit_note':
            vals = {}
            Sequence = Pool().get('ir.sequence')

            vals['number'] = Sequence.get_id(self.invoice_type.invoice_sequence.id)
            # vals['number'] = '%04d-%08d' % (self.pos.number, int(number))
            self.write([self], vals)

    @classmethod
    @ModelView.button
    @Workflow.transition('posted')
    def post(cls, invoices):
        Move = Pool().get('account.move')

        moves = []
        for invoice in invoices:
            if not invoice.invoice_type:
                invoice.raise_user_error('not_invoice_type')
            if invoice.pos and invoice.pos.pos_type == 'electronic':
                    invoice._create_electronic_voucher()
                    #if not invoice.pysriws_cae:
                    #    invoice.raise_user_error('not_cae')
            invoice.set_number()
            moves.append(invoice.create_move())
        Move.post(moves)
        cls.write(invoices, {
                'state': 'posted',
                })
        for invoice in invoices:
            if invoice.type in ('out_invoice', 'out_credit_note'):
                pass
                #invoice.print_invoice()

    def _create_electronic_voucher(self):
        Evoucher = Pool().get('account.electronic_voucher')
        evoucher = Evoucher.create_electronic_voucher(self)


class InvoiceReport(Report):
    __name__ = 'account.invoice'

    @classmethod
    def parse(cls, report, records, data, localcontext):
        pool = Pool()
        User = pool.get('res.user')
        Invoice = pool.get('account.invoice')

        invoice = records[0]

        user = User(Transaction().user)
        #localcontext['barcode_img'] = cls._get_pysriws_barcode_img(Invoice, invoice)
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
        return super(InvoiceReport, cls).parse(report, records, data,
                localcontext=localcontext)

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
    def _get_pyws_barcode_img(cls, Invoice, invoice):
        "Generate the required barcode Interleaved of 7 image using PIL"
        from pysriws.pyi25 import PyI25
        from cStringIO import StringIO as StringIO
        # create the helper:
        pyi25 = PyI25()
        output = StringIO()
        if not invoice.pysriws_barcode:
            return
        # call the helper:
        bars = ''.join([c for c in invoice.pysriws_barcode if c.isdigit()])
        if not bars:
            bars = "00"
        pyi25.GenerarImagen(bars, output, basewidth=3, width=380, height=50, extension="PNG")
        image = buffer(output.getvalue())
        output.close()
        return image
