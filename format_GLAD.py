import os
import arcpy
from arcpy.sa import *
import sys
import re
import math
from utility_functions import *
import numpy as np
import cProfile

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True
arcpy.env.parallelProcessingFactor = "100%"

# Set up dir structure
rootdir = os.path.dirname(os.path.abspath(__file__)).split('\\src')[0]
datdir = os.path.join(rootdir, 'data')
resdir = os.path.join(rootdir, 'results')
scratchdir = os.path.join(rootdir, 'scratch')
scratchgdb = os.path.join(scratchdir, 'scratch.gdb')
pathcheckcreate(scratchgdb)
arcpy.env.scratchWorkspace = scratchgdb

hydrotemplate = os.path.join(resdir, 'HydroSHEDS', 'mask.gdb', 'af_mask_15s')  # Grab HydroSHEDS layer for one continent as template

glad_dir = os.path.join(datdir, 'GLAD')
alos_dir = os.path.join(datdir, 'ALOS')
mod44w_outdir = os.path.join(datdir, 'mod44w')
mod44w_resgdb = os.path.join(resdir, 'mod44w.gdb')
alosresgdb = os.path.join(resdir, 'alos.gdb')
gladresgdb = os.path.join(resdir, 'glad.gdb')
pathcheckcreate(gladresgdb)
pathcheckcreate(alosresgdb)

#GLAD values mean the following
#0: NoData
#1: Land
#2: Permanent water:
#3: Stable seasonal
#4: Water gain
#5: Water loss
#6: Dry period
#7: Wet period
#8: High frequency
#10: Probable land
#11: Probable water
#12: Sparse data - exclude

#---------------------------- Remove GLAD tiles with only 0 values -----------------------------------------------------
rawtilelist = getfilelist(glad_dir, 'class99_19.*[.]tif$')

for tile in rawtilelist:
    print(tile)
    # Get unique categorical values
    if not Raster(tile).hasRAT and arcpy.Describe(tile).bandCount == 1:  # Build attribute table if doesn't exist
        try:
            arcpy.BuildRasterAttributeTable_management(tile)  # Does not work
        except Exception:
            e = sys.exc_info()[1]
            print(e.args[0])
            arcpy.DeleteRasterAttributeTable_management(tile)

    gladvals = {row[0] for row in arcpy.da.SearchCursor(tile, 'Value')}

    if len(gladvals) == 1:  # If only one value across entire tile
        if list(gladvals)[0] == 0:  # And that value is NoData
            print('Tile only has NoData values, deleting...')
            arcpy.Delete_management(tile)  # Delete tile

#---------------------------- pre-process MODIS -------------------------------------------------------------------------
#Get list of MODIS tiles
mod44w_tilelist = getfilelist(mod44w_outdir, '.*[.]hdf$')

#Get wgs84 extent of all mod44w tiles (because MODIS is in custom Spheroid Sinusoidal projection)
mod44w_wgsextdict= {}
for i in mod44w_tilelist:
    print(i)
    modtileid = re.search('(?<=MOD44W[.]A2015001[.])h[0-9]{2}v[0-9]{2}(?=[0-9.]{18}[.]hdf)',
                          os.path.split(i)[1]).group()

    extpoly = arcpy.Project_management(in_dataset=arcpy.Describe(i).extent.polygon,
                                       out_dataset=os.path.join(mod44w_resgdb, 'extpoly{}'.format(modtileid)),
                                       out_coor_system=rawtilelist[0])
    mod44w_wgsextdict[i] = arcpy.Describe(extpoly).extent

#---------------------------- Identify sea vs freshwater pixels -----------------------------------------------------
alos_tilelist = getfilelist(alos_dir, 'ALPSMLC30_[NS][0-9]{3}[WE][0-9]{3}_DSM.tif$')
gladtile = os.path.join(gladresgdb, 'glad_seatest')
gladtileid = 'seatest' #re.sub('(^.*class99_18_)|([.]tif)', '', gladtile)

gladtile_extent = arcpy.Describe(gladtile).extent
# Subset tiles to only keep those that intersect the GLAD tile
alos_seltiles = [i for i in alos_tilelist
                 if arcpy.Describe(i).extent.overlaps(gladtile_extent) or
                 arcpy.Describe(i).extent.touches(gladtile_extent) or
                 arcpy.Describe(i).extent.within(gladtile_extent)]

#Format ALOS
alos_mosaictile = os.path.join(alosresgdb, 'alos_mosaic')
arcpy.MosaicToNewRaster_management(input_rasters=alos_seltiles,
                                   output_location= os.path.split(alos_mosaictile)[0], #'in_memory
                                   raster_dataset_name_with_extension=os.path.split(alos_mosaictile)[1],
                                   pixel_type='16_BIT_SIGNED',
                                   number_of_bands=1)

arcpy.env.extent = gladtile
arcpy.env.snapRaster = gladtile
alos_rsp = os.path.join(alosresgdb, 'alos_rsp')
arcpy.Resample_management(in_raster=alos_mosaictile,
                          out_raster=alos_rsp,
                          cell_size=arcpy.Describe(gladtile).meanCellWidth,
                          resampling_type='NEAREST')

#---------------------------- Format MODIS -----------------------------------------------------------------------------
#First whether an already-processed MODIS tile contains the entire area
mod44w_seltiles = get_inters_tiles(ref_extent=gladtile_extent, tileiterator=mod44w_wgsextdict)

#Extracr QA dataset
mod44w_seltilesQA = []
for tile in mod44w_seltiles:
    outQA = os.path.join(mod44w_resgdb, "QA_{}".format(re.sub('[.]', '_', os.path.splitext(os.path.split(tile)[1])[0])))
    if not arcpy.Exists(outQA):
        print(outQA)
        arcpy.ExtractSubDataset_management(in_raster=tile, out_raster=outQA, subdataset_index=1)
    mod44w_seltilesQA.append(outQA)

#If multiple MODIS tiles intersect GLAD tile, mosaick them
if len(mod44w_seltilesQA) > 1:
    mod44w_gladmatch = os.path.join(mod44w_resgdb, 'mod44wQA_gladmosaic{}'.format(gladtileid))
    if not arcpy.Exists(mod44w_gladmatch):
        arcpy.MosaicToNewRaster_management(mod44w_seltilesQA,
                                           os.path.split(mod44w_gladmatch)[0],
                                           raster_dataset_name_with_extension=os.path.split(mod44w_gladmatch)[1],
                                           number_of_bands=1)

#Check whether there are any seawater pixels in MODIS
if not Raster(mod44w_gladmatch).hasRAT and arcpy.Describe(tile).bandCount == 1:  # Build attribute table if doesn't exist
    try:
        arcpy.BuildRasterAttributeTable_management(tile)  # Does not work
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
        arcpy.DeleteRasterAttributeTable_management(tile)

gladvals = {row[0] for row in arcpy.da.SearchCursor(tile, 'Value')}

#Run a 3x3 majority filter on MODIS to get rid of isolated sea pixels
modmaj = os.path.join(mod44w_resgdb, 'modmaj_{}'.format(gladtileid))
FocalStatistics (in_raster=mod44w_gladmatch,
                 neighborhood=NbrRectangle(4, 4, "CELL"),
                 statistics_type='MAJORITY').save(modmaj)

#Project, adjust cell size, and snap MODIS to GLAD tile
tic = time.time()
arcpy.env.snapRaster = gladtile
arcpy.env.extent = gladtile
mod44w_gladmatch_wgs = os.path.join(mod44w_resgdb, 'mod44wQA_gladwgs{}'.format(gladtileid))
if not arcpy.Exists(mod44w_gladmatch_wgs):
    arcpy.ProjectRaster_management(modmaj,
                                   out_raster=mod44w_gladmatch_wgs,
                                   out_coor_system= gladtile,
                                   cell_size=arcpy.Describe(gladtile).meanCellWidth,
                                   resampling_type='NEAREST')

#Create GLAD land-water mask
gladtile_mask = os.path.join(gladresgdb, '{}_mask'.format(gladtileid))
arcpy.CopyRaster_management(in_raster=Reclassify(gladtile, "Value",
                                                 RemapValue([[0,0], [1,1], [2,2], [3,2], [4,2], [5,2],
                                                             [6,2], [7,2], [8,2], [10,1], [11,2], [12,0]])),
                            out_rasterdataset=gladtile_mask,
                            pixel_type='4_BIT')

#Prepare pixels that are water, under 0 m elevation and not already labeled as seamask by MOD44W for Nibbling
gladtile_shore1 = os.path.join(gladresgdb, '{}_shore1'.format(gladtileid))
#If seawater in MODIS seamask and water in GLAD:
#   9
#else:
#   if elevation > 0 or land in glad:
#       glad values
#   else (i.e. <0 & water in glad):
#       NoData
if not arcpy.Exists(gladtile_shore1):
    Con((Raster(mod44w_gladmatch_wgs) == 4) & (Raster(gladtile_mask)==2),
        3,
        Con((Raster(alos_rsp)>0) | (Raster(gladtile_mask) < 2),
        Raster(gladtile_mask))).save(gladtile_shore1)

#Expand seamask in contiguous areas < 0 meters in elevation and identified as water in GLAD
outnibble1 = os.path.join(gladresgdb, '{}_nibble1'.format(gladtileid))
if not arcpy.Exists(outnibble1):
    Nibble(in_raster=Raster(gladtile_shore1), in_mask_raster=Raster(gladtile_shore1),
           nibble_values='DATA_ONLY', nibble_nodata='PROCESS_NODATA',
           in_zone_raster=Con(IsNull(Raster(gladtile_shore1)),1,
                              Con(Raster(gladtile_shore1)==3, 1, 0))
           ).save(outnibble1)

#Expand seamask by ten pixels in non-sea GLAD water pixels under 10 m in elevation
outexpand = os.path.join(gladresgdb, '{}_expand'.format(gladtileid))
if not arcpy.Exists(outexpand):
    Con(Raster(outnibble1)==2 & (Raster(alos_rsp)<10),
        Expand(in_raster=Raster(outnibble1), number_cells=10, zone_values=3),
        Raster(outnibble1)).save(outexpand)

#Fill in remaining water pixels under 0 m elevation and not already labeled with nearest water value, whether inland or sea
outnibble2 = os.path.join(gladresgdb, '{}_nibble2'.format(gladtileid))
if not arcpy.Exists(outnibble2):
    Nibble(in_raster=outexpand, in_mask_raster=outexpand,
           nibble_values='DATA_ONLY', nibble_nodata='PROCESS_NODATA',
           in_zone_raster=Raster(gladtile_mask)==2
           ).save(outnibble2)

#Get regions
outregion = os.path.join(gladresgdb, '{}_region'.format(gladtileid))
if not arcpy.Exists(outregion):
    RegionGroup(in_raster=outnibble2,
                number_neighbors='FOUR',
                zone_connectivity='WITHIN',
                excluded_value=1).save(outregion)

#Remove sea mask regions under 2000 pixels. This avoids having artefact patches surrounded by land or inland water
outregionclean = os.path.join(gladresgdb, '{}_regionclean'.format(gladtileid))
if not arcpy.Exists(outregionclean):
    Con(IsNull(ExtractByAttributes(outregion, 'LINK = 3 AND Count > 2000')),
        gladtile_mask,
        3).save(outregionclean)

#Fill in inland water zones entirely surrounded by sea water
outeuc = os.path.join(gladresgdb, '{}_euc'.format(gladtileid))
if not arcpy.Exists(outeuc):
    EucAllocation(in_source_data=InList(outregionclean, [0, 1, 3])).save(outeuc)

outzone = os.path.join(gladresgdb, '{}_zone'.format(gladtileid))
if not arcpy.Exists(outzone):
    ZonalStatistics(in_zone_data=outregion,
                    zone_field='Value',
                    in_value_raster=outeuc,
                    statistics_type='RANGE').save(outzone)

outseafinal = os.path.join(gladresgdb, '{}_seamask'.format(gladtileid))
if not arcpy.Exists(outseafinal):
    Con(IsNull(Raster(outregionclean)), gladtile, #To deal with remaining NoData (< 0 elevation)
        Con(((Raster(outzone)==0) & (Raster(outeuc)==3) & (Raster(outregionclean)==2)) | (Raster(outregionclean)==3),
            9,
            gladtile)).save(outseafinal)
print(time.time()-tic)






# alos_tilex = os.path.join(alos_dir, 'N040W073', 'ALPSMLC30_N040W073_DSM.tif')
# arcpy.Describe(alos_tilex).meanCellWidth
# arcpy.Describe(gladtile).meanCellWidth

########################################################################################################################
########################################################################################################################



#---------------------------- Aggregate GLAD to match HydroSHEDS -----------------------------------------------------

#Check aggregation ratio
cellsize_ratio = arcpy.Describe(hydrotemplate).meanCellWidth / arcpy.Describe(rawtilelist[0]).meanCellWidth
print('Aggregating GLAD by cell size ratio of {0} would lead to a difference in resolution of {1} mm'.format(
    math.floor(cellsize_ratio),
    11100000 * (arcpy.Describe(hydrotemplate).meanCellWidth - math.floor(cellsize_ratio) * arcpy.Describe(
        rawtilelist[0]).meanCellWidth)
))
# Make sure that the cell size ratio is a multiple of the number of rows and columns in DEM tiles to not have edge effects
float(arcpy.Describe(rawtilelist[0]).height) / math.floor(cellsize_ratio)
float(arcpy.Describe(rawtilelist[0]).width) / math.floor(cellsize_ratio)

hysogagg_dict = {}
for tile in rawtilelist:
    print(tile)
    hysogagg_dict[outaggk] = os.path.join(gladresgdb, '{0}_agg'.format(os.path.splitext(os.path.split(tile)[1])[0]))

    # Get unique categorical values
    if not arcpy.Exists(hysogagg_dict[outaggk]):
        if not Raster(tile).hasRAT and arcpy.Describe(tile).bandCount == 1:  # Build attribute table if doesn't exist
            try:
                arcpy.BuildRasterAttributeTable_management(tile)  # Does not work
            except Exception:
                e = sys.exc_info()[1]
                print(e.args[0])
                arcpy.DeleteRasterAttributeTable_management(tile)

        gladvals = {row[0] for row in arcpy.da.SearchCursor(tile, 'Value')}

        if len(gladvals) == 1:  # If only one value across entire tile
            if list(gladvals)[0] == 0:  # And that value is NoData
                print('Tile only has NoData values, deleting...')
                arcpy.Delete_management(tile)  # Delete tile

        else:
            # Divide and aggregate each band
            if compsr(tile, hydrotemplate):  # Make sure that share spatial reference with HydroSHEDS
                print('Divide into {1} bands and aggregate by rounded value of {2}'.format(
                    tile, len(gladvals), math.floor(cellsize_ratio)))
                arcpy.CompositeBands_management(in_rasters=catdivagg_list(inras=tile,
                                                                          vals=gladvals,
                                                                          exclude_list=[0, 12],
                                                                          aggratio=math.floor(cellsize_ratio)),
                                                out_raster=hysogagg_dict[outaggk])

#Differentiate sea water from inland water
processedtilelist = getfilelist(gladresgdb, 'class99_19.*[.]tif$')


#Mosaick tiles


#Resample to snap
hysog_500 = {}
for cont in hydrodir_list:
    hysog_500[cont] = os.path.join(hysogresgdb, 'hysogs_{}_500m'.format(cont))
    if not arcpy.Exists(hysog_500):
        print(hysog_500[cont])
        # Resample with nearest cell assignment
        arcpy.env.extent = arcpy.env.snapRaster = arcpy.env.cellSize = arcpy.env.mask = hydromask_dict[cont]
        arcpy.Resample_management(hysogagg, hysog_500[cont], cell_size=arcpy.env.cellSize, resampling_type='NEAREST')

