from enum import Enum
Atmosphere = Enum('Atmosphere',['Earth','Mars','Moon'])

class Athlete:
    def __init__(self, mass = 70, Ecor = 0.98, fatigueResistanceCoef = 0.07, CdForward = 0.5, CdRear = 0.5, frontalArea = 0.5):
        self.mass = mass
        self.fatigueResistanceCoef = fatigueResistanceCoef
        self.CdForward = CdForward
        self.CdRear = CdRear
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
    def __init__(self,temperature = 10, humidity = 20, wind = 2, gravity = 9.81, altitude = 0, atmosphere = Atmosphere.Earth):
        self.temperature = temperature
        self.humidity = humidity
        self.wind = wind
        self.gravity = gravity
        self.altitude = altitude
        self.atmosphere = atmosphere
        if atmosphere == Atmosphere.Earth:
            self.density = 1.15
            
        
class Segment:
    def __init__(self,length = 1609, slope = 5, surfaceDampingMod = 0):
        self.length = length
        self.slope = slope
        self.surfaceDampingMod = surfaceDampingMod
	

def getSlopePower(environment, athlete, segment, velocity):
    slopePower = athlete.mass*velocity*environment.gravity*(segment.slope/100)*(45.6-1.1622*segment.slope)/100
    return slopePower	
	
def getDragPower(environment, athlete, velocity):
    if velocity+environment.wind <=0:
        dragPower = 0.5*environment.density*athlete.CdForward*athlete.frontalArea*(velocity+environment.wind)**2*velocity
    else:
        dragPower = 0.5*environment.density*athlete.CdRear*athlete.frontalArea*(velocity+environment.wind)**2*velocity
    return dragPower

def getFlatPower(environment, athlete, velocity):
    flatPower = athlete.mass*athlete.Ecor*velocity
    return flatPower
