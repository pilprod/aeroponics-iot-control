import argparse
import time
import os
import sys
import paho.mqtt.client as mqtt
import json
from datetime import datetime

# Определяем путь к файлу блокировки
LOCKFILE = os.getenv("HISENSE_LOCKFILE", "hisense.lock")
# Логи
LOG_FILE = os.getenv("HISENSE_LOG_FILE", "hisense.log")

# Глобальные переменные для хранения текущих состояний
current_power = None
current_mode = None
current_temperature = None
current_fan_speed = None
current_swing = None
current_dimmer = None

# Значения по умолчанию
DEFAULT_POWER = "off"
DEFAULT_DIMMER = "off"
DEFAULT_MODE = "Cool"
DEFAULT_TEMPERATURE = 24
DEFAULT_FAN_SPEED = "Medium"
DEFAULT_SWING = "off"

# Глобальная переменная для таймаута между сигналами
TIMEOUT = 5

# Настройки MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = 1883
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_KEEPALIVE = 30
MQTT_QOS = 2

# MQTT топики
MQTT_TOPIC_POWER = os.getenv("MQTT_TOPIC_POWER", "portfolio/hisense/power")
MQTT_TOPIC_MODE = os.getenv("MQTT_TOPIC_MODE", "portfolio/hisense/mode")
MQTT_TOPIC_TEMPERATURE = os.getenv("MQTT_TOPIC_TEMPERATURE", "portfolio/hisense/temperature")
MQTT_TOPIC_FAN_SPEED = os.getenv("MQTT_TOPIC_FAN_SPEED", "portfolio/hisense/fan_speed")
MQTT_TOPIC_SWING = os.getenv("MQTT_TOPIC_SWING", "portfolio/hisense/swing")
MQTT_TOPIC_DIMMER = os.getenv("MQTT_TOPIC_DIMMER", "portfolio/hisense/dimmer")
MQTT_TOPIC_IR_SEND = os.getenv("MQTT_TOPIC_IR_SEND", "portfolio/hisense/ir_send")
MQTT_TOPIC_LOG = os.getenv("MQTT_TOPIC_LOG", "portfolio/hisense/log")

# Сигналы для комбинаций режима, температуры, скорости вентилятора и swing
IR_SIGNALS = {
    # (режим, температура, вентилятор, swing): сигнал
    # Cool Auto ON
    ("Cool", 16, "Auto", "on"): "CIUgqhFmAoYGH2ADAx8CZgLgBwNAGwEfAoAHBYYGZgIfAuAtA+AzO+ANc0ABgBsDhSBmAsBfQAdAA0AbBYYGHwIfAuADBwFmAkAPQANAC0ADQAsAH2ABQAfgFwPAAcAnwAHAD+AHB0ABQBNAAcAH4AMBQBPgHQPAq0AHwAPAO0APQQPAD+AJB0ABwBcBHwJACcABQAvAA+ADAUATwAHgEwtAG0AD4AMBQA8DhgYfAkAHwAPgAwHAE+AHB8ABQBfgBz8DZgIfAg==",
    ("Cool", 17, "Auto", "on"): "B5Ig5xExArMGgAPgCwFAG0ABQAdAA+AvAeADO+ADC+AlAQJhAjHgCgEDkiAxAsBTQAdAA0AB4A8HQAFAG0AD4BMB4A1t4AEBQB9AA+ADAeADD0ALwANAAUALQAFAB+ADA+ATAUAnQAHAq0AHQAPAF0AHQA9BA0ABQA/AAcALQAdAA+AHAUATwANAAUAL4AMBQA/gAwPAAUATQAFAB8AD4AcBQJPAG0AH4AMBQA/gFwPgBz8DYQIxAg==",
    ("Cool", 18, "Auto", "on"): "B5sgyBEnArQGgAPgCwFAGwMnAmECQAdAA0ABAmECJ+ACAeAFDQEnAuAHD4ABwDsBJwKAH+ABD8ABgBfgCQXgAwHgAx3gAQEDmyAnAsBPQAdAA0ABQAdAMUAHwAPAAcAPQB9AAcAHQAFAC+AnA+ADAeAHO0ABQBPAAUAL4AMDwAFAE0ABQAfgBwPAAcC3wAdAJ0ALQQNAC+ATA0AB4BcfQAHgEyPgHxtAk+AfK+ALJ+AIPwICJwI=",
    ("Cool", 19, "Auto", "on"): "B4sgyRE5Ap8GgAPgCwFAG0ABQAdAA+AvAeADO0ALQAPgPwEDiyA5AsBPQAdAA0AB4AMHQAtAA8ABQAtAA+B9AQJiAjngCAHAE0AHwAMEOQKfBmIgAwM5AjkCwAcBOQJAD0ED4IMBQJMBYgLgAQPgEwFAJ+AHAUA/4AQBAgI5Ag==",
    ("Cool", 20, "Auto", "on"): "B58g2xEtArEGgAPgAwECXgItIAEBXgJAG0ABQAdAA+ABAQJeAi3gAAHgAwvgAwHgARfAO4ARgAXAE4ABgBOAAYAL4AMFgAHgAxGAC0ABA58gLQLAS0AHQANAAeADB0ALQAMBLQKAN0ALQAPAAYAV4AEBQA/AA+APAcAfQAfgAwFAD+APAwEtAkAZAS0CQAVAA4AB4AEJgAGAD4AF4AUBQLPAAwMtAl4CwAtBA+ADAQFeAoADQAFAC8ABwAtAB+AHA8AB4AcXwA/gAwHAE+ADB0ABwA9Al8AL4CsH4Ag/AgItAg==",
    ("Cool", 21, "Auto", "on"): "B5wggBFkAocGgAMBEQLgCQNAG0AXQAdAA0AL4CsD4AM7wAvAB+ArT+ADMwOcIGQCwEtAB0ADQB/gBwfgBxNAHwJkAhEgAUAF4IEDAWQC4AeNBGQChwYRYAMDZAIRAkALQAdAA0ALQAMDnCARAkAP4A8DQAHgDxvgSxdAk+AzV+AIPwICEQI=",
    ("Cool", 22, "Auto", "on"): "B5EgxRE2Ap8GgAPgCwFAG0ABQAdAA+AvAeAHO0APQAPgCwECYgI24AwB4A8XA5EgNgLAS0AHQANAAeAHB0AB4AMTwAvgJwHgA4fgAwvgDQFAIUADQAFAB+AfA+AFAUCrQANAAUAH4AcDQQPgDwFAccAB4AsL4AMT4AcBQBtAA+AHAeALE+ADAUCf4BcjwAFAJ0AD4AMBQD/AAQdiAjYCNgI2Ag==",
    ("Cool", 23, "Auto", "on"): "B5sgqxFoAqMGQAMBLgLgCwHAF0AHQAPgAwECaAIu4CAB4AM7QAsCowZoIAMBLgLgEwECaAIu4AwB4AcXA5sgLgLAS0AHQANAAeAHB0AB4AETAGggCwNoAi4CQAPAAUAL4AMDQAHgBw/gGQFAMeAfAeATK0AbwAMBowaAA0ABQAtAF0AHwANBA8ABQBvgAwFAD0AD4AMBwA9AB8ADQAHAC0AHQAFAB+ArA0CX4Cs3wDPgCD8CAi4C",
    ("Cool", 24, "Auto", "on"): "B48g5RE4ApgGgAPgCwFAG0ABQAdAA+AvAeAFOwF8AkADA/YBfALgBRfAAQF8AkAbADigAQP2ATgCgAEBfAKACwJ8AjjgAgEDjyB8AsBHQAdAA0AB4AMH4AMLQAFAD0AD4CMBgHuAAeADC+BfAcCvQAcBmAbgBYEDjyA4AuBHAQF8AkADBPYBfAI4YAHgAwcKfAL2ATgCOAJ8AjggAQH2AYAHFzgCfAL2ATgCOAKYBjgCOAL2AXwCOAJ8AoAH4AMBAXwCQAMI9gE4AjgCfAI4IAHgAQsDfAL2AUA/AnwCOGABB3wCOAI4AjgC",
    ("Cool", 25, "Auto", "on"): "CKAgphFkAogGMGADgAECZAIw4AABBWQCiAZkAoAHAzACiAZAC+APAcAbwAfgAwEBZALgATvACwJkAjAgAeABF+AHAYAfgAHgDwuAAQOgIGQCwEdABwOIBjACQAHgAwcEiAZkAjAgAQeIBjACMAJkAkAHQAOAAQJkAjDgDAHgAxfgAwvgGwHAL8AHwAFAD+ALA0AB4AsX4AETwK8EiAZkAjDgBgEDoCAwAsAB4AMd4AML4AMB4AMXwAvAB+ADAUATQAPAAeAHC0AP4AsDA4gGMALgCxdAE0ABQAfgEwPgCD8CAjAC",
    ("Cool", 26, "Auto", "on"): "B5MgqBFPAo0GgAPgCwFAG0ABQAdAA+APAQP/AU8CwAHgAwvAAeAHO8APwAfgEwHAT0AH4AMDQAFADweTIE8CjQahAkALAY0GgAPAC8AHQBfAC8AHQBPAAUATQANAAUAHQAPgGQHgAyXgKwvAM8AHQAFAC0ADQAHAB0ABAf8BwK8BjQZAC0ADBU8CTwL/AUADQQMDTwL/AeBdA0AB4AtrQAGAFwONBv8BgAtAAeALC8ATAf8BgbngBQdAP0AXC6EC/wGhAv8BoQL/AQ==",
    ("Cool", 27, "Auto", "on"): "B6UghRFmAogGgAMBEgLgCQNAG0AXQAdAA0AL4AUDA7sCxAHgBxPgCQ/gAztAC0ADA2YCEgJABwESAkADQAFAB0ADQAFAB+AHA0ABgBNAAcALA6UgZgLAR0AHQANAG+ALB+ADE8ALQCvgHwMCZgISIAEAZiABwAUBEgKAC+APBwJmAhIgAUAFgANAAcAL4CEHA4gGEgJAAUAzQAvgAwdACwOlIBICQAfgfwPAo+ANjwHEAeIFNQPEAWYCQCsBxAHAFwOIBsQBQA8LZgLEAbsCxAFmAhIC",
    ("Cool", 28, "Auto", "on"): "CKYgrBFnApcGMmAD4AsBQBtAAUAHQAPgHQECZwIy4AYBgDvgBRcClwZnYAMAMuAsAeABNwemIGcClwYyAkABQAdAAwEyAuADEwJnAjIgAQGXBoADQAHgAwvgBQGAK4AB4AML4BsB4AMvwAvgAwdAC+ALA0AB4AsXQBOAAUCvwAFAC0ADQAHABwOmIDIC4BMB4AFJ4AUBQBdAA+APAUAbwAPgDwFAH+AHAUCXQBfgFwNAAeALI+AIPwICMgI=",
    ("Cool", 29, "Auto", "on"): "CI8gmRF1AocGNGADBDQCdQI0YAFABwV1AvUBdQJAG0ABQAdAA0ATAzQCdQLAB4ALBDQC9QF1YAMANCABQAsBNAJAA0ABQAcBdQJAO4ABwAtAB0ADATQC4AEvCnUC9QE0AjQCdQI04AABgAsB9QFAB0AD4AkBA48gdQJAR0ABAYcGQAsCdQI0IAHgCwfgAxPAC+AbAUB/gAMFNAI0AnUCgANAAYALgBfAAeAHD+APAQJ1AjTgHgEDhwY0AsAB4AsLA48gNALgRwHgE51AG0ADQAFABwF1AuEBAQN1AjQCQKNABwV1AvUBdQJABwA0IAEF9QE0AjQCQAsFdQL1AXUCQAcANGAB4AEHBfUBNAI0AkA/DzQC9QF1AjQCdQL1ATQC9QE=",
    ("Cool", 30, "Auto", "on"): "B54gyRFAAp0GgAPgCwFAGwPxAUACQAdAA8ABQBMDQAKOAoAH4AEB4AcPQAFAE8A7QAtAAUAPwANAAcAX4CsBA54gQAJAS0ABQAdAA0BPQAdAAUAHgAMAjmAHQAEBnQaAA+ADAUAz4G0B4A954AMX4AELwLuAB0AXB/EBniDxAUACQAEC8QGOIAMBQAJAAQrxAY4CQAKOAvEBQGADwAFAD8ABAfEBQB9AA0ALAUACwAEK8QGOAkACjgLxAUAgAwiOAkACjgLxAUBgAwFAAoALAUACQAeAAwBAIAGACwNAAkACgJcBQAJAFwOOAvEBQAMAQKAHQAvgFwNAP+AEIwIC8QE=",
    # Heat Auto ON
    ("Heat", 16, "Auto", "on"): "B5Ig3RE6ApoGgAPgCwFAG0ABQAdAA+CLAQOSIDoCwAFAo0ADQAHgDwdAAUAbQAPgiQECcQI64A4BQK/gAwPAAUAT4QMD4HsBQJPgMwHgCD8CAjoC",
    ("Heat", 17, "Auto", "on"): "B3wgzBEyApoGgAPgCwFAG0ABQAdAA+A7AeAFRwJkAjLgBAFAD+APA0ABwBtAAYALA3wgZALAC0BbQAMBMgKACwEyAoAHQBNAAwMyAmQCQANAC0ADAzICZALgAQNAAeADD+ATC+BHAUBrQAFAB+AJAwGaBsADADJgCwAyYAFABwVkApoGZALhAwMAMuA+AeAPSeAHF+AHD0ABA5oGMgJAAUAbQAPgBwHgAxPgAwvAAUA/QBcLZAIyAmQCMgIyAjIC",
    ("Heat", 18, "Auto", "on"): "B7QgwhFAArYGgAPgCwFAG0ABQAdAA+A/AeBDSwO0IEACwAFAV0ADQAHgAwfgAwsDQAL5AUAPQAPgWQED+QFAAuAXAeAPI+ABF+ADq0ALCbYG+QG2BkACQAJABwX5AbQg+QFACwFAAsABQAsC+QGQIAMBQAJAAQH5AYALAfkBgANAAYAL4AMX4A0LQAEB+QGAA0ABwAsB+QFAL8ADQA8BQAJAAQH5AUCTQAdAG0AHAUACQAFAB4ADwBdAB+ALA0A/4AQXAgL5AQ==",
    ("Heat", 19, "Auto", "on"): "B5UguRFEAqkGgAPgCwFAG0ABQAdAA+AVAQP6AUQC4BkBQEdAA4AB4A8z4AMX4AML4AUBQBkDlSBEAkAHA/oBlQJAV0ADA/oBRALgCwdAE0ABQAdAA+AlAUBVwAHgAwvgAwHgCxfgBxPgBw9AAeALE0AB4AEXAakGgAvgCQcCRAKVIQPgAQFAJwL6AZUgA4AHAEQgAYALQAcAleAMC0ABAfoBwAPgASNAAQH6AYADQAHgCQvgASsD+gFEAkABBfoBqQb6AcAXwAdAF0ADwA9AB+APA8A/C5UC+gGVAvoBlQL6AQ==",
    ("Heat", 20, "Auto", "on"): "B4ggwhFFAqEGQAMD/gFFAsAB4AELA6EGRQJAAUAHQAPgBQHgASfgEQHgDyMB/gGATwP+AUUC4AMB4AcP4BkBA4ggRQLAAUBTQANAAeADB0ALwANAYcAL4BkBQC3gAwHgBw9AAeAHE+AHD8AB4AMXwAvAB0ABQAtAA+AHAQH+AYCvAf4B4AELAUUCQAFAB0ADAYggQBvAAUALAv4BlCADQAfgCQNAAYAX4A8j4AMX4AMLwDdAB+ABF0ABAf4BwANAFwWhBv4BRQJAAQH+AUAPQANAC0ADQAtAA+ADC0AP4AMDQD/gAw8DRQL+AQ==",
    ("Heat", 21, "Auto", "on"): "CKUgpBFhAp4GNWADgAECYQI14AIBQBtAAUAHQAPgCQHgBS/gAQHgERfAR8AH4BMBAmECNeAYAQOlIDUCwAFAU0ADQAFAB0A/QAdAA8ABQAvAA+AHAUAv4BcB4BsjATUCwCVAB+ATA+ALAUAv4AUBAZ4GgBMDngY1AkABgA0BNQJAD0AD4QMD4A8BwDPgAwFAE0ADwAHgBwtAD0AD4AMB4AMPQAvAA+ADAUCTQAHAG0AH4AsBQBdAA0ABQAfAA0A/wAsHYQI1AmECNQI=",
    ("Heat", 22, "Auto", "on"): "B48g4BFCAqsGgAPgCwFAG0ABQAdAA+A/AUBLQAPgGQED+AFCAuAVAQOPIEICwEtAB0ADQAGABwGaAkAHwEXgBwvAAcAfwAfgAwFAE8AD4D0BQE3gCwHgAxfgAwsBQgJAt8ABgAsB+AFABwGrBoAHBY8g+AFCAsADQAHgFwsC+AGaIAPgAwdACwFCAkABQAeAA8AjAUICQAFAB4AD4BcXB6sGQgJCAvgBQAPgASsD+AFCAkABAfgBQBPgEwMDqwb4AeAEHwIC+AE=",
    ("Heat", 23, "Auto", "on"): "B40gxxFCArcGgAPgCwFAG0ABQAdAAwP5AUIC4AsB4A8X4AMBwCNAR8ADwAHAG+ArAQONIEICQE9AAUAHQANAAeADB4ALAfkBgAeAAeADC+BNAQP5AUIC4BcB4A8j4AMX4AMLAUICQLcFtwb5AbcG4AEHBY0g+QFCAkADA0IClAJAB4AD4AELQAEB+QHAA+ABF+AbC0ABAfkBwAPgGzsDtwb5AYAvQAHgCQtAQ0ADQBtAB0AD4AMLQD9AEwuUAvkBlAL5AZQC+QE=",
    ("Heat", 24, "Auto", "on"): "B2sg3hEpAowGgAPgCwFAG0ABQAdAA+ABAQJsAilgAQVsAscBbAJAB+ArA4BTAWwC4A0DQAHgDxvgARcHayBsAowGbAJAEwKMBikgAwJsAikgAQmMBikCKQJsAowGgAOACwApYAcHKQJsAowGbAJAB+AJA0ABBWwCxwEpAuANAQFsAoAD4AMBQBPAAeAPC0AB4AMbASkCgA1ABeAhA+ABt+ABAQNrICkC4AsBAmwCKeAQAeADG+ADC+ADAUAXQAPAAQFsAuEFFQFsAoAD4AcBA4wGKQJAAcAfQAfgAwHAD0AH4AsDQD/gAxcDKQIpAg==",
    ("Heat", 25, "Auto", "on"): "B58gyBEqAroGgAPgCQEBZwJAG0ABQAdAA+A7AeADR+ADC0ABAmcCKuAMAeADF+ADC0ABA58gKgJAR0AXQAdAA0ABQAfAE0AHQAPAAUAbQANAE0AD4A8B4AsbwBNAB0AD4A8BQBtAA8AB4AcLQA/AA0AB4AsLQBNAAUCrQAFAB0ADQBfAA0ABQQPgBwHgAx9AC8ABQAvgTwNAAUBb4AejQBPgIwPgCD8CAioC",
    ("Heat", 26, "Auto", "on"): "B6Yg6xE4ArcGgAPgCwFAG0ABQAdAA+A/AcBLwAfgMwEDpiA4AsBHQAdAA0AB4AcH4AMBQBtAA+CPAQFuAoADwAHAq0AH4AMDwAFBA+BvAUCr4AcBQKPgHwHgFz8HbgI4AjgCOAI=",
    ("Heat", 27, "Auto", "on"): "CKwgtBFkArQGKWAD4AEBAmQCKaABQBtAAUAHQAMBKQKAG4AF4AMB4AMR4AML4AMBgBdAR0ADAykCZAKAB0ABAmQCKeAAAeADC+ADAeAFF8ANA6wgKQLAR0AHQANAAUAHQCNAB+AHAUATQANAH0ABQAfgCQMCZAIp4AAB4AML4AMB4BUX4BMdQBtAA+ALAUAX4AMDQKtAAUAHQANAG8AHQAFBA0ATQAPAAUALwAPAAcAP4FcHwJvgL2fgCD8CAikC",
    ("Heat", 28, "Auto", "on"): "B40ggBFjAoUGgAMBFwLgCQNAG0AXAoUGFyADA2MCFwLgLQPgCztAE0AD4C9TwDcDjSBjAkALQEvAA8AP4AMHQAvgJwNAAeAnM+ABL0ABwA9AAcAL4DEH4AffQA9AT8EDQAvgBQMBFwJAEUABQAdAA8ABQAvgAwNAAcAPwAHAD0AHwAFAC+ATA0ABA4UGFwLgFyPgEx/gCD8CAhcC",
    ("Heat", 29, "Auto", "on"): "B7YgrBFJAp0GgAMD/wFJAkABwAdAAUAbQAFAB0AD4AMbwAFAE8AD4AMB4AMTgDsDiwL/AYALQAFAE0ADQBMB/wGAG4AB4AML4BkBB7YgSQL/AUkCQEvAA0ABQAtAAQKdBosgAwFJAsABQCvAAUALAv8BiyADQAeAA0ABQAvAAUALQANAAcAHQAHAC0AHwANAAUAL4CUB4BkxwL9AB4ADA/8BnQaAC0ABBbYg/wFJAkADwAGAC+AD2eADCwFJAkABQAcB/wHgAxfgCwsCiwJJIAEB/wHAAwCL4AwLQAEB/wHAAwOdBv8BQAvgDSsD/wFJAkABQAcB/wFAI+ADA0ATQD/gAxMDiwL/AQ==",
    ("Heat", 30, "Auto", "on"): "CJwgsxFnApIGGCADA2cCGALgCQMFkgYYAhgCQAdAAwUYAhgCZwLgKwPgBzsBkgbAAwUYAhgCZwLgJQNAAUAzgAEBnCBACwNnApIG4AEDwA8AGCABwBcAGOAAAUAL4HMDQAFAfwEYAoAFgAHgBwtAD0ADQAEDkgYYAkALQAdAA0ALQANAC0ABA5wgGAJAD8ABwAtAB8ADQAFAC0ABQAfgUwNAl+AzX+AIPwICGAI=",
    # Fan
    ("Fan", None, "Auto", "on"): "B48gyREvAq4GgAPgBQECYgIvIAFAG0ABQAdAA+ADAYAhAWICQBdAA+ABAQJiAi/gCgHAI0AHwAPgFQHgDUfAAcAdA48gLwJAAcBTQAdAAeAFB4AtwBOAAYATgAGAC4AFgAHAC8AHwAHgBw/gCwFAI+AHA+ABAUAZ4AsB4A8XAS8CwLdAB8ADAy8CYgLAC8EDwAECYgIvYAFAB0ADwAHgBwtAD8ADwAHAD+AHB8AB4AcXwA/AAUAPQJdAB+AvA+AHPwMvAi8C",
    ("Fan", None, "High", "on"): "B5cg3REbApIGgAMEGwJlAhtgAUAHgANAGwEbAkAHQAMFGwIbAmUC4AcDA5IGZQLgBxPgCw/AJ0AHwAPgCyfgJxMDlyBlAkAzwFNABwAbIAGABwFlAkAHwANAD+AlA8ABQDfAAYALgAXgAwGAEeADBcABgBPgAQHAD0AHQANAAUAH4A8DwAFAHwGSBoAD4AMLA5cgGwJAD0ABQAfgdwNAo+Azg+AIPwICGwI=",
    ("Fan", None, "Medium", "on"): "B5wgsRFIAooGgAMBAwKAA0ABBwMCiwJIAosCQBsDAwJIAkAHQANAAUAPwAFAC0ADQBtABwYDAosCAwJI4AABQAtAA0ABgCMBiwJAB8ADQAEBAwLAAwSLAgMCSOAAAUALQANAAUAHQANAAcAHQAFACwOcIEgCQAHAU0AHQAHgBwdAAcAT4CMBQGPgFwHgAyNAC0ADQAFAB0ADQAFAB4AD4BXnwAECAwJI4AABwAtAv8ADQAGACwEDAsED4BEBAgMCSOAMAeADF+ADC+ADAeADF+APC+ADAQEDAkCTgOXgAQdACwBIYAFAB0ADQAFABwEDAsArQAsASCABQD8PSAIDAosCAwJIAgMCSAIDAg==",
    ("Fan", None, "Low", "on"): "B48gyREvAq4GgAPgBQECYgIvIAFAG0ABQAdAA+ADAYAhAWICQBdAA+ABAQJiAi/gCgHAI0AHwAPgFQHgDUfAAcAdA48gLwJAAcBTQAdAAeAFB4AtwBOAAYATgAGAC4AFgAHAC8AHwAHgBw/gCwFAI+AHA+ABAUAZ4AsB4A8XAS8CwLdAB8ADAy8CYgLAC8EDwAECYgIvYAFAB0ADwAHgBwtAD8ADwAHAD+AHB8AB4AcXwA/AAUAPQJdAB+AvA+AHPwMvAi8C"
    # Добавьте здесь остальные комбинации для разных режимов, температур, вентиляторов и swing
}

IR_SIGNALS_POWER = {
    "on": "B9og3RF3AoMGgAMBDQLgCQNAG0AXQAdAA0AL4A8D4BMf4A8b4A8X4A9j4AsXA9ogdwJAF+ADS+AHC0APQANAJ+CrA0C7wANAv0ALQAdAAwO4AXcCwQNAD+APA+ADM+API0BL4A8b4BkXAtUCdyABQEPgEWsDDQJ3AuANAwSDBg0CdyABAA0gAYALDQ0CdwINAncCDQINAg0C",
    "off": "B7khDRI0AtcGgAPgCwFAG0ABQAdAA+ATAeATH+ATG+A3AQO5ITQC4BMB4FN74GMBQMdAA+AHAUATBbkhpgGOAkADBY4CpgE0AuALAUAn4GcB4A9z4AsX4AMTwAsL1wY0AjQCNAI0AjQC"
}

def log_message(client, message):
    """Функция для отправки логов в MQTT и запись в файл в формате JSON с датой и временем."""
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "message": message
    }

    # Публикация сообщения в MQTT
    if client is not None:
        client.publish(MQTT_TOPIC_LOG, message, qos=MQTT_QOS)

    # Запись логов в файл
    try:
        with open(LOG_FILE, 'a') as logfile:
            logfile.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Ошибка записи в файл лога: {e}")

    # Вывод в консоль
    print(json.dumps(log_entry, ensure_ascii=False))

def check_lock():
    """Функция для проверки и ожидания освобождения блокировки. Удаляет файл блокировки после 6 попыток."""
    lock_attempts = 0
    while os.path.exists(LOCKFILE):
        lock_attempts += 1
        log_message(None, f"Обнаружена блокировка. Ожидание... Попытка {lock_attempts}/6")
        time.sleep(3)
        if lock_attempts >= 6:
            log_message(None, f"Удаление файла блокировки после {lock_attempts} попыток.")
            remove_lock()
            break

    try:
        open(LOCKFILE, 'w').close()
    except Exception as e:
        log_message(None, f"Ошибка при создании блокировки: {str(e)}")
        remove_lock()
        sys.exit()

def remove_lock(client=None):
    """Функция для удаления блокировки."""
    if os.path.exists(LOCKFILE):
        os.remove(LOCKFILE)
    log_message(client, "Блокировка снята.")

def on_connect(client, userdata, flags, rc):
    """Функция при подключении к MQTT."""
    log_message(client, "Подключено к MQTT брокеру")
    client.subscribe([(MQTT_TOPIC_POWER, MQTT_QOS),
                      (MQTT_TOPIC_MODE, MQTT_QOS),
                      (MQTT_TOPIC_TEMPERATURE, MQTT_QOS),
                      (MQTT_TOPIC_FAN_SPEED, MQTT_QOS),
                      (MQTT_TOPIC_SWING, MQTT_QOS),
                      (MQTT_TOPIC_DIMMER, MQTT_QOS)])
    log_message(client, "Подписка на топики выполнена")

def on_message(client, userdata, msg):
    """Функция для обработки входящих сообщений MQTT."""
    global current_power, current_mode, current_temperature, current_fan_speed, current_swing, current_dimmer

    if msg.topic == MQTT_TOPIC_POWER:
        current_power = msg.payload.decode() == "on"
        log_message(client, f"Получено сообщение: Текущее состояние питания: {'on' if current_power else 'off'}")
    elif msg.topic == MQTT_TOPIC_MODE:
        current_mode = msg.payload.decode()
        log_message(client, f"Получено сообщение: Текущий режим: {current_mode}")
    elif msg.topic == MQTT_TOPIC_TEMPERATURE:
        current_temperature = int(msg.payload.decode())
        log_message(client, f"Получено сообщение: Текущая температура: {current_temperature}")
    elif msg.topic == MQTT_TOPIC_FAN_SPEED:
        current_fan_speed = msg.payload.decode()
        log_message(client, f"Получено сообщение: Текущая скорость вентилятора: {current_fan_speed}")
    elif msg.topic == MQTT_TOPIC_SWING:
        current_swing = msg.payload.decode() == "on"
        log_message(client, f"Получено сообщение: Текущее состояние swing: {'on' if current_swing else 'off'}")
    elif msg.topic == MQTT_TOPIC_DIMMER:
        current_dimmer = msg.payload.decode() == "on"
        log_message(client, f"Получено сообщение: Текущее состояние диммера: {'on' if current_dimmer else 'off'}")

def send_ir_signal(client, ir_code, topic=None, state=None):
    """
    Функция для отправки одного IR сигнала через MQTT и обновления состояния.
    """
    if not ir_code:
        log_message(client, "Ошибка: IR код не найден.")
        return False

    client.publish(MQTT_TOPIC_IR_SEND, ir_code, qos=MQTT_QOS, retain=True)
    log_message(client, f"Отправлен IR сигнал.")
    time.sleep(TIMEOUT)  # Таймаут между отправками

    if topic and state is not None:
        client.publish(topic, state, qos=MQTT_QOS, retain=True)
        log_message(client, f"Опубликовано обновленное состояние '{state}' в топик: {topic}")
    return True

def get_ir_code(mode, temperature, fan_speed, swing):
    """Функция для получения IR кода, учитывая особенности режима Fan."""
    # Если режим Fan, игнорируем температуру
    if mode == "Fan":
        temperature = None
    key = (mode, temperature, fan_speed, swing)
    return IR_SIGNALS.get(key)

def main():
    global current_power, current_mode, current_temperature, current_fan_speed, current_swing, current_dimmer, TIMEOUT

    parser = argparse.ArgumentParser(description="Управление кондиционером Hisense через MQTT")
    parser.add_argument("power_state", choices=["on", "off"], nargs="?", help="Состояние питания")
    parser.add_argument("target_mode", choices=["Cool", "Heat", "Fan", "Dry", "Auto"], nargs="?", help="Режим работы (только при включении)")
    parser.add_argument("target_temperature", type=int, choices=range(16, 30), nargs="?", help="Целевая температура (от 16 до 29 градусов, только при включении)")
    parser.add_argument("fan_speed", choices=["Low", "Medium", "High", "Auto"], nargs="?", help="Скорость вентилятора (только при включении)")
    parser.add_argument("swing", choices=["on", "off"], nargs="?", help="Состояние swing (только при включении)")
    parser.add_argument("dimmer", choices=["on", "off"], help="Состояние диммера (on/off)")
    parser.add_argument("--timeout", type=int, default=5, help="Таймаут между сигналами (по умолчанию 5 секунд)")

    args = parser.parse_args()

    # Инициализация MQTT клиента перед использованием log_message
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    check_lock()

    try:
        TIMEOUT = max(args.timeout, 5)

        client.loop_start()

        time.sleep(5)  # Ждем получения данных по текущим состояниям через MQTT

        log_message(client, f"Получено power_state: {args.power_state}")

        if args.power_state == "off":
            log_message(client, "Выключение кондиционера...")
            ir_code = IR_SIGNALS_POWER.get("off")
            if send_ir_signal(client, ir_code, MQTT_TOPIC_POWER, "off"):
                # Сбрасываем состояние диммера после выключения питания
                current_dimmer = False
                client.publish(MQTT_TOPIC_DIMMER, "on", qos=MQTT_QOS, retain=True)
                log_message(client, "Состояние диммера сброшено в 'on' после выключения питания.")
            remove_lock()
            return

        if current_power is False:
            log_message(client, "Включение кондиционера...")
            ir_code = IR_SIGNALS_POWER.get("on")
            send_ir_signal(client, ir_code, MQTT_TOPIC_POWER, "on")
            time.sleep(1)  # Задержка перед установкой режимов
        else:
            log_message(client, "Кондиционер уже включен, пропуск сигнала включения.")

        # Если режим Fan, игнорируем температуру
        if args.target_mode == "Fan":
            args.target_temperature = None

        need_update = False

        if args.target_mode and args.target_mode != current_mode:
            need_update = True
        if args.target_temperature is not None and args.target_mode != "Fan":
            if args.target_temperature != current_temperature:
                need_update = True
        if args.fan_speed and args.fan_speed != current_fan_speed:
            need_update = True
        if args.swing and (args.swing == "on") != current_swing:
            need_update = True

        last_ir_code = None  # Добавлено для сохранения последнего отправленного IR кода

        if need_update:
            # Установка режима работы, температуры, скорости вентилятора и swing
            ir_code = get_ir_code(args.target_mode, args.target_temperature, args.fan_speed, args.swing)
            if ir_code:
                log_message(client, "Отправка IR сигнала для обновления настроек...")
                if send_ir_signal(client, ir_code, MQTT_TOPIC_MODE, args.target_mode):
                    # Предсказанное состояние диммера после отправки IR кода
                    predicted_dimmer_state = not current_dimmer if current_dimmer is not None else None

                    # Обновляем соответствующие состояния
                    if args.target_mode:
                        current_mode = args.target_mode
                    if args.target_temperature is not None:
                        current_temperature = args.target_temperature
                    if args.fan_speed:
                        current_fan_speed = args.fan_speed
                    if args.swing:
                        current_swing = args.swing == "on"

                    last_ir_code = ir_code  # Сохраняем IR код
                else:
                    log_message(client, "Ошибка при отправке IR сигнала для обновления настроек.")
            else:
                log_message(client, "Ошибка: не найден сигнал для комбинации режим/температура/вентилятор/swing.")
        else:
            log_message(client, "Все параметры уже установлены, пропуск отправки сигнала.")
            # Предсказанное состояние диммера остается таким же
            predicted_dimmer_state = current_dimmer
            # Получаем IR код текущих настроек
            ir_code = get_ir_code(current_mode, current_temperature, current_fan_speed, current_swing)
            if ir_code:
                last_ir_code = ir_code
            else:
                log_message(client, "Ошибка: не найден сигнал для текущих настроек.")

        # Управление диммером
        if args.dimmer:
            if current_power:  # Проверяем, включен ли кондиционер
                desired_dimmer_state = args.dimmer == "on"

                if need_update and predicted_dimmer_state is not None:
                    # Если были обновления настроек и мы знаем предсказанное состояние диммера
                    if predicted_dimmer_state != desired_dimmer_state:
                        # Нужно отправить IR код еще раз
                        log_message(client, f"Отправка IR сигнала для изменения состояния диммера на: {args.dimmer}")
                        send_ir_signal(client, last_ir_code)
                        predicted_dimmer_state = not predicted_dimmer_state
                elif current_dimmer is not None:
                    # Если не было обновлений настроек, используем текущее состояние диммера
                    if current_dimmer != desired_dimmer_state:
                        # Нужно отправить IR код
                        log_message(client, f"Отправка IR сигнала для изменения состояния диммера на: {args.dimmer}")
                        send_ir_signal(client, last_ir_code)
                        predicted_dimmer_state = not current_dimmer
                else:
                    log_message(client, "Состояние диммера неизвестно, невозможно определить необходимость отправки сигнала.")

                # Обновляем состояние диммера
                if predicted_dimmer_state is not None:
                    current_dimmer = predicted_dimmer_state
                    client.publish(MQTT_TOPIC_DIMMER, args.dimmer, qos=MQTT_QOS, retain=True)
                    log_message(client, f"Опубликовано обновленное состояние диммера '{args.dimmer}' в топик: {MQTT_TOPIC_DIMMER}")
            else:
                log_message(client, "Кондиционер выключен. Пропуск отправки сигнала для диммера.")

    finally:
        remove_lock()
        log_message(client, "Скрипт завершен успешно.")
        client.loop_stop()

if __name__ == "__main__":
    main()
