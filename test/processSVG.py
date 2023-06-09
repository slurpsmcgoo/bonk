# -*- coding: utf-8 -*-
"""
Created on Sat Apr  1 11:16:52 2023

@author: jackm_000
"""
path = 'ouray.csv'

#run woodstock 761 pixels per 16 miles
# 187 pixels per 80 ft

def processSVG(pathToCourseFile):
    # read in segments line by line and create course object
    with open(pathToCourseFile, newline='') as csvfile:
    #elements of description:
        #number length slope EcorMod surfaceTechMod
        lines = csvfile.readlines()
        newlines = []
        for line in lines:
            line = line.split(',')
            newline = []
            for elem in line:
                elem = elem.split(' ')
                
                newline.append(elem[0].replace('\n',''))
            line = newline[0:2]
            newlines.append(line)
            
    #yFtPerPixel = 2.81 #boston
    #yFtPerPixel = 80/187.0 #woodstock
    #yMperPixel = yFtPerPixel/3.2808
    yMperPixel = 9.807
    #xMilePerPixel = 1/105.3#boston
    #xMilePerPixel = 16/761#woodstock
    xMperPixel = 123.68#xMilePerPixel*1609
    x = []
    y = []
    xOffset = float(newlines[0][0])
    yOffset = float(newlines[0][1])
    for line in newlines:
        if len(line)>1:
            pixelX = float(line[0])
            pixelY = float(line[1])
            posX = (pixelX-xOffset)*xMperPixel
            posY = (-pixelY+yOffset)*yMperPixel
            print(posX, ' ',posY)
            x.append(posX)
            y.append(posY)
    file1 = open('ourayTemp.csv', 'w')
    for line in newlines:
        file1.write("%s\n" % line)
    file1.close()
    
    file = open('ourayCourse.csv','w')
    file.write('number length slope EcorMod surfaceTechMod\n')
    for j in range(1):
        print(j)
        for i in range(len(x)-1):
            if x[i+1]-x[i] > 0:
                line = str(i)+' '+str(x[i+1]-x[i])+' '+str(y[i+1]-y[i])+' '+'0 0\n'
                file.write(line)
    file.close()
        
        
processSVG(path)

