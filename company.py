#! -*- coding: utf8 -*-

from trytond.model import fields
from trytond.pool import PoolMeta, Pool

__all__ = ['Company']
__metaclass__ = PoolMeta

ENVIROMENT_TYPE = [
        ('1', 'Test'),
        ('2', 'Production'),
]


BROADCAST_TYPE_SRI = [
        ('1', 'Normal'),
        ('2', 'Unavailable system'),
]

class Company:
    __name__ = 'company.company'
    private_key = fields.Binary('Private Key GTA',
        help="Clave Privada (.key) de la empresa para webservices")
    default_enviroment_type = fields.Selection(ENVIROMENT_TYPE,
        'Default Enviroment Type', required=False)
    response_lead_time = fields.Integer('WS Response Lead Time',
        help="Tiempo de espera maximo de respuesta de GTA")
    ws_url = fields.Char('Web Service Url')
    ws_test_url = fields.Char('Web Test Service Url')
    gta_user_password_hash = fields.Char('GTA User Password')
    gta_user_password = fields.Function(fields.Char('Password'), getter='get_password',
        setter='set_password')
    broadcast_type = fields.Selection(BROADCAST_TYPE_SRI, 'Broadcast Type', 
        required=False)
    connection_mode = fields.Selection([
                ('', ''),
                ('out_connection', 'Out Connection'),
                ('on_line', 'On Line'),
            ], 'Connection Mode')

    def gta_authenticate(self, service="wsfe"):
        "Authenticate against GTA, returns token, sign, err_msg (dict)"
        #import gta_auth
        auth_data = {}

        # get the authentication credentials:
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

    def get_password(self, name):
        return 'x' * 10

    @classmethod
    def set_password(cls, companies, name, value):
        User = Pool().get("res.user")
        if value == 'x' * 10:
            return
        to_write = []
        for user in companies:
            to_write.extend([[user], {
                        'gta_user_password_hash': User.hash_password(value),
                        }])
        cls.write(*to_write)
