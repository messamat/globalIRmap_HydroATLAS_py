import arcpy
import os
import sys
import arcgisscripting
import time
import datetime
import math
from arcpy import da
from arcpy.sa import *

# Use all of the cores on the machine
arcpy.env.parallelProcessingFactor = "100%"

def set_environment(workspace, mask_layer):
    arcpy.CheckOutExtension("spatial")
    arcpy.env.cellSize = mask_layer
    arcpy.env.extent = mask_layer
    arcpy.env.workspace = workspace
    arcpy.overwriteOutputs = True
    arcpy.env.overwriteOutput = True

def createWorkspace(scratchws, ts):
    try:
        valueGDB = "zonal" + "_" + str(ts) + ".gdb"
        fullpath = scratchws + "\\" + valueGDB

        arcpy.CreateFileGDB_management(scratchws, valueGDB)
        return fullpath

    except Exception, e:
        # If an error occurred, print line number and error message
        import traceback, sys

        tb = sys.exc_info()[2]
        print("Line %i" % tb.tb_lineno, 2)
        print(str(e.message), 2)

def FieldExist(featureclass, fieldname):
    fieldList = arcpy.ListFields(featureclass, fieldname)

    fieldCount = len(fieldList)

    if (fieldCount == 1):
        return True
    else:
        return False

def calculate_zonal_stats(zoneLayer, value_raster, name, timestamp, stat="SUM"):

    try:
        print "Calculate zonal stats"
        ZonalStatisticsAsTable(zoneLayer, "Value", value_raster, name, "DATA", stat)

    except arcpy.ExecuteError:
        print arcpy.GetMessages(2)
    except Exception as e:
        print e.args[0]

start = time.clock()
ts = int(datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S'))
arcpy.AddMessage(str(ts))

#SHAPEFILE LOCATION

shapefiles_location = arcpy.GetParameterAsText(1)

#WORKSPACE FOLDER

workspaceFolder = arcpy.GetParameterAsText(2)
workspace = createWorkspace(workspaceFolder, ts)

#IMPORT THE ATTRIBUTE FILE
import csv
import sys

from collections import defaultdict

pathAL = arcpy.GetParameterAsText(0)

#Create Output GEODATABASE called output.gdb in the foder if it exists

output_folder = arcpy.GetParameterAsText(4)

if not arcpy.Exists(r"" + output_folder + "\output.gdb"):
    arcpy.CreateFileGDB_management(r""+output_folder, "output.gdb")


f = open(pathAL, 'rb') #EDIT HERE
reader = csv.reader(f)
myList = list(reader)

#SET MASK AS FIRST VALUE GRID OR THE PARAMETER
if len(arcpy.GetParameterAsText(3))>0:
    arcpy.AddMessage("Mask grid will be used to set environment")
    mask_layer = arcpy.GetParameterAsText(3) #EDIT HERE
else:
    arcpy.AddMessage("First value grid will be used as mask grid to set environment")
    mask_layer = myList[1][3] #set the mask as the first value grid

set_environment(workspace, mask_layer)

for x in range(1,len(myList)):

    if myList[x][11] == 'Y': #If the run layer switch is set as Yes (Y) then proceed

        def getValues():
            # Fills the dictionaries with values
            try:
                flds = [FromJoinField, FromValueField] #VALUE #STATISTIC_FIELD
                with arcpy.da.SearchCursor(FromJoinFC, flds) as cursor:
                    for myrow in cursor:
                        from_valueDict[myrow[0]] = myrow[1]
                return

            except Exception, e:
                # If an error occurred, print line number and error message
                import traceback, sys
                tb = sys.exc_info()[2]
                print "Line %i" % tb.tb_lineno
                arcpy.AddMessage(str(e.message))

        def getValuesMax():
            # Fills the dictionaries with values
            try:
                flds = [FromJoinField, 'MAX'] #VALUE #STATISTIC_FIELD
                with arcpy.da.SearchCursor(FromJoinFC, flds) as cursor:
                    for myrow in cursor:
                        from_valueDict[myrow[0]] = myrow[1]
                return

            except Exception, e:
                # If an error occurred, print line number and error message
                import traceback, sys
                tb = sys.exc_info()[2]
                print "Line %i" % tb.tb_lineno
                print e.message

        def getValuesMin():
            # Fills the dictionaries with values
            try:
                flds = [FromJoinField, 'MIN'] #VALUE #STATISTIC_FIELD
                with arcpy.da.SearchCursor(FromJoinFC, flds) as cursor:
                    for myrow in cursor:
                        from_valueDict[myrow[0]] = myrow[1]
                return

            except Exception, e:
                # If an error occurred, print line number and error message
                import traceback, sys
                tb = sys.exc_info()[2]
                print "Line %i" % tb.tb_lineno
                print e.message

        def copyRaw(level,outputName):

            arcpy.AddMessage("Copying " + r"" + shapefiles_location +"\link_hybas_lev" + "%02d"%int(level) + "_v1c")

            try:
                #Copies the raw copy of the shapefile to the output folder
                #Grab the copy based on level
                arcpy.CopyFeatures_management(r"" + shapefiles_location +"\link_hybas_lev" + "%02d"%int(level) + "_v1c", r"" + output_folder + "\output.gdb" + "\\" + str(outputName))

            except Exception, e:
                # If an error occurred, print line number and error message
                import traceback, sys
                tb = sys.exc_info()[2]
                print "Line %i" % tb.tb_lineno
                print e.message

        try:

            start_time = time.time()

            arcpy.AddMessage("System version: {}".format(sys.version))
            if sys.maxsize > 2**32:
               arcpy.AddMessage("Running python 64 bit")
            else:
               arcpy.AddMessage("Running python 32 bit")

            #IF THE OUTPUT FOLDER EXISTS THEN MAKE IT

            ToJoinFC = r"" + output_folder + "\output.gdb" + "\\" + str(myList[x][10])

            if not arcpy.Exists(ToJoinFC):
                arcpy.AddMessage("The feature class " + ToJoinFC + " does not exist.")
                arcpy.AddMessage("Creating feature class...")
                copyRaw(myList[x][2],myList[x][10])

            if (FieldExist(ToJoinFC, myList[x][4])): #INTO FC, INTO FIELD
                arcpy.AddMessage("Field " +  str(myList[x][4]) + " already exists in " + str(myList[x][10]))
                arcpy.AddMessage("")
                continue

            if (not FieldExist(ToJoinFC, myList[x][9])): #INTO FC, INTO FIELD
                arcpy.AddMessage("Link field " +  str(myList[x][9]) + " does not exist in " + str(ToJoinFC))
                arcpy.AddMessage("")
                continue

            #calculate_zonal_stats(zoneLayer, value_raster, name, timestamp, stat="SUM")
            arcpy.AddMessage("Starting | " + str(myList[x][0]) + " - " + str(myList[x][6]))
            calculate_zonal_stats(myList[x][1], myList[x][3], myList[x][4], ts, myList[x][6])



            ToJoinField = str(myList[x][9])#"GOID"  #LINK_BAS/SET JOIN FIELD
            IntoJoinField = myList[x][4]#+ "_" + myList[x][6] #NEW FIELD NAME = COLUMN_NAME+STAT
            ToJoinFieldType = myList[x][5] #TYPE OF NEW FIELD
            FromValueField = myList[x][6]

            Multiplier = myList[x][7]

            FromJoinField = "VALUE"
            FromJoinTableName = myList[x][4]
            FromJoinFC = workspace + "\\" + FromJoinTableName #TABLE FROM WHICH JOIN WILL BE MADE AU_TMEAN7

            #from_valueDict = defaultdict(float) # adjust accordingly
            from_valueDict = defaultdict(lambda: -9999) #sets all empty values as -999

            arcpy.AddField_management(ToJoinFC, IntoJoinField, ToJoinFieldType,"#",3)

            flds = [ToJoinField, IntoJoinField]

            if FromValueField == 'MAXIMUM':
                numS = getValuesMax()
            elif FromValueField == 'MINIMUM':
                numS = getValuesMin()
            else:
                numS = getValues()

            newValue = 0

            i = 1

            if Multiplier == '1':

                with arcpy.da.UpdateCursor(ToJoinFC, flds) as cursor:
                    for row1 in cursor:
                        ToJoinFieldValue = row1[0]
                        newValue = from_valueDict[ToJoinFieldValue]
                        if newValue == -9999:
                            row1[1] = -9999
                        else:
                            row1[1] = round(newValue, 3)
                        cursor.updateRow(row1)
                        i += 1

            else:

                with arcpy.da.UpdateCursor(ToJoinFC, flds) as cursor:
                    for row1 in cursor:
                        ToJoinFieldValue = row1[0]
                        newValue = from_valueDict[ToJoinFieldValue]
                        if newValue == -9999:
                            row1[1] = -9999
                        else:
                            row1[1] = round(newValue * float(Multiplier), 3)
                        cursor.updateRow(row1)
                        i += 1

            if arcpy.GetParameterAsText(5) == 'true':
                arcpy.AddMessage("creating shapefile")
                if not arcpy.Exists(output_folder + "\\" + str(myList[x][10]) + ".shp"):
                    arcpy.AddMessage(str(myList[x][10]) + ".shp does not exist in " + output_folder)
                    arcpy.CopyFeatures_management(ToJoinFC, output_folder + "\\" + str(myList[x][10]) + ".shp")
                else:
                    arcpy.AddMessage(str(myList[x][10]) + ".shp already exists in " + output_folder)

                if FieldExist(r"" + output_folder + "\\" + str(myList[x][10]) + ".shp", IntoJoinField): #INTO FC, INTO FIELD
                    continue

                else:
                    #Add field
                    arcpy.AddField_management(r"" + output_folder + "\\" + str(myList[x][10]) + ".shp", IntoJoinField, ToJoinFieldType)

                    ToJoinSHP = r"" + output_folder + "\\" + str(myList[x][10]) + ".shp"

                    newValue = 0

                    i = 1

                    with arcpy.da.UpdateCursor(ToJoinSHP, flds) as cursor:
                        for row1 in cursor:
                            ToJoinFieldValue = row1[0]
                            newValue = from_valueDict[ToJoinFieldValue]
                            if newValue == -9999:
                                row1[1] = -9999
                            else:
                                row1[1] = round(newValue * float(Multiplier), 3)
                            cursor.updateRow(row1)
                            i += 1

        except Exception, e:
            # If an error occurred, print line number and error message
            import traceback, sys
            tb = sys.exc_info()[2]
            arcpy.AddMessage("Line %i" % tb.tb_lineno)
            arcpy.AddMessage(str(e.message))

print "Completed in %d minutes" % ((time.clock() - start)/60)
