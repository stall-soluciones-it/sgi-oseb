# -*- coding: utf-8 -*-
"""
Created on Fri Mar 13 12:05:37 2020 @author: dscioli.

Datos para acceso a DBs, etc.
"""
import os
import configparser
from .dcyt import dcyt, get_key

SEC_PATH = os.path.dirname(__file__)  # get current directory
CONFIG = configparser.ConfigParser()
CONFIG.read(SEC_PATH + '/sec.stall')

ACC_TK = CONFIG.get('SEC', 'ACC_TK')
SEC_ID = CONFIG.get('SEC', 'SEC_ID')
YEK = get_key(SEC_ID, ACC_TK)

# PROJECT:
DJANGO_SECRET_KEY = dcyt(CONFIG.get('DJANGO', 'DJANGO_SECRET_KEY'), YEK)
# DB SISA:
DB_SISA_HOST = dcyt(CONFIG.get('DB', 'DB_SISA_HOST'), YEK)
DB_SISA_USR = dcyt(CONFIG.get('DB', 'DB_SISA_USR'), YEK)
DB_SISA_PASS = dcyt(CONFIG.get('DB', 'DB_SISA_PASS'), YEK)
# DB SHPD:
DB_SHPD_HOST = dcyt(CONFIG.get('DB', 'DB_SHPD_HOST'), YEK)
DB_SHPD_USR = dcyt(CONFIG.get('DB', 'DB_SHPD_USR'), YEK)
DB_SHPD_PASS = dcyt(CONFIG.get('DB', 'DB_SHPD_PASS'), YEK)
# DB OSEBAL
DB_OSEBAL_HOST = dcyt(CONFIG.get('DB', 'DB_OSEBAL_HOST'), YEK)
