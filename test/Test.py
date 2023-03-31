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

print(bonk.getDragPower(environment, athlete, velocity))
print(bonk.getFlatPower(environment, athlete, velocity))
print(bonk.getSlopePower(environment, athlete, segment, velocity))