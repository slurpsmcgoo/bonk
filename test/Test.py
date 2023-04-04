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
from enum import Enum

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

bostonCourse = bonk.readCourse('bostonCourse.csv','boston')




flatCourse = bonk.readCourse('flatMarathon.csv','flat')
slopeSweep = bonk.readCourse('slopeSweep.csv','slope')
updownCourse = bonk.readCourse('marathonUpDown.csv','updown')
woodstockCourse = bonk.readCourse('woodstockCourse.csv','woodstock')

bostonCourse.plotProfile()
woodstockCourse.plotProfile()

print('air density ', environment.airDensity)



#getV(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, power)
v = bonk.getV(1.226, 0.24, 1, 0, 0.98, 0, 70, 9.81, 235)

#getP(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, velocity)


# duration, p = bonk.powerDuration(42195, 3600*2+60*39,1.226, 0.24, 1, 0, 0.98, 0, 70, 9.81)
# print(np.interp(300,p,duration))
# print(np.interp(12603,duration,p))

powerDuration = bonk.PowerDuration()
powerDuration.plotPowerDuration()
powerDuration.plotDurationPower()

raceTime, power = bonk.getRaceTime(environment,athlete,bostonCourse,powerDuration,errorLim = 0.001,powerGuess = 300)
print('Boston: ')
print('race time ',raceTime, ' power ', power)
h, m, s = bonk.getTime(raceTime)
print('h ',h, 'm ',m ,'s ',s)

performance = bonk.Performance(environment,athlete,bostonCourse)
performance.getDuration(power)
performance.plotPowerDistance()
performance.plotPowerDuration()
performance.plotVDistance()

raceTime, power = bonk.getRaceTime(environment,athlete,flatCourse,powerDuration,errorLim = 0.001,powerGuess = 300)
print('Flat: ')
print('race time ',raceTime, ' power ', power)
h, m, s = bonk.getTime(raceTime)
print('h ',h, 'm ',m ,'s ',s)

performance1 = bonk.Performance(environment,athlete,flatCourse)
performance1.getDuration(power)
performance1.plotPowerDistance()
performance1.plotPowerDuration()
performance1.plotVDistance()

# raceTime, power = bonk.getRaceTime(environment,athlete,slopeSweep,powerDuration,errorLim = 0.001,powerGuess = 300)
# print('race time ',raceTime, ' power ', power)

# performance2 = bonk.Performance(environment,athlete,slopeSweep)
# performance2.getDuration(power)
# performance2.plotPowerDistance()
# performance2.plotPowerDuration()
# performance2.plotVDistance()

raceTime, power = bonk.getRaceTime(environment,athlete,updownCourse,powerDuration,errorLim = 0.001,powerGuess = 300)
print('10% up / down: ')
print('race time ',raceTime, ' power ', power)
h, m, s = bonk.getTime(raceTime)
print('h ',h, 'm ',m ,'s ',s)

updown = bonk.Performance(environment,athlete,updownCourse)
updown.getDuration(power)
updown.plotPowerDistance()
updown.plotPowerDuration()
updown.plotVDistance()