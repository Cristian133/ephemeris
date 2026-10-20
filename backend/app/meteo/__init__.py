"""Datos y estadísticas meteorológicas (etapa 3).

A diferencia de `app.solar`, que calcula, este paquete consume una fuente
externa (reanálisis ERA5 vía Open-Meteo), guarda en disco lo que ya pidió y
agrega series diarias en estadísticas. La agregación es pura (numpy, sin
red); el cliente y el caché están separados para poder probarlos por su lado.
"""
