# -*- coding: utf-8 -*-
"""
Created on Thu Mar 30 23:13:09 2023

@author: jackm_000
"""
import numpy as np
import sys
import os
module_path = os.path.abspath(os.path.join('../source'))
if module_path not in sys.path:
    sys.path.append(module_path)
import bonk

environment = bonk.Environment()
athlete = bonk.Athlete()
segment = bonk.Segment()

velocity = 12.06/3.6

print('drag power',bonk.getDragPower(environment, athlete, velocity))
print('flat power',bonk.getFlatPower(environment, athlete, velocity, 0))
print('slope power',bonk.getSlopePower(environment, athlete, segment, velocity))

course = bonk.readCourse('bostonCourse.csv')

course.plotProfile()

print('air density ', environment.airDensity)



#getV(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, power)
v = bonk.getV(1.226, 0.24, 1, 0, 0.98, 0, 70, 9.81, 235)
print('velocity ',v)
#getP(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, velocity)
print('power ', bonk.getP(1.226, 0.24, 1, 0, 0.98, 0, 70, 9.81, v))
print('time 42.195k ', 42195/(3.348))

# duration, p = bonk.powerDuration(42195, 3600*2+60*39,1.226, 0.24, 1, 0, 0.98, 0, 70, 9.81)
# print(np.interp(300,p,duration))
# print(np.interp(12603,duration,p))

powerDuration = bonk.PowerDuration()
powerDuration.plotPowerDuration()
powerDuration.plotDurationPower()

raceTime, power = bonk.getRaceTime(environment,athlete,course,powerDuration,errorLim = 0.001,powerGuess = 300)
print('race time ',raceTime, ' power ', power)

performance = bonk.Performance(environment,athlete,course)
performance.getDuration(power)
performance.plotPowerDistance()
performance.plotPowerDuration()