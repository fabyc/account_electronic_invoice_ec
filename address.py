#! -*- coding: utf8 -*-

from trytond.model import ModelSQL, ModelView
from trytond.pyson import Id
from trytond.pool import PoolMeta

__all__ = ['Address']
__metaclass__ = PoolMeta

class Address:
    __name__ = 'party.address'

    @staticmethod
    def default_country():
        return Id('country', 'ec').pyson()
