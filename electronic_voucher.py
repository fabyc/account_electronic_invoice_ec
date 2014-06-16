#! -*- coding: utf8 -*-
import logging
import lxml
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval
from trytond.pool import Pool
from trytond.transaction import Transaction
import lxml.builder
from functools import partial
#from builder import metaprocess_xml

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

def fmt(num):
    return str(round(num, 2))

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
    raw_xml = fields.Text('Xml File')
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
    """
    pysriws_cae_due_date = fields.Date('Vencimiento CAE', readonly=True,
       help="Date limit for verification CAE, returned by GTA")
    pysriws_barcode = fields.Char('Barcode', readonly=True,)
    pysriws_number = fields.Char('Number', readonly=True,
            help="Invoice Number send to GTA")
    """

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
        #to_write = []
        """
        for company in companies:
            to_write.extend([[company], {
                        'signature_token': cls.hash_password(value),
                        }])
        cls.write(*to_write)
        """

    @classmethod
    def _get_serie(cls):
        return '001001'

    @classmethod
    def _get_number(cls, invoice):
        Sequence = Pool().get('ir.sequence')
        seq = Sequence.get_id(invoice.pos.pos_sequence.invoice_sequence.id)
        print seq
        return seq

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

    def _get_data_verification_digit(self):
        evoucher_type = EVOUCHER_TYPE[self.evoucher_type]
        data = self.release_date.strftime('%d%m%Y') + \
                evoucher_type + \
                self.invoice.company.vat_number + \
                self.enviroment_type + \
                self.serie + \
                self.number + \
                self.code + \
                self.broadcast_type
        return '41261533'

    @classmethod
    def create_electronic_voucher(cls, invoice):
        pool = Pool()
        Company = pool.get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            enviroment_type = company.default_enviroment_type
        else:
            enviroment_type = 1

        serie = cls._get_serie()
        number = cls._get_number(invoice)
        verification_digit = cls._get_verification_digit('41261533')

        # TODO: FIXME
        if invoice.state == 'draft':
            broadcast_type = '1'
        else:
            broadcast_type = '2'

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
        vouchers = cls.create([values])
        for voucher in vouchers:
            val = {'raw_xml': voucher.create_xml(invoice)}
            voucher.write([voucher], val)

    def get_password(self):
        if self.invoice.company.gta_private_key:
            return self.invoice.company.gta_private_key
        return '00000000000'

    def get_invoice_line_tax(self, line, tax):
        pool = Pool()
        Tax = pool.get('account.tax')

        if not self.invoice:
            return
        context = self.invoice.get_tax_context()

        with Transaction().set_context(**context):
            taxes = Tax.compute([tax], line.unit_price, line.quantity)
        if taxes:
            return taxes[0]['amount']
        else:
            return '0.00'

    def metaprocess_xml(self, data):
        E = lxml.builder.ElementMaker()
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
                        subargs = self.metaprocess_xml(v2)
                        args.append(partial(E, v1)(*subargs))
                    else:
                        args.append(partial(E, v1)(v2))
                res.append(partial(E, parent)(*args))
        return res

    def create_xml(self, invoice):
        E = lxml.builder.ElementMaker()
        #------------ INFOTRIBUTARIA ------------
        street = ''
        if invoice.company.party.addresses[0].street:
            street = invoice.company.party.addresses[0].street
        password = self.get_password()
        INFOTRIBUTARIA = {
            'infoTributaria': [
                    [
                    ('ambiente', self.enviroment_type),
                    ('tipoEmision', self.broadcast_type),
                    ('razonSocial', self.invoice.company.party.name),
                    ('nombreComercial', self.invoice.company.party.commercial_name),
                    ('ruc',  self.invoice.company.party.vat_number),
                    ('claveAcceso', password),
                        ('codDoc', self.evoucher_type),
                    ('estab', self.invoice.pos.code),
                    ('ptoEmi', self.invoice.pos.code),
                    ('secuencial', self.number),
                    ('dirMatriz', street),
                    ],]
        }

        #------------ INFOFACTURA ------------
        TOTAL_TAXES = {}

        total_taxes  = []
        total_withholdings  = []

        for invoice_tax in invoice.taxes:

            if not invoice_tax.tax.group or not invoice_tax.tax.group.code:
                self.raise_user_error('missing_tax_group', invoice_tax.tax.name)
            if not invoice_tax.tax_code or not invoice_tax.tax_code.code:
                self.raise_user_error('missing_tax_code', invoice_tax.tax.name)

            if invoice_tax.tax.group.code == GTA_CODE_TAX['IVA']:
                total_taxes.append([
                    ('codigo', invoice_tax.tax.group.code),
                    ('codigoPorcentaje', invoice_tax.tax_code.code),
                    ('baseImponible', fmt(invoice_tax.base)),
                    ('valor', fmt(invoice_tax.amount)),
                ])
            elif invoice_tax.tax.group.code == GTA_CODE_TAX['RETENCION']:
                total_withholdings.append([
                    ('codigo', invoice_tax.tax.group.code),
                    ('codigoPorcentaje', invoice_tax.tax_code.code),
                    ('tarifa', fmt(invoice_tax.tax.rate * 100)),
                    ('valor', fmt(invoice_tax.amount)),
                ])
            elif invoice_tax.tax.group.code == GTA_CODE_TAX['ICE']:
                pass

        TOTAL_TAXES['totalImpuesto'] = total_taxes

        INFOFACTURA = {
            'infoFactura': [[
                    ('fechaEmision', str(self.invoice.invoice_date)),
                    ('dirEstablecimiento', street),
                    ('contribuyenteEspecial', '12345'),
                    ('obligadoContabilidad', self.invoice.party.mandatory_accounting),
                    ('tipoIdentificacionComprador', self.invoice.party.type_document),
                    ('razonSocialComprador', self.invoice.party.name),
                    ('identificacionComprador', self.invoice.party.vat_number),
                    ('totalSinImpuestos', fmt(invoice.untaxed_amount)),
                    ('totalDescuento', '0.00'),
                    ('totalConImpuestos', TOTAL_TAXES),
                    ('propina','0.00'),
                    ('moneda', 'DOLAR'),
                ],]
        }

        #------------ DETALLES ------------
        detalles = []
        for line in invoice.lines:
            line_taxes = []
            for tax in line.taxes:
                if not tax.group.code == GTA_CODE_TAX['IVA']:
                    continue
                tax_amount = self.get_invoice_line_tax(line, tax)
                line_taxes.append([
                    ('codigo', tax.group.code),
                    ('codigoPorcentaje', tax.invoice_tax_code.code),
                    ('tarifa', fmt(tax.rate*100)),
                    ('baseImponible', fmt(line.amount)),
                    ('valor', fmt(tax_amount)),
                ])
            discount = '0.00'
            detalles.append([
                ('codigoPrincipal', line.product.code),
                ('descripcion', line.product.name),
                ('cantidad', fmt(line.quantity)),
                ('precioUnitario', str(line.unit_price)),
                ('descuento', discount),
                ('precioTotalSinImpuesto', fmt(line.amount)),
                ('impuestos', {'impuesto': line_taxes}),
                ])
        DETALLE = {'detalle': detalles}

        #------------ RETENCIONES ------------
        RETENCIONES = {'retencion': total_withholdings}


        #------------ INFOADICIONAL ------------
        INFOAD = []
        if self.invoice.party.addresses[0].street:
            INFOAD.append(E.campoAdicional(
                self.invoice.party.addresses[0].street,
                nombre='Direccion',
                ))
        if self.invoice.party.email:
            INFOAD.append(E.campoAdicional(
                    self.invoice.party.email,
                    nombre='Email',
                    ))

        infoTributaria_ = self.metaprocess_xml(INFOTRIBUTARIA)[0]
        infoFactura_ = self.metaprocess_xml(INFOFACTURA)[0]
        infoAdicional_ = E.infoAdicional(*INFOAD)
        detalles_ = E.detalles(*self.metaprocess_xml(DETALLE))
        retenciones_ = E.retenciones(*self.metaprocess_xml(RETENCIONES))

        evoucher = E.factura(
                infoTributaria_,
                infoFactura_,
                detalles_,
                retenciones_,
                infoAdicional_,
        )
        data = lxml.etree.tostring(evoucher, pretty_print=True)
        return data

    def do_request_ws(self):
        logger = logging.getLogger('py_ws')
        "Request to GTA the invoices' Authorization Electronic Code (CAE)"
        # if already authorized (electronic invoice with CAE), ignore
        """
        for evoucher in electronic_vouchers:
            
        if self.pyws_cae:
            logger.info('You try to get a CAE invoice, that already it have.'\
                        'Invoice: %s, CAE: %s', self.number, self.pyws_cae)
            return
        """
        # get the electronic invoice type, point of sale and service:
        pool = Pool()
        Company = pool.get('company.company')
        company_id = Transaction().context.get('company')
        if not company_id:
            logger.info('There is not company!')
            return

        company = Company(company_id)
        tipo_cbte = self.invoice_type.invoice_type
        punto_vta = self.pos.number
        service = self.pos.pysriws_electronic_invoice_service
        # check if it is an electronic invoice sale point:
        ##TODO
        #if not tipo_cbte:
        #    self.raise_user_error('invalid_sequence', pos.invoice_type.invoice_type)

        # authenticate against GTA:
        auth_data = company.pysriws_authenticate(service=service)

        # import the GTA webservice helper for electronic invoice
        if service == 'wsfe':
            from pysriws.wsfev1 import WSFEv1  # local market
            ws = WSFEv1()
        #elif service == 'wsmtxca':
        #    from pysriws.wsmtx import WSMTXCA, SoapFault   # local + detail
        #    ws = WSMTXCA()
        elif service == 'wsfex':
            from pysriws.wsfexv1 import WSFEXv1 # foreign trade
            ws = WSFEXv1()
        else:
            logger.critical('WS not supported: %s', service)
            return

        # connect to the webservice and call to the test method
        ws.Conectar()
        # set GTA webservice credentials:
        ws.Cuit = company.party.vat_number
        ws.Token = auth_data['token']
        ws.Sign = auth_data['sign']
        #ws.LanzarExcepciones = True

        # get the last 8 digit of the invoice number
        if self.move:
            cbte_nro = int(self.move.number[-8:])
        else:
            Sequence = pool.get('ir.sequence')
            cbte_nro = int(Sequence(
                self.invoice_type.invoice_sequence.id).get_number_next(''))

        # get the last invoice number registered in GTA
        if service == "wsfe" or service == "wsmtxca":
            cbte_nro_sri = ws.CompUltimoAutorizado(tipo_cbte, punto_vta)
        elif service == 'wsfex':
            cbte_nro_sri = ws.GetLastCMP(tipo_cbte, punto_vta)
        cbte_nro_next = int(cbte_nro_sri or 0) + 1
        # verify that the invoice is the next one to be registered in GTA
        if cbte_nro != cbte_nro_next:
            self.raise_user_error('invalid_invoice_number', (cbte_nro, cbte_nro_next))

        # invoice number range (from - to) and date:
        cbte_nro = cbt_desde = cbt_hasta = cbte_nro_next

        if self.invoice_date:
            fecha_cbte = self.invoice_date.strftime("%Y-%m-%d")
        else:
            Date = pool.get('ir.date')
            fecha_cbte = Date.today().strftime("%Y-%m-%d")

        if service != 'wsmtxca':
            fecha_cbte = fecha_cbte.replace("-", "")

        # due and billing dates only for concept "services"
        concepto = tipo_expo = int(self.pysriws_concept or 0)
        if int(concepto) != 1:

            payments = self.payment_term.compute(self.total_amount, self.currency)
            last_payment = max(payments, key=lambda x:x[0])[0]
            fecha_venc_pago = last_payment.strftime("%Y-%m-%d")
            if service != 'wsmtxca':
                    fecha_venc_pago = fecha_venc_pago.replace("-", "")
            if self.pysriws_billing_start_date:
                fecha_serv_desde = self.pysriws_billing_start_date.strftime("%Y-%m-%d")
                if service != 'wsmtxca':
                    fecha_serv_desde = fecha_serv_desde.replace("-", "")
            else:
                fecha_serv_desde = None
            if  self.pysriws_billing_end_date:
                fecha_serv_hasta = self.pysriws_billing_end_date.strftime("%Y-%m-%d")
                if service != 'wsmtxca':
                    fecha_serv_hasta = fecha_serv_hasta.replace("-", "")
            else:
                fecha_serv_hasta = None
        else:
            fecha_venc_pago = fecha_serv_desde = fecha_serv_hasta = None

        # customer tax number:
        if self.party.vat_number:
            nro_doc = self.party.vat_number
            if len(nro_doc) < 11:
                tipo_doc = 96           # DNI
            else:
                tipo_doc = 80           # CUIT
        else:
            nro_doc = "0"           # only "consumidor final"
            tipo_doc = 99           # consumidor final

        # invoice amount totals:
        imp_total = str("%.2f" % abs(self.total_amount))
        imp_tot_conc = "0.00"
        imp_neto = str("%.2f" % abs(self.untaxed_amount))
        imp_iva = str("%.2f" % abs(self.tax_amount))
        imp_subtotal = imp_neto  # TODO: not allways the case!
        imp_trib = "0.00"
        imp_op_ex = "0.00"
        if self.currency.code == 'ECP':
            moneda_id = "PES"
            moneda_ctz = 1
        else:
            moneda_id = {'USD':'DOL'}[self.currency.code]
            moneda_ctz = str(self.currency.rate)

        # foreign trade data: export permit, country code, etc.:
        #if invoice.pysriws_incoterms:
        #    incoterms = invoice.pysriws_incoterms.code
        #    incoterms_ds = invoice.pysriws_incoterms.name
        #else:
        #    incoterms = incoterms_ds = None
        if int(tipo_cbte) == 19 and tipo_expo == 1:
            permiso_existente =  "N" or "S"     # not used now
        else:
            permiso_existente = ""
        obs_generales = self.comment
        if self.payment_term:
            payment_term = self.payment_term.name
            obs_comerciales = self.payment_term.name
        else:
            payment_term = obs_comerciales = None
        idioma_cbte = 1     # invoice language: spanish / español

        # customer data (foreign trade):
        customer_name = self.party.name
        if self.party.vat_number:
            if self.party.vat_country == "EC":
                # use the Ecuador GTA's global CUIT for the country:
                cuit_customer_country = self.party.vat_number
                id_impositivo = None
            else:
                # use the VAT number directly
                id_impositivo = self.party.vat_number
                # TODO: the prefix could be used to map the customer country
                cuit_customer_country = None
        else:
            cuit_customer_country = id_impositivo = None
        if self.invoice_address:
            address = self.invoice_address
            customer_address = " - ".join([
                                        address.name or '',
                                        address.street or '',
                                        address.streetbis or '',
                                        address.zip or '',
                                        address.city or '',
                                ])
        else:
            customer_address = ""
        if self.invoice_address.country:
            # map ISO country code to GTA destination country code:
            pais_dst_cmp = {
                'ar': 200, 'bo': 202, 'br': 203, 'ca': 204, 'co': 205,
                'cu': 207, 'cl': 208, 'ec': 210, 'us': 212, 'mx': 218,
                'py': 221, 'pe': 222, 'uy': 225, 've': 226, 'cn': 310,
                'tw': 313, 'in': 315, 'il': 319, 'jp': 320, 'at': 405,
                'be': 406, 'dk': 409, 'es': 410, 'fr': 412, 'gr': 413,
                'it': 417, 'nl': 423, 'pt': 620, 'uk': 426, 'sz': 430,
                'de': 438, 'ru': 444, 'eu': 497,
                }[self.invoice_address.country.code.lower()]


        # create the invoice internally in the helper
        """
        if service == 'wsfe':
            ws.CrearFactura(concepto, tipo_doc, nro_doc, tipo_cbte, punto_vta,
                cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
                imp_iva, imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
                fecha_serv_desde, fecha_serv_hasta,
                moneda_id, moneda_ctz)
        elif service == 'wsmtxca':
            ws.CrearFactura(concepto, tipo_doc, nro_doc, tipo_cbte, punto_vta,
                cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
                imp_subtotal, imp_trib, imp_op_ex, fecha_cbte,
                fecha_venc_pago, fecha_serv_desde, fecha_serv_hasta,
                moneda_id, moneda_ctz, obs_generales)
        elif service == 'wsfex':
            ws.CrearFactura(tipo_cbte, punto_vta, cbte_nro, fecha_cbte,
                imp_total, tipo_expo, permiso_existente, pais_dst_cmp,
                customer_name, cuit_customer_country, customer_address,
                id_impositivo, moneda_id, moneda_ctz, obs_comerciales,
                obs_generales, payment_term, incoterms,
                idioma_cbte, incoterms_ds)

        # analyze VAT (IVA) and other taxes:
        if service in ('wsfe', 'wsmtxca'):
            for tax_line in self.taxes:
                tax = tax_line.tax
                if tax.group.name == "IVA":
                    iva_id = IVA_GTA_CODE[tax.rate]
                    base_imp = ("%.2f" % abs(tax_line.base))
                    importe = ("%.2f" % abs(tax_line.amount))
                    # add the vat detail in the helper
                    ws.AgregarIva(iva_id, base_imp, importe)
                else:
                    if 'impuesto' in tax_line.tax.name.lower():
                        tributo_id = 1  # nacional
                    elif 'iibbb' in tax_line.tax.name.lower():
                        tributo_id = 3  # provincial
                    elif 'tasa' in tax_line.tax.name.lower():
                        tributo_id = 4  # municipal
                    else:
                        tributo_id = 99
                    desc = tax_line.name
                    base_imp = ("%.2f" % abs(tax_line.base))
                    importe = ("%.2f" % abs(tax_line.amount))
                    alic = "%.2f" % tax_line.base
                    # add the other tax detail in the helper
                    ws.AgregarTributo(tributo_id, desc, base_imp, alic, importe)

        # analize line items - invoice detail
        if service in ('wsfex', 'wsmtxca'):
            for line in self.lines:
                codigo = line.product.code
                u_mtx = 1  # TODO: get it from uom?
                cod_mtx = 'xxx' #FIXME: ean13
                ds = line.description
                qty = line.quantity
                umed = 7                        # TODO: line.uos_id...?
                precio = line.unit_price
                importe = line.get_amount('')
                bonif = None  # line.discount
                for tax in line.taxes:
                    if tax.group.name == "IVA":
                        iva_id = IVA_GTA_CODE[tax.rate]
                        imp_iva = importe * tax.rate
                #if service == 'wsmtxca':
                #    ws.AgregarItem(u_mtx, cod_mtx, codigo, ds, qty, umed,
                #            precio, bonif, iva_id, imp_iva, importe+imp_iva)
                if service == 'wsfex':
                    ws.AgregarItem(codigo, ds, qty, umed, precio, importe,
                            bonif)

        # Request the authorization! (call the GTA webservice method)
        try:
            if service == 'wsfe':
                ws.CAESolicitar()
            elif service == 'wsmtxca':
                ws.AutorizarComprobante()
            elif service == 'wsfex':
                ws.Authorize(self.id)
        except SoapFault as fault:
            msg = 'Falla SOAP %s: %s' % (fault.faultcode, fault.faultstring)
        except Exception, e:
            if ws.Excepcion:
                # get the exception already parsed by the helper
                msg = ws.Excepcion + ' ' + e
            else:
                # avoid encoding problem when reporting exceptions to the user:
                import traceback
                import sys
                msg = traceback.format_exception_only(sys.exc_type,
                                                      sys.exc_value)[0]
        else:
            msg = u"\n".join([ws.Obs or "", ws.ErrMsg or ""])
        # calculate the barcode:
        if ws.CAE:
            cae_due = ''.join([c for c in str(ws.Vencimiento or '')
                                       if c.isdigit()])
            bars = ''.join([str(ws.Cuit), "%02d" % int(tipo_cbte),
                              "%04d" % int(punto_vta),
                              str(ws.CAE), cae_due])
            bars = bars + self.pysriws_verification_digit_modulo10(bars)
        else:
            bars = ""

        GTA_Transaction = pool.get('account_invoice_ec.sri_transaction')
        with Transaction().new_cursor():
            GTA_Transaction.create([{'invoice': self,
                                'pysriws_result': ws.Resultado,
                                'pysriws_message': msg,
                                'pysriws_xml_request': ws.XmlRequest,
                                'pysriws_xml_response': ws.XmlResponse,
                                }])
            Transaction().cursor.commit()

        if ws.CAE:
            # store the results
            vals = {'pysriws_cae': ws.CAE,
                   'pysriws_cae_due_date': ws.Vencimiento or None,
                   'pysriws_barcode': bars,
                }
            if not '-' in vals['pysriws_cae_due_date']:
                fe = vals['pysriws_cae_due_date']
                vals['pysriws_cae_due_date'] = '-'.join([fe[:4],fe[4:6],fe[6:8]])

            self.write([self], vals)
        """

class WsTransaction(ModelSQL, ModelView):
    'SRI Ws Transaction'
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



"""
class ElectronicVoucherSequence(ModelSQL, ModelView):
    'Point of Sale Sequences'
    __name__ = 'account.electronic_voucher.sequence'

    electronic_voucher = fields.Many2One('account.electronic_voucher', 'Point of Sale')
    invoice_type = fields.Selection([
            ('', ''),
            ('1', 'Factura A'),
            ('2', 'Nota de Debito A'),
            ('3', 'Nota de Credito A'),
            ('4', 'Recibos A'),
            ], 'Tipo Comprobante SRI', required=True,
        help="Tipo de Comprobante SRI")
    invoice_sequence = fields.Property(fields.Many2One('ir.sequence',
            'Sequence', required=True,
            domain=[('code', '=', 'account.invoice')],
            context={'code': 'account.invoice'}))

    def get_rec_name(self, name):
        type2name = {}
        for type, name in self.fields_get(fields_names=['invoice_type']
                )['invoice_type']['selection']:
            type2name[type] = name
        return type2name[self.invoice_type][3:]
"""
