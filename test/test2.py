#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr  4 09:18:06 2023

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

# velocity = 12.06/3.6

# print('drag power',bonk.getDragPower(environment, athlete, velocity))
# print('flat power',bonk.getFlatPower(environment, athlete, velocity, 0))
# print('slope power',bonk.getSlopePower(environment, athlete, segment, velocity))

bostonCourse = bonk.readCourse('marathonUpDown.csv','Flat Marathon')
environment = bonk.Environment(temperature = 5, humidity = 0, wind = 0, altitude = 0, body = 1)
athlete = bonk.Athlete(mass = 64, Ecor = 0.98, fatigueResistanceCoef = 0.07, Cd = 0.5*8, frontalArea = 0.5, vo2maxPower=5.42*64, glucoseConsumption = 60, startingGlycogen = 1500,temp=environment.temperature)
bostonPerformance = bonk.Performance(environment,athlete,bostonCourse)
p = 287.25
time = bostonPerformance.getDuration(p)
print(time)
print(bostonPerformance.speeds)
print(bostonPerformance.durations)
print(np.average(bostonPerformance.speeds))
print(np.divide(bostonPerformance.durations,bostonPerformance.speeds))
print(bostonPerformance.segDistances)
print(np.divide(bostonPerformance.segDistances,bostonPerformance.speeds))
segDurations = (np.sum(np.divide(bostonPerformance.segDistances,bostonPerformance.speeds)))
energy = np.multiply(segDurations,p)
print(energy)
print(energy/time)
v = bostonPerformance.distance/bostonPerformance.duration
print(v)
for segmentPerformance in bostonPerformance.segmentPerformances:
    print('segEnergy', segmentPerformance.dragEnergy, segmentPerformance.slopeEnergy, segmentPerformance.flatEnergy, segmentPerformance.energy)
    
print(bostonPerformance.getNormalizedPower())

bostonCourse = bonk.readCourse('marathonUpDown.csv','Flat Marathon')
environment = bonk.Environment(temperature = 5, humidity = 0, wind = 0, altitude = 0, body = 1)
athlete = bonk.Athlete(mass = 64, Ecor = 0.98, fatigueResistanceCoef = 0.07, Cd = 0.5*8, frontalArea = 0.5, vo2maxPower=5.42*64, glucoseConsumption = 60, startingGlycogen = 1500,temp=environment.temperature)
bostonPerformance = bonk.Performance(environment,athlete,bostonCourse)
p = 287.25
time, v, power = bostonPerformance.getEvenSplitRaceTime()
print(time)
print(bostonPerformance.speeds)
print(bostonPerformance.durations)
print(np.average(bostonPerformance.speeds))
print(np.divide(bostonPerformance.durations,bostonPerformance.speeds))
print(bostonPerformance.segDistances)
print(np.divide(bostonPerformance.segDistances,bostonPerformance.speeds))
segDurations = (np.sum(np.divide(bostonPerformance.segDistances,bostonPerformance.speeds)))
energy = np.multiply(segDurations,p)
print(energy)
print(energy/time)
v = bostonPerformance.distance/bostonPerformance.duration
print(v)
for segmentPerformance in bostonPerformance.segmentPerformances:
    print('segEnergy', segmentPerformance.dragEnergy, segmentPerformance.slopeEnergy, segmentPerformance.flatEnergy, segmentPerformance.energy)
    
print(bostonPerformance.getNormalizedPower())