import datetime
import arcpy
import os
import sys
from arcpy import env
from arcpy.sa import *
import time
import csv

# Use all of the cores on the machine.
arcpy.env.parallelProcessingFactor = "100%"

start = time.clock()
ts = int(datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S'))
arcpy.AddMessage(str(ts))


def set_environment(workspace, mask_layer):
    arcpy.CheckOutExtension("spatial")
    arcpy.env.cellSize = mask_layer
    arcpy.env.extent = mask_layer
    arcpy.env.workspace = workspace
    arcpy.overwriteOutputs = True
    arcpy.env.overwriteOutput = True

def createWorkspace(scratchws, ts):
    try:
        valueGDB = "upland" + "_" + str(ts) + ".gdb"
        fullpath = scratchws + "\\" + valueGDB

        arcpy.CreateFileGDB_management(scratchws, valueGDB)
        return fullpath

    except Exception, e:
        # If an error occurred, print line number and error message
        import traceback, sys

        tb = sys.exc_info()[2]
        print("Line %i" % tb.tb_lineno, 2)
        print(str(e.message), 2)

#SET PARAMETERS

#VALUE GRID
value_grid = arcpy.GetParameterAsText(0)

#FLOW DIRECTION GRID FOLDER

grid_loc = arcpy.GetParameterAsText(1)

#SELECT CONTINENT

cont = arcpy.GetParameterAsText(2)

continent = []

for fc in cont.split(';'):
    continent.append(str(fc)[-3:][:2])

# List continent
arcpy.AddMessage(continent)

#WORKSPACE FOLDER

workspaceFolder = arcpy.GetParameterAsText(3)
workspace = createWorkspace(workspaceFolder, ts)

#OUTPUT PREFIX
prefix = arcpy.GetParameterAsText(4)

#OUTPUT FOLDER
output_folder = arcpy.GetParameterAsText(5)

if not arcpy.Exists(r"" + output_folder + "\output.gdb"):
    arcpy.CreateFileGDB_management(r""+output_folder, "output.gdb")

try:

    for i in range(0,len(continent)):

        direction = r"" + grid_loc + '\\' + continent[i] + "_dir_15s"

        set_environment(workspace, direction)

        # Flow accumulation of value grid

        outFlowAccumulation = FlowAccumulation(direction,r""+ value_grid, "FLOAT")
        outFlowAccumulation.save(r""+continent[i] + "_flowacc")

        # Sum the flow accumulation result and the value grid
        outFlowAccumulation_2 = Plus(r""+continent[i] + "_flowacc",r""+ value_grid)
        outFlowAccumulation_2.save(r""+output_folder + "\output.gdb" + "\\" + prefix + "_" + continent[i])

except Exception, e:

    # If an error occurred, print line number and error message
    import traceback, sys
    tb = sys.exc_info()[2]
    arcpy.AddMessage("Line %i" % tb.tb_lineno)
    arcpy.AddMessage(str(e.message))

for fc in arcpy.ListRasters():
    arcpy.Delete_management(fc)
