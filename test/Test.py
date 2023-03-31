# -*- coding: utf-8 -*-
"""
Created on Thu Mar 30 23:13:09 2023

@author: jackm_000
"""
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

course = bonk.readCourse('testCourseFile.csv')

course.plotProfile()

print('air density ', environment.airDensity)

performance = bonk.Performance(environment,athlete,course)
performance.plotPowerDistance()
performance.plotPowerDuration()

#getV(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, power)
v = bonk.getV(1.226, 0.24, 1, 0, 0.98, 0, 70, 9.81, 235)
print('velocity ',v)
#getP(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, velocity)
print('power ', bonk.getP(1.226, 0.24, 1, 0, 0.98, 0, 70, 9.81, v))
print('time 42.195k ', 42195/(3.348))