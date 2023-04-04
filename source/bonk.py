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
from scipy import interpolate

Body = Enum('Body',['Earth','Mars','Moon'])
plotSize = (12, 8)

#ax1.grid(color='lightgrey', linestyle='-', linewidth=1)

class Athlete:
    # Athlete contains the properties of a runner
    def __init__(self, mass = 70, Ecor = 0.98, fatigueResistanceCoef = 0.07, Cd = 0.5, frontalArea = 0.5, vo2maxPower=347, glucoseConsumption = 60, startingGlycogen = 1500,temp=5,altitude=0):
        self.mass = mass
        self.fatigueResistanceCoef = fatigueResistanceCoef
        self.Cd = Cd
        self.frontalArea = frontalArea
        self.Ecor = Ecor
        self.vo2maxPower = vo2maxPower
        self.powerDuration = PowerDuration(glucoseConsumption = glucoseConsumption, startingGlycogen = startingGlycogen, vo2maxPower=vo2maxPower,temp=temp, altitude=altitude)
        
        
    
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
    def __init__(self,temperature = 5, humidity = 0, wind = 0, altitude = 0, body = 1):
        self.temperature = temperature
        self.tempK = temperature+273
        self.humidity = humidity
        self.wind = wind
        self.altitude = altitude
        self.body = body
        if self.body == 1:
            self.density = 1.205 #kg/m3
            self.p0 = 101300 #Pa
            self.R = 8.314 # kJ/kmol/k
            self.M = 28.97 #g/mol
            self.gravity = 9.81
            self.airDensity = self.getAirDensity(altitude)
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
        self.airPressure = self.p0*math.exp(-self.M/1000*self.gravity*altitude/self.R/self.tempK)
        #print(self.airPressure)
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
    def __init__(self,segments,name):
        self.segments = segments
        x = 0
        y = 0
        for segment in self.segments:
            segment.setStart(x,y)
            x += segment.length
            y += segment.elevGain
        self.name = name

    def plotProfile(self):
        fig, ax = plt.subplots(figsize=(plotSize))#figsize=(7, 4)
        #x = 0
        #y = 0
        for segment in self.segments:
            #segment.setStart(x,y)
            ax.plot([segment.x0/1000, segment.x1/1000],[segment.y0, segment.y1],'cornflowerblue')
            #x += segment.length
            #y += segment.elevGain
        ax.set_title(self.name)
        #ax.legend(loc='upper left')
        ax.set_xlabel('Distance (km)')
        ax.set_ylabel('Elevation (m)')
        ax.grid(color='lightgrey', linestyle='-', linewidth=1)
        #fig.tight_layout()
	

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
        self.power = 0
        self.powerGuess = 0
        self.distance = 0
        self.interpDone = 0
        
    def getNormalizedPower(self,order=4):
        #samplingWindow = 30.0 #seconds
        #powers = []
        #if self.interpDone == 0:
        #    self.f = interpolate.interp1d(self.durations,self.powers,kind='nearest-up',bounds_error=False,fill_value=self.powers[0])
        #self.interpDone = 1
        #print(self.durations)
        #for i in range(int(self.duration/samplingWindow)): # loop through each 30 second section
            #power = self.f(samplingWindow/2+i*samplingWindow)
            
            #print('interpolated power: ',power,' at time ',i*samplingWindow+samplingWindow/2)
            #powerRaised = power**order
            #powers.append(powerRaised)
        #print('powers',self.powers)
        powersRaised = np.power(self.powers,order)
        #print('powersraised',powersRaised)
        #normForDuration
        timeFactor = np.divide(self.segDurations,self.duration)
        #powersRaised = np.multiply(powersRaised,timeFactor)
        #print('normed',powersRaised)
        avgPowerRaised = np.average(powersRaised,weights=timeFactor)
        #print('averageRaised',avgPowerRaised)
        normalizedPower = avgPowerRaised**(1/order)
        #print('normalized',normalizedPower)
        return normalizedPower
            
            

    def getMileSplits(self,relative=0):
        previousTime = 0
        self.getDuration(self.power)
        avgSpeed = self.distance/self.duration
        avgMileTime = 1609.0/avgSpeed
        for i in range(int(self.distance/1609)): # loop through miles
            time = np.interp((i+1)*1609,self.distances,self.durations)
            mileSplit = (time-previousTime)
            
            m, s = divmod(mileSplit, 60)
            mile = i+1
            m = int(m)
            s = int(s)
            if(relative==1):
                out = 'Mile: {:02d} - {:.2f}'
                print(out.format(mile,(time-previousTime)/avgMileTime))
            else:
                out = 'Mile: {:02d} - {:02d}:{:02d}'
                print(out.format(mile,m,s))
            previousTime = time
            
    def getMileSplitsV(self,relative=0):
        previousTime = 0
        self.getDurationV(self.v)
        avgSpeed = self.distance/self.duration
        avgMileTime = 1609.0/avgSpeed
        for i in range(int(self.distance/1609)): # loop through miles
            time = np.interp((i+1)*1609,self.distances,self.durations)
            mileSplit = (time-previousTime)
            
            m, s = divmod(mileSplit, 60)
            mile = i+1
            m = int(m)
            s = int(s)
            if(relative==1):
                out = 'Mile: {:02d} - {:.2f}'
                print(out.format(mile,(time-previousTime)/avgMileTime))
            else:
                out = 'Mile: {:02d} - {:02d}:{:02d}'
                print(out.format(mile,m,s))
            previousTime = time
        
            
    def getDuration(self,power):
        self.duration = 0
        self.durations = []
        self.distances = []
        self.speeds = []
        self.segDistances = []
        self.segDurations = []
        self.segmentPerformances = []
        self.powers = []
        self.distance = 0
        self.energy = 0
        self.averagePower = 0
        self.power = power
        for segment in self.course.segments:
            segmentPerformance = SegmentPerformance(segment,self.athlete,self.environment)
            segmentPerformance.getTimeFromPower(self.athlete,self.environment,power)
            segmentPerformance.setStart(self.duration)
            self.segDistances.append(segment.length)
            self.segmentPerformances.append(segmentPerformance)
            self.duration += segmentPerformance.duration
            self.distance += segmentPerformance.segment.length
            self.durations.append(self.duration)
            self.distances.append(self.distance)
            self.speeds.append(segmentPerformance.distance/segmentPerformance.duration)
            self.segDurations.append(segmentPerformance.duration)
            self.powers.append(power)
        self.energy = np.sum(np.multiply(power, self.segDurations))
        self.averagePower = self.energy/self.duration
        return self.duration
    
    def getDurationV(self,v):
        self.duration = 0
        self.durations = []
        self.distances = []
        self.powers = []
        self.segDistances = []
        self.segDurations = []
        self.segmentPerformances = []
        self.distance = 0
        self.energy = 0
        self.averagePower = 0
        self.v = v
        self.speeds = []
        for segment in self.course.segments:
            segmentPerformance = SegmentPerformance(segment,self.athlete,self.environment)
            segmentPerformance.getPowerFromV(self.athlete,self.environment,v)
            segmentPerformance.setStart(self.duration)
            self.segDistances.append(segment.length)
            self.segmentPerformances.append(segmentPerformance)
            self.duration += segmentPerformance.duration
            self.distance += segmentPerformance.segment.length
            self.durations.append(self.duration)
            self.distances.append(self.distance)
            self.powers.append(segmentPerformance.power)
            self.segDurations.append(segmentPerformance.duration)
            self.speeds.append(v)
        self.energy = np.sum(np.multiply(self.powers, self.segDurations))
        self.averagePower = self.energy/self.duration
        return self.duration
            
    def plotPowerDistance(self):
        self.fig, self.ax = plt.subplots(figsize=plotSize)
        segmentsX = []
        segmentsPower = []
        segmentsDragPower = []
        segmentsFlatPower = []
        segmentsSlopePower = []
        for segmentPerformance in self.segmentPerformances:
            segmentsX.append(segmentPerformance.segment.x0/1000)
            segmentsX.append(segmentPerformance.segment.x1/1000)
            segmentsPower.append(segmentPerformance.power)
            segmentsPower.append(segmentPerformance.power)
            segmentsDragPower.append(segmentPerformance.dragPower)
            segmentsDragPower.append(segmentPerformance.dragPower)
            segmentsFlatPower.append(segmentPerformance.flatPower)
            segmentsFlatPower.append(segmentPerformance.flatPower)
            segmentsSlopePower.append(segmentPerformance.slopePower)
            segmentsSlopePower.append(segmentPerformance.slopePower)
            
        self.ax.plot(segmentsX,segmentsPower,label='total power')
        self.ax.plot(segmentsX,segmentsFlatPower,label='base power')
        self.ax.plot(segmentsX,segmentsDragPower,label='drag power')
        self.ax.plot(segmentsX,segmentsSlopePower,label='slope power')
        
        self.ax.set_title('Power vs. Distance')
        self.ax.legend(loc='upper left')
        self.ax.set_xlabel('Distance (km)')
        self.ax.set_ylabel('Power (w)')
        self.ax.grid(color='lightgrey', linestyle='-', linewidth=1)
        self.fig.tight_layout()
        
    def plotVDistance(self):
        self.fig3, self.ax3 = plt.subplots(figsize=plotSize)
        segmentsX = []
        segmentsV = []

        for segmentPerformance in self.segmentPerformances:
            segmentsX.append(segmentPerformance.segment.x0/1000)
            segmentsX.append(segmentPerformance.segment.x1/1000)
            segmentsV.append(segmentPerformance.v)
            segmentsV.append(segmentPerformance.v)
        
        self.ax3.plot(segmentsX,segmentsV)
        self.ax3.set_title('Speed vs. Distance')
        #self.ax3.legend(loc='upper left')
        self.ax3.set_xlabel('Distance (km)')
        self.ax3.set_ylabel('V (m/s)')
        self.ax3.grid(color='lightgrey', linestyle='-', linewidth=1)
        self.fig3.tight_layout()


    def plotPowerDuration(self):
        self.fig1, self.ax1 = plt.subplots(figsize=plotSize)
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
            
        self.ax1.plot(segmentsX,segmentsPower,label='total power')
        self.ax1.plot(segmentsX,segmentsFlatPower,label='base power')
        self.ax1.plot(segmentsX,segmentsDragPower,label='drag power')
        self.ax1.plot(segmentsX,segmentsSlopePower,label='slope power')
        
        self.ax1.set_title('Power vs. Time')
        self.ax1.legend(loc='upper left')
        self.ax1.set_xlabel('Duration (s)')
        self.ax1.set_ylabel('Power (w)')
        self.ax1.grid(color='lightgrey', linestyle='-', linewidth=1)
        self.fig1.tight_layout()
        
    def getRaceTime(self):
        #environment,athlete,course,powerDuration,errorLim = 0.0001,powerGuess = athlete.vo2maxPower
        self.errorLim = 0.0001

        powerDuration = self.athlete.powerDuration
        self.powerGuess = self.athlete.vo2maxPower
        self.timeMissing = 1
        self.duration = 0
        while(self.timeMissing):
            
            if self.powerGuess > self.athlete.vo2maxPower or self.powerGuess < 10:
                print('failed')
                return self.duration, self.powerGuess
            self.getDuration(self.powerGuess)
            self.limDuration = powerDuration.getDuration(self.powerGuess)
            #print('limduration ',limDuration)
            self.error = self.duration-self.limDuration
            self.errorFrac = self.error/self.duration
            #print('errorFrac ',errorFrac)
            if (self.errorFrac)>self.errorLim:
                self.powerGuess = self.powerGuess*(1-0.01*self.errorFrac)
            elif (self.errorFrac)<-self.errorLim:
                self.powerGuess = self.powerGuess*(1-0.01*self.errorFrac)
            else:
                return self.duration, self.powerGuess
            
    def getEvenSplitRaceTime(self,considerNormalizedPower = True):
        #environment,athlete,course,powerDuration,errorLim = 0.0001,powerGuess = athlete.vo2maxPower
        self.errorLim = 0.0001

        powerDuration = self.athlete.powerDuration
        self.vGuess = 3
        self.timeMissing = 1
        self.duration = 0
        while(self.timeMissing):
            
            self.energySum = 0
            #if self.power > self.athlete.vo2maxPower or self.power < 10:
            #    print('failed')
            #    return self.duration, self.vGuess
            self.getDurationV(self.vGuess)
            self.normPower = self.getNormalizedPower()
            #print('powerGuess ',powerGuess)
            #print('duration ', duration)
            if considerNormalizedPower:
                self.limDuration = powerDuration.getDuration(self.normPower)
            else:
                self.limDuration = powerDuration.getDuration(self.averagePower)
            #print('limduration ',limDuration)
            self.error = self.duration-self.limDuration
            self.errorFrac = self.error/self.duration
            #print('errorFrac ',errorFrac)
            #print('normPower',self.normPower)
            #print('vguess',self.vGuess)
            if (self.errorFrac)>self.errorLim:
                self.vGuess = self.vGuess*(1-0.01*self.errorFrac)
            elif (self.errorFrac)<-self.errorLim:
                self.vGuess = self.vGuess*(1-0.01*self.errorFrac)
            else:
                return self.duration, self.vGuess, self.averagePower
            
        


class SegmentPerformance:
    def __init__(self,segment, athlete, environment):
        self.segment = segment
        self.duration = 0
        self.distance = segment.length
        #self.duration = self.getDuration(segment.length,self.v)
        self.time0 = 0
        self.time1 = self.duration
        
    def getTimeFromPower(self,athlete,environment,power):
        self.v = getV(environment.airDensity, athlete.Cd, athlete.frontalArea, environment.wind, athlete.Ecor, self.segment.slope, athlete.mass, environment.gravity, power)
        #self.v = getViterate(environment,athlete,self.segment,power)
        self.dragPower = self.getDragPower(environment,athlete,self.v)
        self.slopePower = self.getSlopePower(environment,athlete,self.segment,self.v)
        self.flatPower = self.getFlatPower(environment,athlete,self.v,self.segment.EcorMod)
        self.duration = self.getDuration(self.segment.length,self.v)
        self.flatEnergy = self.flatPower*self.duration
        self.slopeEnergy = self.slopePower*self.duration
        self.dragEnergy = self.dragPower*self.duration
        self.power = power
        self.energy = self.power*self.duration
        self.time1 = self.duration
        
        return self.duration
    
    def getPowerFromV(self,athlete,environment,v):
        self.v = v
        self.dragPower = self.getDragPower(environment,athlete,v)
        self.slopePower = self.getSlopePower(environment,athlete,self.segment,v)
        self.flatPower = self.getFlatPower(environment,athlete,v,self.segment.EcorMod)
        self.duration = self.getDuration(self.segment.length,self.v)
        self.flatEnergy = self.flatPower*self.duration
        self.slopeEnergy = self.slopePower*self.duration
        self.dragEnergy = self.dragPower*self.duration
        self.power = self.dragPower+self.slopePower+self.flatPower
        self.energy = self.power*self.duration
        self.time0 = 0
        self.time1 = self.duration
        
    def getSlopePower(self,environment, athlete, segment, velocity):
        eta = (45.6+1.1622*segment.slope*100)/100
        slopePower = athlete.mass*velocity*environment.gravity*(segment.slope)*eta
        return slopePower	
    	
    def getDragPower(self,environment, athlete, velocity):
        dragPower = 0.5*environment.airDensity*athlete.Cd*athlete.frontalArea*(velocity+environment.wind)**2*velocity
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
	
def plotSlopePower(environment, athlete, velocity):
    slopes = np.arange(-30,35,5)/100
    slopePowers = []
    for slope in slopes:
        eta = (45.6+1.1622*slope*100)/100
        slopePower = athlete.mass*velocity*environment.gravity*(slope)*eta
        slopePowers.append(slopePower)
    fig1, ax1 = plt.subplots(figsize=plotSize)
    ax1.plot(slopes,slopePowers,color='orange')
    ax1.set_title('Slope Power vs. Slope')
    ax1.set_xlabel('Slope (%)')
    ax1.set_ylabel('Power (w)')
    ax1.grid(color='lightgrey', linestyle='-', linewidth=1)
    fig1.tight_layout()

def getDragPower(environment, athlete, velocity):
    dragPower = 0.5*environment.airDensity*athlete.Cd*athlete.frontalArea*(velocity+environment.wind)**2*velocity
    return dragPower

def plotDragPower(environment, athlete, velocity):
    #velocity = 4.05
    dragPowers = []
    winds = np.arange(-10,11,1)
    for wind in winds:
        dragPower = 0.5*environment.density*athlete.Cd*athlete.frontalArea*(velocity+wind)**2*velocity*np.sign(velocity+wind)
        dragPowers.append(dragPower)
    fig1, ax1 = plt.subplots(figsize=plotSize)
    ax1.plot(winds/velocity*100,dragPowers,color='orange')
    ax1.set_title('Drag Power vs. Headwind Speed at 4.05 m/s')
    ax1.set_xlabel('Headwind Speed (% running speed)')
    ax1.set_ylabel('Power (w)')
    ax1.grid(color='lightgrey', linestyle='-', linewidth=1)
    fig1.tight_layout()

def getFlatPower(environment, athlete, velocity, EcorMod):
    flatPower = athlete.mass*athlete.Ecor*environment.gravity/9.81*(1+EcorMod)*velocity
    return flatPower

def readCourse(pathToCourseFile,name):
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
        course = Course(segments,name)
        return course


def getV(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, power):
    Ecor = Ecor*gravity/9.81
    # slope is a decimal value
    # given a power, solve for velocity
    eta = (45.6+1.1622*slope*100)/100
    
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
    
    a = m*g*s*n+c*m
    b = 1/2*d*q
    #v = getVnew2(a, b, p, w)
    return v


def getVnew1(a, b, p, w):
    # a = m*g*s*eta+c*m
    # b = 1/2*rho*Cd*A
    # p = power
    # w = headwind speed
    
    return -(1/(3*(2)**(1/3)*b))*(-18*a*b**2*w+math.sqrt(4*(3*a*b-b**2*w**2)**3+(-18*a*b**2*w-2*b**3*w**3-27*b**2*p)**2)-2*b**3*w**3-27*b**2*p)**(1/3)/(3*2**(1/3)*b)+(2**(1/3)*(3*a*b-b**2*w**2))/(3*b*(-18*a*b**2*w+math.sqrt(4*(3*a*b-b**2*w**2)**3+(-18*a*b**2*w-2*b**3*w**3-27*b**2*p)**2)-2*b**3*w**3-27*b**2*p)**(1/3))-(2*w)/3
    
def getVnew2(a, b, p, w):
    # a = m*g*s*eta+c*m
    # b = 1/2*rho*Cd*A
    # p = power
    # w = headwind speed
    
    return (1/(3*(2)**(1/3)*b))*(-18*a*b**2*w+math.sqrt(4*(-3*a*b-b**2*w**2)**3+(-18*a*b**2*w+2*b**3*w**3-27*b**2*p)**2)+2*b**3*w**3-27*b**2*p)**(1/3)/(3*2**(1/3)*b)-(2**(1/3)*(-3*a*b-b**2*w**2))/(3*b*(-18*a*b**2*w+math.sqrt(4*(-3*a*b-b**2*w**2)**3+(-18*a*b**2*w+2*b**3*w**3-27*b**2*p)**2)+2*b**3*w**3-27*b**2*p)**(1/3))-(2*w)/3

def getViterate(environment, athlete, segment,power):
    Ecor = athlete.Ecor
    airDensity = environment.airDensity
    wind = environment.wind
    mass = athlete.mass
    slope = segment.slope
    gravity = environment.gravity
    frontalArea = athlete.frontalArea
    Cd = athlete.Cd
    Ecor = Ecor*gravity/9.81
    # slope is a decimal value
    # given a power, solve for velocity
    eta = (45.6+1.1622*slope*100)/100
    
    c = Ecor
    d = airDensity
    w = wind
    m = mass
    n = eta
    s = slope
    p = power
    g = gravity
    q = frontalArea*Cd
    
    a = m*g*s*n+c*m # p = v*a -> v = p/a
    #guess v from flat and slope
    v = power/a
    error = 99
    errorlim = 0.0001
    numIter = 0
    while abs(error)>errorlim:
        numIter += 1
        
        p = getP(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, v)
        
        error = (p-power)/power
        #print('Iter: ',numIter,'Vguess: ',v,'p: ',p,'error: ',error)
        if error>errorlim:
            # p too large
            v = v*(1-min(error,1)*0.5)
        elif error<-errorlim:
            # p too small
            v = v*(1+min(abs(error),1)*0.5)
        else:
            #print('v found: ',v,'error: ',error, 'numIterations: ',numIter)
            return v
            
    #calculate p
    #if p too low, increase v
    #if p too high, decrease v
    #if error < tol, return v

def getP(airDensity, Cd, frontalArea, wind, Ecor, slope, mass, gravity, velocity):
    Ecor = Ecor*gravity/9.81
    eta = (45.6+1.1622*slope*100)/100
    return Ecor*mass*velocity+0.5*airDensity*Cd*frontalArea*(velocity+wind)**2*velocity+slope*mass*gravity*velocity*eta


class PowerDuration:
    def __init__(self, glucoseConsumption = 60, startingGlycogen = 3000, vo2maxPower = 347,temp = 5, altitude=0):
        self.tempK = temp+273
        self.tempFrac = abs(self.tempK/(273+5)-1)
        self.metabolicEfficiency = 0.25
        self.glucoseConsumption = glucoseConsumption+0.01
        self.startingGlycogen = startingGlycogen+0.01
        self.vo2maxPower = vo2maxPower
        self.altitudeFactor = (100+-2.63*10**-3*float(altitude)+-9.04*10**-7*float(altitude)**2)/100
        self.vo2maxPower = self.vo2maxPower*self.altitudeFactor
        self.fractionVo2 = np.arange(0,105,5)/100
        self.fractionFTP = self.fractionVo2/1.13
        self.power = self.fractionVo2*self.vo2maxPower
        self.power = self.power/(1+self.tempFrac)# reduce by temperature with simple linear decrease around optimal 5c 
        self.percentFat = np.asarray([100,97.5,95,92.5,90,88.75,87.5,81.25,75,70.5,66,61.5,57,51.5,46,40.5,35,28.75,22.5,16.25,10])/100
        self.percentGlucose = 1-self.percentFat
        self.powerFat = np.multiply(self.percentFat,self.power)
        self.powerGlucose = self.power-self.powerFat
        self.metabolicPowerFat = self.powerFat/self.metabolicEfficiency
        self.metabolicPowerGlucose = self.powerGlucose/self.metabolicEfficiency
        self.powerGlucoseConsumption = 4*4184*self.glucoseConsumption/3600 # convert g/h to watts
        self.maxPowerFatOnly = max(self.powerFat)
        self.equivalentIntensityFatOnly = np.interp(self.maxPowerFatOnly,self.power,self.fractionVo2)
        a = 10e10 # no limit duration value
        self.durationUntilGlycogenDepletion = self.startingGlycogen*4184/(self.metabolicPowerGlucose-self.powerGlucoseConsumption)
        for i in range(len(self.durationUntilGlycogenDepletion)):
            if self.durationUntilGlycogenDepletion[i]<0:
                self.durationUntilGlycogenDepletion[i]=a
            if self.fractionVo2[i]<=self.equivalentIntensityFatOnly:
                self.durationUntilGlycogenDepletion[i] = a
        #print(self.durationUntilGlycogenDepletion)
        self.durationFromEmpirical = np.asarray([a,a,a,a,a,a,a,a,a,a,a,a,a,a,a,a,16200,6600,3000,1200,600])
        #print(self.durationFromEmpirical)
        self.durationEnergyLimited = np.minimum(self.durationFromEmpirical, self.durationUntilGlycogenDepletion)
        #print(self.durationEnergyLimited)
        self.durationSleepLimited = np.asarray([a,a,a,a,a,a,a,a,a,1440,336,120,44.03988009,21.97936125,14.18897655,10.24099629,4.5,1.833333333,0.8333333333,0.3333333333,0.1666666667])*3600
        #print(self.durationSleepLimited)
        self.duration = np.minimum(self.durationEnergyLimited,self.durationSleepLimited)
        #print(self.duration)
    def getDuration(self,power):
        return np.interp(power,self.power,self.duration)
    def getPower(self,duration):
        return np.interp(duration,self.duration,self.power)
    def plotPowerDuration(self,maxDuration = 24,temp=5):
        self.fig1, self.ax1 = plt.subplots(figsize=plotSize)
        self.ax1.plot(self.duration/3600,self.power,color='orange')
        self.ax1.set_title('Power vs Duration')
        self.ax1.set_xlabel('Duration (h)')
        self.ax1.set_ylabel('Power (w)')
        self.ax1.set_xlim(xmin=0,xmax=maxDuration)
        self.ax1.set_ylim(ymin=self.vo2maxPower*0.4,ymax=self.vo2maxPower*1.1)
        self.ax1.grid(color='lightgrey', linestyle='-', linewidth=1)
        self.fig1.tight_layout()
    
    def plotDurationPower(self,maxDuration = 24):
        self.fig2, self.ax2 = plt.subplots(figsize=plotSize)
        self.ax2.plot(self.power,self.duration/3600,color='orange')
        self.ax2.set_title('Duration vs Power')
        self.ax2.set_ylabel('Duration (h)')
        self.ax2.set_xlabel('Power (w)')
        self.ax2.set_xlim(xmin=self.vo2maxPower*0.4,xmax=self.vo2maxPower*1.1)
        self.ax2.set_ylim(ymin=0,ymax=maxDuration)
        self.ax2.grid(color='lightgrey', linestyle='-', linewidth=1)
        self.fig2.tight_layout()
        

def getTime(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return h, m, s