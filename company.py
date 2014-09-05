#! -*- coding: utf8 -*-

from trytond.model import ModelView, ModelSQL, fields

__all__ = ['Company']

ENVIROMENT_TYPE = [
        ('1', 'Test'),
        ('2', 'Production'),
]

class Company(ModelSQL, ModelView):
    'Company'
    __name__ = 'company.company'
    certificate = fields.Binary('Certificate GTA',
        help="Certificado (.crt) de la empresa para webservices")
    private_key = fields.Binary('Private Key GTA',
        help="Clave Privada (.key) de la empresa para webservices")
    default_enviroment_type = fields.Selection(ENVIROMENT_TYPE,
        'Default Enviroment Type', required=False)
    response_lead_time = fields.Integer('WS Response Lead Time',
        help="Tiempo de espera maximo de respuesta de GTA")

    def gta_authenticate(self, service="wsfe"):
        "Authenticate against GTA, returns token, sign, err_msg (dict)"
        #import gta_auth
        auth_data = {}

        # get the authentication credentials:
        certificate = str(self.certificate)
        private_key = str(self.private_key)

        # call the helper function to obtain the access ticket:
        #auth = sri_auth.authenticate(service, certificate, private_key)
        #auth_data.update(auth)

        return auth_data

    @staticmethod
    def default_default_enviroment_type():
        return '1'

    @classmethod
    def __setup__(cls):
        super(Company, cls).__setup__()
