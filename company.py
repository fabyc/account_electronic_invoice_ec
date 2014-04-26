#! -*- coding: utf8 -*-

from trytond.model import ModelView, ModelSQL, fields

__all__ = ['Company']

class Company(ModelSQL, ModelView):
    'Company'
    __name__ = 'company.company'

    sri_certificate = fields.Text('Certificado SRI',
        help="Certificado (.crt) de la empresa para webservices SRI")
    sri_private_key = fields.Text('Clave Privada AFIP WS',
        help="Clave Privada (.key) de la empresa para webservices SRI")

    def sri_authenticate(self, service="wsfe"):
        "Authenticate against SRI, returns token, sign, err_msg (dict)"
        #import afip_auth
        auth_data = {}
        # get the authentication credentials:
        certificate = str(self.pyafipws_certificate)
        private_key = str(self.pyafipws_private_key)
        # call the helper function to obtain the access ticket:
        #auth = afip_auth.authenticate(service, certificate, private_key)
        #auth_data.update(auth)
        #return auth_data
