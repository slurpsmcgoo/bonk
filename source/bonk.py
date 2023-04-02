# =============================================================================
# Performance is made up of performance in each segment of a course
# 
# 
# =============================================================================

from enum import Enum
import csv
import matplotlib.pyplot as plt
import math
import numpy as np

Body = Enum('Body',['Earth','Mars','Moon'])

class Athlete:
    # Athlete contains the properties of a runner
    def __init__(self, mass = 70, Ecor = 0.98, fatigueResistanceCoef = 0.07, Cd = 0.5, frontalArea = 0.5, vo2maxPower=347):
        self.mass = mass
        self.fatigueResistanceCoef = fatigueResistanceCoef
        self.Cd = Cd
        self.frontalArea = frontalArea
        self.Ecor = Ecor
        self.vo2maxPower = vo2maxPower
        
    
    def getRunningPowerDuration(self):
        self.runningPowerDistribution = [500, 400, 300, 200, 100]
	
    def getDetailedRunningEnergy(self):
        self.massUpperLeg = 5
        self.massLowerLeg = 3
        self.massTorsoHead = 40
        self.massArm = 3
        self.massShoe = 0.25
        self.massClothing = 0.3
        self.mass = self.massUpperLeg*2 + self.massLowerLeg*2 + self.massTorsoHead + self.massArm*2 + self.massShoe*2 + self.massClothing
		
	
class Environment:
    # Environment is contains global properties like temp and humidity, for now we assume constant
    def __init__(self,temperature = 10, humidity = 20, wind = 0, gravity = 9.81, altitude = 0, body = 1):
        self.temperature = temperature
        self.tempK = temperature+273
        self.humidity = humidity
        self.wind = wind
        self.gravity = gravity
        self.altitude = altitude
        self.body = body
        if self.body == 1:
            self.density = 1.205 #kg/m3
            self.p0 = 101300 #Pa
            self.R = 8.314 # kJ/kmol/k
            self.M = 28.97 #g/mol
            self.airDensity = self.getAirDensity(altitude)
            self.gravity = 9.81
        elif self.body == 2:
            self.airDensity = 0.000001
            self.density = self.airDensity
            self.gravity = 1.62
        elif self.body == 3:
            self.airDensity = 0.02
            self.gravity = 3.721
            self.density = self.airDensity
        else:
            print('error: no known body')
    def getAirDensity(self,altitude):
        self.airPressure = self.p0*math.exp(-self.M*self.gravity*altitude/self.R/self.tempK)
        return (self.airPressure*self.M)/(self.R*self.tempK)/1000
            
            
        
class Segment:
    # Segment is an element of a course
    def __init__(self,number=1, length = 1609, elevGain = 100, EcorMod = 0, surfaceTechMod = 0):
        self.number = number
        self.length = length
        self.elevGain = elevGain
        self.slope = elevGain/length
        self.EcorMod = EcorMod
        self.surfaceTechMod = surfaceTechMod
        self.x0 = 0
        self.x1 = length
        self.y0 = 0
        self.y1 = elevGain
        
    def setValues(self,number, length, slope, EcorMod, surfaceTechMod):
        self.number = number
        self.length = length
        self.slope = slope
        self.EcorMod = EcorMod
        self.surfaceTechMod = surfaceTechMod
    
    def setStart(self,startX,startY):
        self.x0 += startX
        self.x1 += startX
        self.y0 += startY
        self.y1 += startY

        
class Course:
    # Course is basically a collection of segments
    def __init__(self,segments):
        self.segments = segments
        x = 0
        y = 0
        for segment in self.segments:
            segment.setStart(x,y)
            x += segment.length
            y += segment.elevGain

    def plotProfile(self):
        fig, ax = plt.subplots(figsize=(5, 3))
        x = 0
        y = 0
        for segment in self.segments:
            segment.setStart(x,y)
            ax.plot([segment.x0, segment.x1],[segment.y0, segment.y1])
            x += segment.length
            y += segment.elevGain
        ax.set_title('Course Elevation')
        #ax.legend(loc='upper left')
        ax.set_xlabel('Distance (m)')
        ax.set_ylabel('Elevation (m)')
        fig.tight_layout()
	

class Performance:
    # Performance is a combination of an athlete, environment, and course
    # Performance is the sum of segment performances of a course
    def __init__(self,environment,athlete,course):
        #init
        self.environment = environment
        self.athlete = athlete
        self.course = course
        self.segmentPerformances = []

            
    def getDuration(self,power):
        self.duration = 0
        for segment in self.course.segments:
            segmentPerformance = SegmentPerformance(segment,self.athlete,self.environment,power)
            #segmentPerformance.getTimeFromPower(self.athlete,self.environment,power)
            segmentPerformance.setStart(self.duration)
            self.segmentPerformances.append(segmentPerformance)
            self.duration += segmentPerformance.duration
        return self.duration
            
    def plotPowerDistance(self):
        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        segmentsX = []
        segmentsPower = []
        segmentsDragPower = []
        segmentsFlatPower = []
        segmentsSlopePower = []
        for segmentPerformance in self.segmentPerformances:
            segmentsX.append(segmentPerformance.segment.x0)
            segmentsX.append(segmentPerformance.segment.x1)
            segmentsPower.append(segmentPerformance.power)
            segmentsPower.append(segmentPerformance.power)
            segmentsDragPower.append(segmentPerformance.dragPower)
            segmentsDragPower.append(segmentPerformance.dragPower)
            segmentsFlatPower.append(segmentPerformance.flatPower)
            segmentsFlatPower.append(segmentPerformance.flatPower)
            segmentsSlopePower.append(segmentPerformance.slopePower)
            segmentsSlopePower.append(segmentPerformance.slopePower)
            
        self.ax.plot(segmentsX,segmentsPower,label='total power',color='red')
        self.ax.plot(segmentsX,segmentsFlatPower,label='base power',color='blue')
        self.ax.plot(segmentsX,segmentsDragPower,label='drag power',color='green')
        self.ax.plot(segmentsX,segmentsSlopePower,label='slope power',color='orange')
        
        self.ax.set_title('Power per segment')
        self.ax.legend(loc='upper left')
        self.ax.set_xlabel('Distance (m)')
        self.ax.set_ylabel('Power (w)')
        self.fig.tight_layout()
        
    def plotVDistance(self):
        self.fig3, self.ax3 = plt.subplots(figsize=(5, 3))
        segmentsX = []
        segmentsV = []

        for segmentPerformance in self.segmentPerformances:
            segmentsX.append(segmentPerformance.segment.x0)
            segmentsX.append(segmentPerformance.segment.x1)
            segmentsV.append(segmentPerformance.v)
            segmentsV.append(segmentPerformance.v)
        
        self.ax3.plot(segmentsX,segmentsV)
        self.ax3.set_title('Power per segment')
        #self.ax3.legend(loc='upper left')
        self.ax3.set_xlabel('Distance (m)')
        self.ax3.set_ylabel('V (m/s)')
        self.fig3.tight_layout()


    def plotPowerDuration(self):
        self.fig1, self.ax1 = plt.subplots(figsize=(5, 3))
        segmentsX = []
        segmentsPower = []
        segmentsDragPower = []
        segmentsFlatPower = []
        segmentsSlopePower = []
        for segmentPerformance in self.segmentPerformances:
            segmentsX.append(segmentPerformance.time0)
            segmentsX.append(segmentPerformance.time1)
            segmentsPower.append(segmentPerformance.power)
            segmentsPower.append(segmentPerformance.power)
            segmentsDragPower.append(segmentPerformance.dragPower)
            segmentsDragPower.append(segmentPerformance.dragPower)
            segmentsFlatPower.append(segmentPerformance.flatPower)
            segmentsFlatPower.append(segmentPerformance.flatPower)
            segmentsSlopePower.append(segmentPerformance.slopePower)
            segmentsSlopePower.append(segmentPerformance.slopePower)
            
        self.ax1.plot(segmentsX,segmentsPower,label='total power',color='red')
        self.ax1.plot(segmentsX,segmentsFlatPower,label='base power',color='blue')
        self.ax1.plot(segmentsX,segmentsDragPower,label='drag power',color='green')
        self.ax1.plot(segmentsX,segmentsSlopePower,label='slope power',color='orange')
        
        self.ax1.set_title('Power per segment')
        self.ax1.legend(loc='upper left')
        self.ax1.set_xlabel('Duration (s)')
        self.ax1.set_ylabel('Power (w)')
        self.fig1.tight_layout()


class SegmentPerformance:
    def __init__(self,segment, athlete, environment, power):
        self.segment = segment
        self.duration = self.getTimeFromPower(athlete, environment, power)
        self.velocity = self.v
        self.dragPower = self.getDragPower(environment,athlete,self.v)
        self.slopePower = self.getSlopePower(environment,athlete,segment,self.v)
        self.flatPower = self.getFlatPower(environment,athlete,self.v,segment.EcorMod)
        self.power = self.dragPower+self.slopePower+self.flatPower
        self.duration = self.getDuration(segment.length,self.v)
        self.time0 = 0
        self.time1 = self.duration
        
    def getTimeFromPower(self,athlete,environment,power):
        self.v = getV(environment.airDensity, athlete.Cd, athlete.frontalArea, environment.wind, athlete.Ecor, self.segment.slope, athlete.mass, environment.gravity, power)
        self.duration = self.segment.length/self.v
        self.time1 = self.duration
        return self.duration
        
    def getSlopePower(self,environment, athlete, segment, velocity):
        eta = (45.6+1.1622*segment.slope*100)/100
        slopePower = athlete.mass*velocity*environment.gravity*(segment.slope)*eta
        return slopePower	
    	
    def getDragPower(self,environment, athlete, velocity):
        dragPower = 0.5*environment.density*athlete.Cd*athlete.frontalArea*(velocity+environment.wind)**2*velocity
        return dragPower
    
    def getFlatPower(self,environment, athlete, velocity, EcorMod):
        flatPower = athlete.mass*athlete.Ecor*environment.gravity/9.81*(1+EcorMod)*velocity
        return flatPower
    
    def getDuration(self,length,velocity):
        return length/velocity
    def setStart(self,x):
        self.time0 += x
        self.time1 += x


def getSlopePower(environment, athlete, segment, velocity):
    eta = (45.6+1.1622*segment.slope*100)/100
    slopePower = athlete.mass*velocity*environment.gravity*(segment.slope)*eta
    return slopePower	
	
def getDragPower(environment, athlete, velocity):
    dragPower = 0.5*environment.density*athlete.Cd*athlete.frontalArea*(velocity+environment.wind)**2*velocity
    return dragPower

def getFlatPower(environment, athlete, velocity, EcorMod):
    flatPower = athlete.mass*athlete.Ecor*environment.gravity/9.81*velocity
    return flatPower

def readCourse(pathToCourseFile):
    # read in segments line by line and create course object
    segments = []
    with open(pathToCourseFile, newline='') as csvfile:
    #elements of description:
        #number length slope EcorMod surfaceTechMod
        courseDescription = csv.DictReader(csvfile, delimiter=' ')
    
        for seg in courseDescription:
            number = float(seg['number'])
            length = float(seg['length'])
            slope = float(seg['slope'])
            EcorMod = float(seg['EcorMod'])
            surfaceTechMod = float(seg['surfaceTechMod'])
            #print(number, length, slope, EcorMod, surfaceTechMod)
            segment = Segment(number, length, slope, EcorMod, surfaceTechMod)
            segments.append(segment)
        course = Course(segments)
        return course

def getV(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, power):
    Ecor = Ecor*gravity/9.81
    # slope is a decimal value
    # given a power, solve for velocity
    eta = (45.6+1.1622*slope*100)/100
    # a = 0.5*airDensity*Cd*frontalArea
    # b = 2*0.5*airDensity*Cd*frontalArea*wind
    # c = 0.5*airDensity*Cd*frontalArea*wind**2+Ecor*mass*math.cos(math.atan(slope))+eta*mass*gravity*math.sin(math.atan(slope))
    # d = power
    # part1 = (((-b**3/(27*a**3))+(b*c/(6*a**2))-(d/(2*a)))+(((-b**3/(27*a**3))+(b*c/(6*a**2))-(d/(2*a)))**2+((c/(3*a))-(b**2/(9*a**2)))**3)**0.5)**(1/3)
    # part2 = (((-b**3/(27*a**3))+(b*c/(6*a**2))-(d/(2*a)))-(((-b**3/(27*a**3))+(b*c/(6*a**2))-(d/(2*a)))**2+((c/(3*a))-(b**2/(9*a**2)))**3)**0.5)**(1/3)
    # part3 = b/(3*a)
    
    c = Ecor
    d = airDensity
    w = wind
    m = mass
    n = eta
    s = slope
    p = power
    g = gravity
    q = frontalArea*Cd
    v=(0.26457*(36*c*d**2*m*q**2*w+math.sqrt(4*(6*c*d*m*q-d**2*q**2*w**2+6*d*g*n*m*q*s)**3+(36*c*d**2*m*q**2*w+2*d**3*q**3*w**3+36*d**2*g*n*m*q**2*s*w+54*d**2*p*q**2)**2)+2*d**3*q**3*w**3+36*d**2*g*n*m*q**2*s*w+54*d**2*p*q**2)**(1/3))/(d*q)-(0.41997*(6*c*d*m*q-d**2*q**2*w**2+6*d*g*n*m*q*s))/(d*q*(36*c*d**2*m*q**2*w+math.sqrt(4*(6*c*d*m*q-d**2*q**2*w**2+6*d*g*n*m*q*s)**3+(36*c*d**2*m*q**2*w+2*d**3*q**3*w**3+36*d**2*g*n*m*q**2*s*w+54*d**2*p*q**2)**2)+2*d**3*q**3*w**3+36*d**2*g*n*m*q**2*s*w+54*d**2*p*q**2)**(1/3))-0.66667*w
    return v

def getP(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, velocity):
    Ecor = Ecor*gravity/9.81
    eta = (45.6+1.1622*slope*100)/100
    return Ecor*mass*velocity+0.5*airDensity*Cd*frontalArea*(velocity+wind)**2*velocity+slope*mass*gravity*velocity*eta

# def powerDuration(distance, time,airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity):
#     # given a base distance duration (race result) and a fatigue resistance, calculate velocity vs distance
#     # at each velocity, calculate power (from flat ground including air resistance - assuming typical race conditions)
#     # calculate duration from distance/velocity
#     # plot power vs duration
#     rF = 0.07
#     v0 = distance/time
#     d0 = distance
#     d = np.arange(1600,300000,10000)
#     v = v0*(d/d0)**-rF
#     print(v)
#     duration = np.divide(d,v)
#     p = []
#     for i in range(len(v)):
#         power = getP(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, v[i])
#         p.append(power)
#     p = np.asarray(p)
#     print(p)
#     plt.figure()
#     print(duration.size)
#     print(p.size)
#     plt.plot(duration,p)
#     return duration, p
    
class PowerDuration:
    def __init__(self, glucoseConsumption = 60, startingGlycogen = 3000, vo2maxPower = 347):
        self.metabolicEfficiency = 0.25
        self.glucoseConsumption = glucoseConsumption
        self.startingGlycogen = startingGlycogen
        self.vo2maxPower = vo2maxPower
        self.fractionVo2 = np.arange(0,105,5)/100
        self.fractionFTP = self.fractionVo2/1.13
        self.power = self.fractionVo2*self.vo2maxPower
        self.percentFat = np.asarray([100,97.5,95,92.5,90,88.75,87.5,81.25,75,70.5,66,61.5,57,51.5,46,40.5,35,28.75,22.5,16.25,10])/100
        self.percentGlucose = 1-self.percentFat
        self.powerFat = np.multiply(self.percentFat,self.power)
        self.powerGlucose = self.power-self.powerFat
        self.metabolicPowerFat = self.powerFat/self.metabolicEfficiency
        self.metabolicPowerGlucose = self.powerGlucose/self.metabolicEfficiency
        self.powerGlucoseConsumption = 4*4184*self.glucoseConsumption/3600 # convert g/h to watts
        a = 10e10 # no limit duration value
        self.durationUntilGlycogenDepletion = self.startingGlycogen*4184/(self.metabolicPowerGlucose-self.powerGlucoseConsumption)
        for i in range(len(self.durationUntilGlycogenDepletion)):
            if self.durationUntilGlycogenDepletion[i]<0:
                self.durationUntilGlycogenDepletion[i]=a
        self.durationFromEmpirical = np.asarray([a,a,a,a,a,a,a,a,a,a,a,a,a,a,a,a,16200,6600,3000,1200,600])
        self.durationEnergyLimited = np.minimum(self.durationFromEmpirical, self.durationUntilGlycogenDepletion)
        self.durationSleepLimited = np.asarray([a,a,a,a,a,a,a,a,a,1440,336,120,44.03988009,21.97936125,14.18897655,10.24099629,4.5,1.833333333,0.8333333333,0.3333333333,0.1666666667])*3600
        
        self.duration = np.minimum(self.durationEnergyLimited,self.durationSleepLimited)
    def getDuration(self,power):
        return np.interp(power,self.power,self.duration)
    def getPower(self,duration):
        return np.interp(duration,self.duration,self.power)
    def plotPowerDuration(self):
        self.fig1, self.ax1 = plt.subplots(figsize=(5, 3))
        self.ax1.plot(self.duration/3600,self.power,color='orange')
        self.ax1.set_title('Power vs Duration')
        self.ax1.set_xlabel('Duration (h)')
        self.ax1.set_ylabel('Power (w)')
        self.ax1.set_xlim(xmin=0,xmax=48)
        self.ax1.set_ylim(ymin=0,ymax=self.vo2maxPower*1.1)
        self.fig1.tight_layout()
    
    def plotDurationPower(self):
        self.fig2, self.ax2 = plt.subplots(figsize=(5, 3))
        self.ax2.plot(self.power,self.duration/3600,color='orange')
        self.ax2.set_title('Duration vs Power')
        self.ax2.set_ylabel('Duration (h)')
        self.ax2.set_xlabel('Power (w)')
        self.ax2.set_xlim(xmin=0,xmax=self.vo2maxPower*1.1)
        self.ax2.set_ylim(ymin=0,ymax=48)
        self.fig2.tight_layout()

# process to determine race time
# choose a 
# calculate race time
# if error(race time - duration) > errorLim , increase power by 0.1* errorFrac*power
# if error(race time - duration) < -errorLim, decrease power by 0.1*errorFrac*power

def getRaceTime(environment,athlete,course,powerDuration,errorLim = 0.0001,powerGuess = 300):
    segmentPerformances = []
    timeMissing = 1
    duration = 0
    while(timeMissing):
        if powerGuess > athlete.vo2maxPower or powerGuess < 100:
            print('failed')
            return duration, powerGuess
        duration = 0
        for segment in course.segments:
            segmentPerformance = SegmentPerformance(segment,athlete,environment,powerGuess)
            #segmentPerformance.getTimeFromPower(athlete,environment,powerGuess)
            segmentPerformance.setStart(duration)
            segmentPerformances.append(segmentPerformance)
            duration += segmentPerformance.duration
        #print('powerGuess ',powerGuess)
        #print('duration ', duration)
        limDuration = powerDuration.getDuration(powerGuess)
        #print('limduration ',limDuration)
        error = duration-limDuration
        errorFrac = error/duration
        #print('errorFrac ',errorFrac)
        if (errorFrac)>errorLim:
            powerGuess = powerGuess*(1-0.01*errorFrac)
        elif (errorFrac)<-errorLim:
            powerGuess = powerGuess*(1-0.01*errorFrac)
        else:
            return duration, powerGuess
        
def getTime(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return h, m, s