    #!/usr/bin/python
#! -*- coding: utf8 -*-
import lxml.builder
from functools import partial


E = lxml.builder.ElementMaker()

def metaprocess_xml(data):
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
                    subargs = metaprocess_xml(v2)
                    args.append(partial(E, v1)(*subargs))
                else:
                    args.append(partial(E, v1)(v2))
            res.append(partial(E, parent)(*args))
    return res


#------------ INFOTRIBUTARIA ------------

INFOTRIBUTARIA = {
    'infoTributaria': [
            [
            ('ambiente', '1'),
            ('tipoEmision', '6'),
            ('razonSocial', 'BILL PUERTAS'),
            ('nombreComercial', 'RESTAURANTE SANCHO PANZA'),
            ('ruc', '1234567890'),
            ('claveAcceso', '5555555555'),
            ('codDoc', '01'),
            ('estab', '001'),
            ('ptoEmi', '501'),
            ('secuencial', '00000001'),
            ('dirMatriz', 'EL TEJAR'),
            ],]
}

#------------ INFOFACTURA ------------
TOTAL_TAXES = {'totalImpuesto': [[
            ('codigo', '2'),
            ('codigoPorcentaje', '6'),
            ('baseImponible', '0.00'),
            ('valor', '0.00'),
        ], [
            ('codigo', '3'),
            ('codigoPorcentaje', '8'),
            ('baseImponible', '10.00'),
            ('valor', '10.00'),
        ], [
            ('codigo', '4'),
            ('codigoPorcentaje', '11'),
            ('baseImponible', '20.00'),
            ('valor', '77.00'),
        ]]
}

INFOFACTURA = {
    'infoFactura': [[
            ('fechaEmision', '21/03/2013'),
            ('dirEstablecimiento', 'CLL 31 N 45-81'),
            ('contribuyenteEspecial', '12345'),
            ('obligadoContabilidad', 'SI'),
            ('tipoIdentificacionComprador', '04'),
            ('razonSocialComprador', 'SRI PRUEBAS'),
            ('identificacionComprador', '9078612345'),
            ('totalSinImpuestos', '0.00'),
            ('totalDescuento','0.00'),
            ('totalConImpuestos', TOTAL_TAXES),
            ('propina','0.00'),
            ('moneda', 'DOLAR'),
        ],]
}

#------------ DETALLES ------------

TAXES1 = {'impuesto': [[
            ('codigo', '2'),
            ('codigoPorcentaje', '6'),
            ('tarifa', '6'),
            ('baseImponible', '0.00'),
            ('valor', '0.00'),
        ], [
            ('codigo', '3'),
            ('codigoPorcentaje', '8'),
            ('tarifa', '6'),
            ('baseImponible', '10.00'),
            ('valor', '10.00'),
        ],]
}

DETALLE = {'detalle': [[
        ('codigoPrincipal', '011'),
        ('descripcion', 'JABON FAB'),
        ('cantidad', '0.0000'),
        ('precioUnitario', '0.00'),
        ('descuento', '0.00'),
        ('precioTotalSinImpuesto', '0.00'),
        ('impuestos', TAXES1),
        ], [
        ('codigoPrincipal', '011'),
        ('descripcion', 'COCACOLA'),
        ('cantidad', '3.0000'),
        ('precioUnitario', '1320.00'),
        ('descuento', '0.00'),
        ('precioTotalSinImpuesto', '0.00'),
        ('impuestos', TAXES1),
        ], ]
}

#------------ RETENCIONES ------------
RETENCIONES = {'retencion': [[
            ('codigo', '8'),
            ('codigoPorcentaje', '316'),
            ('tarifa', '6'),
            ('valor', '0.00'),
        ], [
            ('codigo', '9'),
            ('codigoPorcentaje', '321'),
            ('tarifa', '0.00'),
            ('valor', '10.00'),
        ],]
}

#------------ INFOADICIONAL ------------
INFOAD = [
            E.campoAdicional('Lenny Kravitz Street', nombre=u'Dirección'),
            E.campoAdicional('rockstar@itunes.com', nombre='Email'),
        ]

#-----------------------------------------------------------------------

"""
infoTributaria_ = metaprocess_xml(INFOTRIBUTARIA)[0]

infoFactura_ = metaprocess_xml(INFOFACTURA)[0]
detalles_ = E.detalles(*metaprocess_xml(DETALLE))
retenciones_ = E.retenciones(*metaprocess_xml(RETENCIONES))
infoAdicional_ = E.infoAdicional(*INFOAD)


evoucher = E.factura(
        infoTributaria_,
)

        infoFactura_,
        detalles_,
        retenciones_,
        infoAdicional_,
)

print lxml.etree.tostring(evoucher, pretty_print=True)
"""
