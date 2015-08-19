#! -*- coding: utf8 -*-
import os
import logging
import datetime
from decimal import Decimal
from StringIO import StringIO
from lxml import etree, builder
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval
from trytond.pool import Pool
from trytond.transaction import Transaction
from functools import partial


try:
    import bcrypt
except ImportError:
    bcrypt = None


__all__ = ['ElectronicVoucher', 'WsTransaction']

_STATES = {
    'readonly': Eval('state') != 'draft',
}

EVOUCHER_TYPE = {
        'out_invoice': '01',
        'out_credit_note': '04',
        'out_debit_note': '05',
        'reference_guide': '06',
        'withholding': '07',
}

ENVIROMENT_TYPE = [
        ('1', 'Test'),
        ('2', 'Production'),
]

BROADCAST_TYPE_SRI = [
        ('1', 'Normal'),
        ('2', 'Unavailable system'),
]

GTA_CODE_TAX = {
        'IVA': '2',
        'ICE': '3',
        'RETENCION': '4',
}

schemas_dir = os.path.dirname(__file__)
path_schemas = os.path.join(schemas_dir, "schemas")



def fmt2(num):
    return ("%.2f" % float(num))

def fmt6(num):
    return ("%.6f" % float(num))


class ElectronicVoucher(ModelSQL, ModelView):
    'Electronic Voucher'
    __name__ = 'account.electronic_voucher'
    _order_name = 'number'
    number = fields.Char('Number', help='Sequence Document', size=9)
    code = fields.Char('Code', size=8)
    release_date = fields.Date('Release Date', required=True,
        select=True)
    serie = fields.Integer('Serie GTA', required=False, select=True)
    enviroment_type = fields.Selection(ENVIROMENT_TYPE,
        'Enviroment Type', required=False)
    broadcast_type = fields.Selection(BROADCAST_TYPE_SRI, 'Broadcast Type', 
        required=False)
    evoucher_type = fields.Selection(EVOUCHER_TYPE.items(),
        'E-Voucher Type', required=True)
    verification_digit = fields.Integer('Verification Digit', select=True)
    signature_token = fields.Char('Sign Token')
    raw_xml = fields.Text('Xml Request')
    xml_response = fields.Text('Xml Response')
    cache_xml_response = fields.Binary('Cache Xml Response', readonly=True)
    invoice = fields.Many2One('account.invoice', 'Invoice',
            states=_STATES, required=False)
    state = fields.Selection([
           ('draft', 'Draft'),
           ('submitted', 'Submitted'),
           ('rejected', 'Rejected'),
           ('waiting', 'Waiting'),
           ('accepted', 'Accepted'),
       ], 'State', select=True)
    pyws_cae = fields.Char('CAE', readonly=True,
       help="Authorization Code return by GTA")
    pygtaws_barcode = fields.Char('Barcode', readonly=True,)
    authorization_number = fields.Char('Authorization Number', readonly=True)
    authorization_state = fields.Char('Authorization State', readonly=True)
    access_key = fields.Char('Access Key', readonly=True)


    @classmethod
    def __setup__(cls):
        super(ElectronicVoucher, cls).__setup__()
        cls._error_messages.update({
                'missing_tax_group': ('Missing tax group or tax group '
                    'code for tax %s.'),
                'missing_tax_code': ('Missing tax code for '
                    'tax %s.'),
                })

    @staticmethod
    def default_enviroment_type():
        return 1

    @staticmethod
    def default_code():
        return '12345678'

    @classmethod
    def set_token(cls, value):
        logger = logging.getLogger('token')
        logger.info('Token send it...! ')
        if value == 'x' * 10:
            return

    @classmethod
    def _get_serie(cls):
        return '001001'

    @classmethod
    def _get_number(cls, invoice):
        Sequence = Pool().get('ir.sequence')
        seq = Sequence.get_id(invoice.pos.pos_sequence.invoice_sequence.id)
        return seq

    @classmethod
    def _get_raw_sequence(cls, invoice, number):
        Sequence = Pool().get('ir.sequence')
        seq, = Sequence.browse([invoice.pos.pos_sequence.invoice_sequence.id])
        val = number
        if seq.prefix:
            val = number[len(seq.prefix):]
        return val

    @classmethod
    def _get_verification_digit(cls, number):
        "Compute the verification digit - Modulus 11"
        factor = 2
        x = 0
        for n in reversed(number):
            x += int(n) * factor
            factor += 1
            if factor == 8:
                factor = 2
        return (11 - (x % 11))

    @classmethod
    def _get_data_verification_digit(cls, invoice, enviroment_type,
            serie, number, code, broadcast_type):
        evoucher_type = EVOUCHER_TYPE[invoice.type]
        release_date = datetime.datetime.today()
        data = release_date.strftime('%d%m%Y') + \
                evoucher_type + \
                invoice.company.party.vat_number + \
                enviroment_type + \
                serie + \
                number + \
                code + \
                broadcast_type
        return data

    @classmethod
    def create_electronic_voucher(cls, invoice):
        pool = Pool()
        Company = pool.get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            enviroment_type = company.default_enviroment_type
        else:
            enviroment_type = 1

        if invoice.state == 'draft':
            broadcast_type = '1'
        else:
            broadcast_type = '2'

        serie = cls._get_serie()
        number = invoice.number
        raw_number = cls._get_raw_sequence(invoice, number)
        code = cls.default_code()
        full_number = cls._get_data_verification_digit(
                invoice,
                enviroment_type,
                serie,
                raw_number,
                code,
                broadcast_type,
                )
        verification_digit = cls._get_verification_digit(full_number)

        values = {
            'number': number,
            'release_date': invoice.invoice_date,
            'serie': serie,
            'enviroment_type': enviroment_type,
            'broadcast_type': broadcast_type,
            'evoucher_type': invoice.type,
            'verification_digit': verification_digit,
            'state': 'draft',
            'invoice': invoice.id,
        }

        unsigned_xml_invoice = cls.create_xml(invoice, values)
        response = cls.validate_schema(unsigned_xml_invoice)
        print "Is valid schema?: ", response
        if 1: #response:
            signed_invoice = cls.set_sign_invoice(unsigned_xml_invoice)
            vouchers = cls.create([values])
            cls.write(vouchers, {'raw_xml': signed_invoice})
        return response

    @classmethod
    def set_sign_invoice(cls, xml):
        pass

    @classmethod
    def get_password(cls, invoice):
        if invoice.company.private_key:
            return invoice.company.private_key
        return '2103201301000000000000110015010000000101234567811'

    @classmethod
    def get_invoice_line_tax(cls, line, tax, invoice):
        pool = Pool()
        Tax = pool.get('account.tax')

        context = invoice.get_tax_context()

        with Transaction().set_context(**context):
            taxes = Tax.compute([tax], line.unit_price, line.quantity)
        if taxes:
            return taxes[0]['amount']
        else:
            return '0.00'

    @classmethod
    def validate_schema(cls, evoucher):
        factura_xsd = os.path.join(path_schemas, 'factura.xsd')
        xsd_file = open(factura_xsd, 'r')

        xsd_io = StringIO(xsd_file.read())
        xmlschema_doc = etree.parse(xsd_io)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        xsd_file.close()

        evoucher_io = StringIO(evoucher)
        doc = etree.parse(evoucher_io)
        res = xmlschema.validate(doc)
        return res

    @classmethod
    def metaprocess_xml(cls, data):
        E = builder.ElementMaker()
        """
        Parameters
        data :: dict where key is an element and value is a list of elements list
        return :: create
        """
        #field = E.field('azul', name='color')
        #field = partial(E, 'field')('azul', name='color')
        res = []
        for parent, lvalues in data.iteritems():
            for values in lvalues:
                args = []
                for v1, v2 in values:
                    if isinstance(v2, dict):
                        subargs = cls.metaprocess_xml(v2)
                        args.append(partial(E, v1)(*subargs))
                    else:
                        args.append(partial(E, v1)(v2))
                res.append(partial(E, parent)(*args))
        return res

    @classmethod
    def create_xml(cls, invoice, vals):
        head_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        E = builder.ElementMaker()
        #------------ INFOTRIBUTARIA ------------
        street = ''
        if invoice.company.party.addresses[0].street:
            street = invoice.company.party.addresses[0].street
        password = cls.get_password(invoice)
        INFOTRIBUTARIA = {
            'infoTributaria': [
                    [
                    ('ambiente', vals['enviroment_type']),
                    ('tipoEmision', vals['broadcast_type']),
                    ('razonSocial', invoice.company.party.name),
                    ('nombreComercial', invoice.company.party.commercial_name),
                    ('ruc', invoice.company.party.vat_number),
                    ('claveAcceso', password),
                        ('codDoc', EVOUCHER_TYPE[vals['evoucher_type']]),
                    ('estab', invoice.pos.code),
                    ('ptoEmi', invoice.pos.code),
                    ('secuencial', vals['number']),
                    ('dirMatriz', street),
                    ],]
        }

        #------------ INFOFACTURA ------------
        TOTAL_TAXES = {}

        total_taxes  = []
        total_withholdings  = []
        total_with_taxes = Decimal(0)
        
        ret_used_codes = []
        default_ret_codes = ['327', '328', '3']

        for invoice_tax in invoice.taxes:

            if not invoice_tax.tax.group or not invoice_tax.tax.group.code:
                cls.raise_user_error('missing_tax_group', invoice_tax.tax.name)
            if not invoice_tax.tax_code or not invoice_tax.tax_code.code:
                cls.raise_user_error('missing_tax_code', invoice_tax.tax.name)

            if invoice_tax.tax.group.code == GTA_CODE_TAX['IVA']:
                total_taxes.append([
                    ('codigo', invoice_tax.tax.group.code),
                    ('codigoPorcentaje', invoice_tax.tax_code.code),
                    ('baseImponible', fmt2(invoice_tax.base)),
                    ('valor', fmt2(invoice_tax.amount)),
                ])
            
            if invoice_tax.tax.group.code == GTA_CODE_TAX['RETENCION']:
                total_withholdings.append([
                    ('codigo', invoice_tax.tax.group.code),
                    ('codigoPorcentaje', invoice_tax.tax_code.code),
                    ('tarifa', fmt2(invoice_tax.tax.rate * 100)),
                    ('valor', fmt2(invoice_tax.amount)),
                ])
                ret_used_codes.append(invoice_tax.tax.group.code)

            if invoice_tax.tax.group.code == GTA_CODE_TAX['ICE']:
                pass
            total_with_taxes += invoice_tax.amount

        for ret_code in set(default_ret_codes) - set(ret_used_codes):
            total_withholdings.append([
                    ('codigo', '4'),
                    ('codigoPorcentaje', ret_code),
                    ('tarifa', fmt2(0)),
                    ('valor', fmt2(0)),
                ])

        #------------ DETALLES ------------
        detalles = []
        for line in invoice.lines:
            line_taxes = []
            for tax in line.taxes:
                if not tax.group.code == GTA_CODE_TAX['IVA']:
                    continue
                tax_amount = cls.get_invoice_line_tax(line, tax, invoice)
                line_taxes.append([
                    ('codigo', tax.group.code),
                    ('codigoPorcentaje', tax.invoice_tax_code.code),
                    ('tarifa', fmt2(tax.rate * 100)),
                    ('baseImponible', fmt2(line.amount)),
                    ('valor', fmt2(tax_amount)),
                ])
            total_with_taxes += line.amount
            descuento = fmt2(0)
            detalles.append([
                ('codigoPrincipal', line.product.code),
                ('descripcion', line.product.name),
                ('cantidad', fmt6(line.quantity)),
                ('precioUnitario', fmt6(line.unit_price)),
                ('descuento', descuento),
                ('precioTotalSinImpuesto', fmt2(line.amount)),
                ('impuestos', {'impuesto': line_taxes}),
                ])
        DETALLE = {'detalle': detalles}

        #------------ RETENCIONES ------------
        RETENCIONES = {'retencion': total_withholdings}


        #------------ INFOADICIONAL ------------
        INFOAD = []
        if invoice.party.addresses[0].street:
            INFOAD.append(E.campoAdicional(
                invoice.party.addresses[0].street,
                nombre='Direccion',
                ))
        if invoice.party.email:
            INFOAD.append(E.campoAdicional(
                    invoice.party.email,
                    nombre='Email',
                    ))

        TOTAL_TAXES['totalImpuesto'] = total_taxes
        tip = Decimal(0)
        importeTotal = total_with_taxes + tip
        totalDescuento = fmt2(0)
        INFOFACTURA = {
            'infoFactura': [[
                    ('fechaEmision', vals['release_date'].strftime('%d/%m/%Y')),
                    ('dirEstablecimiento', street),
                    ('contribuyenteEspecial', '12345'),
                    ('obligadoContabilidad', invoice.party.mandatory_accounting.upper()),
                    ('tipoIdentificacionComprador', invoice.party.type_document),
                    ('razonSocialComprador', invoice.party.name),
                    ('identificacionComprador', invoice.party.vat_number),
                    ('totalSinImpuestos', fmt2(invoice.untaxed_amount)),
                    ('totalDescuento', totalDescuento),
                    ('totalConImpuestos', TOTAL_TAXES),
                    ('propina', fmt2(tip)),
                    ('importeTotal', fmt2(importeTotal)),
                    ('moneda', 'DOLAR'),
                ],]
        }

        infoTributaria_ = cls.metaprocess_xml(INFOTRIBUTARIA)[0]
        infoFactura_ = cls.metaprocess_xml(INFOFACTURA)[0]
        infoAdicional_ = E.infoAdicional(*INFOAD)
        detalles_ = E.detalles(*cls.metaprocess_xml(DETALLE))
        retenciones_ = E.retenciones(*cls.metaprocess_xml(RETENCIONES))

        evoucher = E.factura(
                infoTributaria_,
                infoFactura_,
                detalles_,
                retenciones_,
                infoAdicional_,
                id="comprobante", version="1.1.2",
        )
        body = etree.tostring(evoucher, pretty_print=True)
        return (head_xml + body)

    def do_request_ws(self):
        pass


class WsTransaction(ModelSQL, ModelView):
    'GTA Ws Transaction'
    __name__ = 'account.sri_transaction'
    pysriws_result = fields.Selection([
           ('', 'N.A.'),
           ('G', 'Generado'),
           ('F', 'Firmado'),
           ('A', 'Autorizado'),
           ('N', 'No Autorizado'),
       ], 'Result', readonly=True,
       help="Result of processing request return by GTA")
    pysriws_message = fields.Text('Message', readonly=True,
       help="Message returned by GTA")
    pysriws_xml_request = fields.Text('Requerimiento XML', readonly=True,
       help="Message XML send by GTA (debugger)")
    pysriws_xml_response = fields.Text('Response XML', readonly=True,
       help="Message XML received de GTA (debugger)")
    invoice = fields.Many2One('account.electronic_voucher', 'Electronic Voucher')
