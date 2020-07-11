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

def rebase_path(in_path, in_rootdir, arcpycheck=False):
    rp1 = os.path.realpath(in_path)
    rp2 = os.path.realpath(in_rootdir)
    rp1_nod = os.path.splitdrive(rp1)[1]
    rp2_nod = os.path.splitdrive(rp2)[1]

    x = 1
    commonlist = list()
    while x > 0:
        prefx = os.path.commonprefix([rp1_nod, rp2_nod])
        if len(prefx) > 0:
            if prefx != '\\':
                commonlist.append(prefx)
        else:
            prefx = rp2_nod.split('\\')[0]
        rp2_nod = rp2_nod.split(prefx, 1)[1]
        x = len(rp2_nod)

    selprefx = re.sub('^[\\\\]', '', max(commonlist, key=len))

    out_path = os.path.join('{}\\'.format(os.path.splitdrive(rp2)[0]),
                            re.sub('[\\\\]$', '', os.path.splitdrive(rp2)[1].split(selprefx)[0]),
                            selprefx,
                            re.sub('^[\\\\]', '', rp1.split(selprefx)[1]))

    if arcpycheck:
        arcpcheckres = arcpy.Exists(out_path)
        if arcpcheckres:
            print('Rebased {0} \n to {1}...'.format(in_path, out_path))
            return (out_path)
        else:
            print('Rebased path {0} to \n {1} \n '
                  'but the dir/file does not exist, returning original path...'.format(in_path, out_path))
    else:
        print('Rebased {0} \n to {1}...'.format(in_path, out_path))
        return(out_path)

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

if __name__ == '__main__':
    from utility_functions import *

    rootdir = "D:/PhD/HydroATLAS/data/Bernhard/HydroATLAS"
    shapefiles_location = os.path.join(rootdir, 'HydroATLAS_Geometry', 'Link_shapefiles', 'link_hyriv_v1c.gdb')
    workspaceFolder = os.path.join(rootdir, 'tempworkspace')
    pathcheckcreate(workspaceFolder)
    pathAL = os.path.join("D:/PhD/HydroATLAS/src", "RiverATLAS_ParameterFile_v11_20200708.csv")
    output_folder = os.path.join(rootdir, 'Output')
    pathcheckcreate(output_folder)

    start = time.clock()
    ts = int(datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S'))
    arcpy.AddMessage(str(ts))

    #SHAPEFILE LOCATION

    #shapefiles_location = arcpy.GetParameterAsText(1)

    #TEMPORARY WORKSPACE FOLDER

    #workspaceFolder = arcpy.GetParameterAsText(2)
    workspace = createWorkspace(workspaceFolder, ts)

    #IMPORT THE ATTRIBUTE FILE (which contains all function parameters, names, units, etc.)
    import csv
    import sys

    from collections import defaultdict

    #pathAL = arcpy.GetParameterAsText(0)

    #Create Output GEODATABASE called output.gdb in the folder if it exists

    #output_folder = arcpy.GetParameterAsText(4)

    if not arcpy.Exists(r"" + output_folder + "\output.gdb"):
        arcpy.CreateFileGDB_management(r""+output_folder, "output.gdb")


    f = open(pathAL, 'rb') #EDIT HERE
    reader = csv.reader(f)
    myList = list(reader)

    #SET MASK AS FIRST VALUE GRID OR THE PARAMETER
    # if len(arcpy.GetParameterAsText(3))>0:
    #     arcpy.AddMessage("Mask grid will be used to set environment")
    #     mask_layer = arcpy.GetParameterAsText(3) #EDIT HERE
    # else:
    #     arcpy.AddMessage("First value grid will be used as mask grid to set environment")
    #     mask_layer = myList[1][3] #set the mask as the first value grid
    #     if not arcpy.Exists(mask_layer):
    #         mask_layer = rebase_path(in_path=mask_layer, in_rootdir=rootdir, arcpycheck=True)
    mask_layer = os.path.join("D:/PhD/HydroATLAS/data/Bernhard/HydroATLAS", "HydroATLAS_Geometry",
                              'Masks', 'hydrosheds_landmask_15s.gdb', 'hys_land_15s')

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

                arcpy.AddMessage("Copying " + r"" + shapefiles_location +"\link_hyriv_v1c") #lev" + "%02d"%int(level)

                try:
                    #Copies the raw copy of the shapefile to the output folder
                    #Grab the copy based on level
                    inlevel_format = r"" + shapefiles_location + "\link_hyriv_v1c"

                    if not arcpy.Exists(inlevel_format):
                        print('{} does not exists... try rebasing'.format(inlevel_format))
                        rebase_path(in_path=inlevel_format, in_rootdir=rootdir, arcpycheck=True)

                    arcpy.CopyFeatures_management(r"" + shapefiles_location +"\link_hyriv_v1c",
                                                  r"" + output_folder + "\output.gdb" + "\\" + str(outputName))

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

                ToJoinFC = r"" + output_folder + "\output.gdb" + "\\" + str(myList[x][10]) #Output_Filename in parameter file (e.g. RiverATLAS_v10)

                if not arcpy.Exists(rebase_path(ToJoinFC, rootdir)):
                    arcpy.AddMessage("The feature class " + ToJoinFC + " does not exist.")
                    arcpy.AddMessage("Creating feature class...")
                    copyRaw(level=myList[x][2],outputName=myList[x][10])

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
                if not arcpy.Exists(myList[x][4]):
                    calculate_zonal_stats(rebase_path(myList[x][1], rootdir, arcpycheck=True),
                                          rebase_path(myList[x][3], rootdir, arcpycheck=True),
                                          myList[x][4], ts, myList[x][6])
                else:
                    print('{} table already exists...'.format(myList[x][4]))

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
