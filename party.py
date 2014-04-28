#! -*- coding: utf8 -*-
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Bool, Eval, Equal, Not, And

from sri_codigo_actividad import CODES

__all__ = ['Party']

class Party:
    __name__ = 'party.party'
    primary_activity_code = fields.Selection(CODES,
            'Primary Activity Code',
            states={
                'readonly': ~Eval('active', True),
                },
            depends=['active'],
            )
    secondary_activity_code = fields.Selection(CODES,
            'Secondary Activity Code',
            states={
                'readonly': ~Eval('active', True),
                },
            depends=['active'],
            )
    start_activity_date = fields.Date('Start activity date',
            states={
                'readonly': ~Eval('active', True),
                },
            depends=['active'],
            )
    controlling_entity = fields.Char('Controlling entity', help="Controlling entity",
        states={
            'readonly': ~Eval('active', True),
            },
        depends=['active'])
    controlling_entity_number = fields.Char('Controlling entity number', help="Controlling entity",
        states={
            'readonly': ~Eval('active', True),
            },
        depends=['active'])

    @classmethod
    def __setup__(cls):
        super(Party, cls).__setup__()
