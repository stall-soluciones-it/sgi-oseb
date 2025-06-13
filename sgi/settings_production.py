from .settings_base import *
import sgi.shpd_cnf as cnf

DEBUG = False

ALLOWED_HOSTS = ['172.16.29.129', 'plataforma.as']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'sgi_db',
        'USER': cnf.DB_SHPD_USR,
        'PASSWORD': cnf.DB_SHPD_PASS,
        'HOST': 'localhost',   # Or an IP Address that your DB is hosted on
        'PORT': '',
    }
}

CARGA_GSA = 'NO'
