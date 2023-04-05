#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr  4 12:22:06 2023

@author: jack
"""
import numpy as np
import sys
import os
module_path = os.path.abspath(os.path.join('../source'))
if module_path not in sys.path:
    sys.path.append(module_path)
import bonk
from enum import Enum
from scipy import interpolate

Body = Enum('Body',['Earth','Mars','Moon'])

environment = bonk.Environment(altitude = 3000, body=1)
#environment = bonk.Environment(body=Body.Earth)
#environment = bonk.Environment(body=Body.Mars)
athlete = bonk.Athlete()
segment = bonk.Segment()

bostonCourse = bonk.readCourse('bostonCourse.csv','Boston Marathon')
environment = bonk.Environment(temperature = 5, humidity = 0, wind = 0, altitude = 0, body = 1)
athlete = bonk.Athlete(mass = 64, Ecor = 0.98, fatigueResistanceCoef = 0.07, Cd = 0.5, frontalArea = 0.5, vo2maxPower=5.42*64, glucoseConsumption = 60, startingGlycogen = 1500,temp=environment.temperature)
bostonPerformance = bonk.Performance(environment,athlete,bostonCourse)

raceTime, power = bostonPerformance.getRaceTime()


print(bostonPerformance.averagePower)

h, m, s = bonk.getTime(raceTime)
out = 'Race time: {:02d}:{:02d}:{:02d}'
print(out.format(int(h),int(m),int(s)))



bostonPerformance.plotPowerDistance()
bostonPerformance.plotVDistance()

bostonPerformance.getMileSplits(relative = 0)
print(bostonPerformance.getNormalizedPower())