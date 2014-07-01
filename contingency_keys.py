#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
#! -*- coding: utf8 -*-
from trytond.model import ModelView, ModelSQL, fields

__all__ = ['ContingencyKeys']


class ContingencyKeys(ModelSQL, ModelView):
    'Contingency Keys'
    __name__ = 'account.contingency_keys'
    key = fields.Text('Key', required=True)
    used_date = fields.Date('Used Date')
    state = fields.Selection([
            ('free', 'Free'),
            ('used', 'Used'),
            ], 'State', required=True, readonly=True)

    @classmethod
    def __setup__(cls):
        super(ContingencyKeys, cls).__setup__()

    @staticmethod
    def default_state():
        return 'free'
