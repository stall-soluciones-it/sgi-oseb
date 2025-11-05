# -*- coding: utf-8 -*-
"""
Created on Mon Nov 27 09:18:05 2023

@author: Daniel
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


def two_dec(flotante):
    string0 = str(flotante)
    punto = string0.find('.')
    res = float(f'{string0[:punto]}{string0[punto:punto + 3]}')
    return res


def calculo_dias(fecha_ingreso, hoy_o_dia_a_calcular, fecha_egreso):
    hoy = hoy_o_dia_a_calcular
    # Creo listado de ANIOS "CALENDARIO" a incluir en calculo.
    anios = []
    anio_ing = fecha_ingreso.year


    if fecha_egreso is None:
        anio_hasta = hoy.year
    else:
        anio_hasta = fecha_egreso.year

    while anio_ing <= anio_hasta:
        anios.append(anio_ing)
        anio_ing += 1

    # Creo dic PERIODOS = {anio: dias_vacaciones, ....}
    periodos = {}
    for anio in anios:
        # Chequeo si es primer año y calculo de acuerdo a fecha de ingreso:
        antiguedad = relativedelta(date(anio, 12, 31), fecha_ingreso).years
        if antiguedad == 0:
            if fecha_ingreso > date(anio, 6, 30):
                start = fecha_ingreso
                all_days = []
                day = start
                while day <= date(anio, 12, 31):
                    all_days.append(day)
                    day += timedelta(days=1)
                laborables = sum(1 for day in all_days if day.isoweekday() in [1, 2, 3, 4, 5])
                vacaciones = round(laborables / 20)
                periodos[anio] = vacaciones
            else:
                periodos[anio] = 14
        else:
            # Calculo antiguedad:
            if date(anio, 10, 1) <= hoy:
                if antiguedad < 5:
                    periodos[anio] = 14
                elif (antiguedad >= 5) and (antiguedad < 10):
                    periodos[anio] = 21
                elif (antiguedad >= 10) and (antiguedad < 20):
                    periodos[anio] = 28
                elif antiguedad >= 20:
                    periodos[anio] = 35
    if fecha_egreso is not None:
        dias_trabajados = fecha_egreso - date(fecha_egreso.year, 1, 1)
        dato = periodos[fecha_egreso.year]
        periodos[fecha_egreso.year] = two_dec(((dias_trabajados.total_seconds() / 86400) * int(dato)) / 365)

    return periodos
