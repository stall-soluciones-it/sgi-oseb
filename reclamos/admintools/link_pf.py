# -*- coding: utf-8 -*-
"""
Created on Wed Jan 18 12:40:05 2023

@author: Daniel
"""
import requests


def link_pf(barra, valido):
    """Genera link de pago PF."""
    url = 'https://pagosenlinea.pagofacil.com.ar/api/linkdepago/obtenerlink'
    anio = str(valido)[:4]
    mes = str(valido)[4:6]
    dia = str(valido)[6:8]
    barra = str(barra)
    parametros = {"api_key": "xxx",
                  "codigo_barra": f"{barra}",
                  "fecha_expiracion": f"{anio}-{mes}-{dia}T23:59:59.000"}
    x = requests.post(url, json=parametros)
    link = str(x.text).replace('{"url":"', '').replace('"}', '')
    return link
