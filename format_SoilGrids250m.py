from utility_functions import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

sg_outdir = os.path.join(datdir, 'SOILGRIDS250')
sgsmalldir = os.path.join(resdir,'soilsgrid250_smalltiles')
sgmediumdir = os.path.join(resdir,'soilsgrid250_mediumtiles')
sgresgdb = os.path.join(resdir, 'soilgrids250.gdb')
pathcheckcreate(sgsmalldir)
pathcheckcreate(sgmediumdir)
pathcheckcreate(sgresgdb)

#Get Goode Homolosine spatial reference
goode_sr = arcpy.SpatialReference(54052)

########################################## MOSAIC TILES ################################################################
#Create a list of files for each texture and depth
checkproj = False
sg_subdirl = defaultdict(list)
for f in getfilelist(sg_outdir, 'tileSG.*tif$'):
    print(f)
    sg_subdirl[os.path.split(f)[0]].append(f)
    if checkproj:
        if arcpy.Describe(f).SpatialReference.name=='Unknown':
            arcpy.DefineProjection_management(f, goode_sr)

tileinterval  = 100
smalldirdict = {os.path.split(partdepth)[1]: os.path.join(sgsmalldir, os.path.split(partdepth)[1]) for partdepth in sg_subdirl}

for partdepth in sg_subdirl:
    print(partdepth)
    partdepthdir = smalldirdict[os.path.split(partdepth)[1]]
    if not os.path.exists(partdepthdir):
        print('Create directory {}...'.format(partdepthdir))
        os.mkdir(partdepthdir)
    dictdiv= [[i, i+tileinterval] for i in range(0, len(sg_subdirl[partdepth]), tileinterval)]
    for tilel in dictdiv:
        outtile= os.path.join(partdepthdir, "mean{1}_{2}.tif".format(os.path.split(partdepth)[1], tilel[0], tilel[1]-1))
        if not arcpy.Exists(outtile):
            print('Mosaicking {}...'.format(outtile))
            arcpy.MosaicToNewRaster_management(input_rasters= sg_subdirl[partdepth][tilel[0]:tilel[1]],
                                               output_location= os.path.split(outtile)[0],
                                               raster_dataset_name_with_extension= os.path.split(outtile)[1],
                                               number_of_bands= 1)
        else:
            print('{} already exists...'.format(outtile))

#Remosaick using MAX
mediumdirdict = {i: os.path.join(sgmediumdir, i) for i in smalldirdict}

for partdepth in smalldirdict:
    print(partdepth)
    partdepthdir = mediumdirdict[partdepth]
    if not os.path.exists(partdepthdir):
        print('Create directory {}...'.format(partdepthdir))
        os.mkdir(partdepthdir)
    smalltiles = getfilelist(smalldirdict[partdepth], '.*[.]tif$')
    dictdiv= [[i, i+tileinterval] for i in range(0, len(smalltiles), tileinterval)]
    for tilel in dictdiv:
        outtile= os.path.join(partdepthdir, "mean{1}_{2}.tif".format(os.path.split(partdepth)[1],
                                                                     tilel[0]*tileinterval,
                                                                     tilel[1]*tileinterval-1))
        if not arcpy.Exists(outtile):
            print('Mosaicking {}...'.format(outtile))
            arcpy.MosaicToNewRaster_management(input_rasters= smalltiles[tilel[0]:tilel[1]],
                                               output_location= os.path.split(outtile)[0],
                                               raster_dataset_name_with_extension= os.path.split(outtile)[1],
                                               number_of_bands= 1,
                                               mosaic_method='MAXIMUM')
        else:
            print('{} already exists...'.format(outtile))




#Last remosaicking
mosaicdict = {lyr:os.path.join(sgresgdb, lyr) for lyr in mediumdirdict}
for dir in mediumdirdict:
    tilel = getfilelist(mediumdirdict[dir], '.*[.]tif$')
    outmosaic =mosaicdict[dir]
    if tilel is not None and not arcpy.Exists(outmosaic):
        print('Processing {}...'.format(outmosaic))
        arcpy.MosaicToNewRaster_management(input_rasters=tilel,
                                           output_location=os.path.split(outmosaic)[0],
                                           raster_dataset_name_with_extension=os.path.split(outmosaic)[1],
                                           number_of_bands=1,
                                           mosaic_method='MAXIMUM')

########################################## MATCH HYDROSHEDS LAND MASK ##################################################
#Check ratio of resolutions
#Re-project
#Snap
#Aggregate and/or resample
#Run accumulation


#Because there is no way to know what is inland vs. sea water, perhaps just re-project to wgs84, resample, and snap.
#Compute everything while ignoring NoData values
#Fill in NoData values with -9999 and use these in model rather than excluding these values.

