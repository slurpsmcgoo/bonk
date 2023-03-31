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
    def __init__(self, mass = 70, Ecor = 0.98, fatigueResistanceCoef = 0.07, Cd = 0.5, frontalArea = 0.5):
        self.mass = mass
        self.fatigueResistanceCoef = fatigueResistanceCoef
        self.Cd = Cd
        self.frontalArea = frontalArea
        self.Ecor = Ecor
        
    
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
    def __init__(self,temperature = 10, humidity = 20, wind = 2, gravity = 9.81, altitude = 0, body = Body.Earth):
        self.temperature = temperature
        self.tempK = temperature+273
        self.humidity = humidity
        self.wind = wind
        self.gravity = gravity
        self.altitude = altitude
        self.body = body
        if self.body == Body.Earth:
            self.density = 1.205 #kg/m3
            self.p0 = 101300 #Pa
            self.R = 8.314 # kJ/kmol/k
            self.M = 28.97 #g/mol
            self.airDensity = self.getAirDensity(altitude)
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
        ax.legend(loc='upper left')
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
        self.duration = 0
        for segment in course.segments:
            segmentPerformance = SegmentPerformance(segment,athlete,environment)
            segmentPerformance.setStart(self.duration)
            self.segmentPerformances.append(segmentPerformance)
            self.duration += segmentPerformance.duration
            
            
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
    def __init__(self,segment, athlete, environment, velocity = 12.06/3.6):
        self.segment = segment
        self.velocity = velocity
        self.dragPower = self.getDragPower(environment,athlete,velocity)
        self.slopePower = self.getSlopePower(environment,athlete,segment,velocity)
        self.flatPower = self.getFlatPower(environment,athlete,velocity,segment.EcorMod)
        self.power = self.dragPower+self.slopePower+self.flatPower
        self.duration = self.getDuration(segment.length,velocity)
        self.time0 = 0
        self.time1 = self.duration
        
        
    def getSlopePower(self,environment, athlete, segment, velocity):
        eta = (45.6-1.1622*segment.slope*100)/100
        slopePower = athlete.mass*velocity*environment.gravity*(segment.slope)*eta
        return slopePower	
    	
    def getDragPower(self,environment, athlete, velocity):
        dragPower = 0.5*environment.density*athlete.Cd*athlete.frontalArea*(velocity+environment.wind)**2*velocity
        return dragPower
    
    def getFlatPower(self,environment, athlete, velocity, EcorMod):
        flatPower = athlete.mass*athlete.Ecor*(1+EcorMod)*velocity
        return flatPower
    
    def getDuration(self,length,velocity):
        return length/velocity
    def setStart(self,x):
        self.time0 += x
        self.time1 += x


def getSlopePower(environment, athlete, segment, velocity):
    eta = (45.6-1.1622*segment.slope*100)/100
    slopePower = athlete.mass*velocity*environment.gravity*(segment.slope)*eta
    return slopePower	
	
def getDragPower(environment, athlete, velocity):
    dragPower = 0.5*environment.density*athlete.Cd*athlete.frontalArea*(velocity+environment.wind)**2*velocity
    return dragPower

def getFlatPower(environment, athlete, velocity, EcorMod):
    flatPower = athlete.mass*athlete.Ecor*velocity
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
            print(number, length, slope, EcorMod, surfaceTechMod)
            segment = Segment(number, length, slope, EcorMod, surfaceTechMod)
            segments.append(segment)
        course = Course(segments)
        return course

def getV(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, power):
    # slope is a decimal value
    # given a power, solve for velocity
    eta = (45.6-1.1622*slope*100)/100
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
    eta = (45.6-1.1622*slope*100)/100
    return Ecor*mass*velocity+0.5*airDensity*Cd*frontalArea*(velocity+wind)**2*velocity+slope*mass*gravity*velocity*eta

def powerDuration(distance, time,airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity):
    # given a base distance duration (race result) and a fatigue resistance, calculate velocity vs distance
    # at each velocity, calculate power (from flat ground including air resistance - assuming typical race conditions)
    # calculate duration from distance/velocity
    # plot power vs duration
    rF = 0.07
    v0 = distance/time
    d0 = distance
    d = np.arange(1600,300000,10000)
    v = v0*(d/d0)**-rF
    print(v)
    duration = np.divide(d,v)
    p = []
    for i in range(len(v)):
        power = getP(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, v[i])
        p.append(power)
    p = np.asarray(p)
    print(p)
    plt.figure()
    print(duration.size)
    print(p.size)
    plt.plot(duration,p)
    return duration, p
    
class powerDurationFromEnergy:
    startingGlycogen = 750 #g
    
    
    