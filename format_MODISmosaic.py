'''Purpose: pre-format and mosaic MODIS ocean mask'''

from utility_functions import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

# Set up dir structure
rootdir = os.path.dirname(os.path.abspath(__file__)).split('\\src')[0]
datdir = os.path.join(rootdir, 'data')
resdir = os.path.join(rootdir, 'results')
scratchdir = os.path.join(rootdir, 'scratch')
scratchgdb = os.path.join(scratchdir, 'scratch.gdb')
pathcheckcreate(scratchgdb)
arcpy.env.scratchWorkspace = scratchgdb

#HydroSHEDS dirs
hydrodir = os.path.join(datdir, 'HydroSHEDS')

# MODIS dirs
mod44w_outdir = os.path.join(datdir, 'mod44w')
mod44w_resgdb = os.path.join(resdir, 'mod44w.gdb')
mod44w_mosaic = os.path.join(mod44w_resgdb, 'mod44w_mosaic')
mod44w_QAmosaic = os.path.join(mod44w_resgdb, 'mod44w_QAmosaic')
mod44w_shore = os.path.join(mod44w_resgdb, 'mod44w_shore')
mod44w_nibbled = os.path.join(mod44w_resgdb, 'mod44w_nib')
pathcheckcreate(mod44w_resgdb)

# Input dir and lyrs
hysogresgdb = os.path.join(resdir, 'hysogs.gdb')
hysogmosaic = os.path.join(hysogresgdb, 'hysogs_mosaic')

#---------------------------------------- Create HydroSHEDS landmask ---------------------------------------------------
hydromaskdir = os.path.join(resdir, 'HydroSHEDS', 'mask')
hydromaskgdb = os.path.join(resdir, 'HydroSHEDS', 'mask.gdb')
pathcheckcreate(hydromaskdir)
if not arcpy.Exists(hydromaskgdb):
    arcpy.CreateFileGDB_management(os.path.split(hydromaskgdb)[0], os.path.split(hydromaskgdb)[1])

#------------- Format direction rasters into 1-NoData masks ------------------------------------------------------------
hydrodir_list = {}
for (dirpath, dirnames, filenames) in \
        arcpy.da.Walk(os.path.join(datdir, 'HydroSHEDS'), topdown=True, datatype="RasterDataset", type="GRID"):
    for filename in filenames:
        if re.search('.*dir_15s$', filename):
            #print(filename)
            hydrodir_list[re.search('^[a-z]*(?=_dir_15s$)', filename).group()] = os.path.join(dirpath, filename)

continents = hydrodir_list.keys()

hydromask_dict = {}
for cont in hydrodir_list.keys():
    tilepath = hydrodir_list[cont]
    hydromask_dict[cont] = os.path.join(hydromaskgdb, re.sub('dir', 'mask', os.path.split(tilepath)[1]))
    tiledesc = arcpy.Describe(tilepath)

    if not arcpy.Exists(hydromask_dict[cont]):
        print('Processing {}...'.format(hydromask_dict[cont]))
        arcpy.env.extent = arcpy.env.snapRaster = tilepath
        #Because HydroSHEDS cell size is set with 16 digits while arcpy.env assignment by layer only handles 12,
        #explicity use arcpy.Describe — still doesn't work unless use file gdb
        arcpy.env.XYResolution = "0.0000000000000001 degrees"
        arcpy.env.cellSize = arcpy.Describe(tilepath).meanCellWidth
        print('%.17f' % float(arcpy.env.cellSize))

        try:
            #Create a 1-NoData mask
            arcpy.CopyRaster_management(Con(~IsNull(Raster(tilepath)), 1),
                                        hydromask_dict[cont], pixel_type='8_BIT_UNSIGNED')

            #Check whether everything is the same
            maskdesc = arcpy.Describe(hydromask_dict[cont])
            print('Equal extents? {}'.format(maskdesc.Extent.JSON == tiledesc.Extent.JSON))
            print('Equal cell size? {}'.format(maskdesc.meanCellWidth == tiledesc.meanCellWidth))
            print('Same Spatial Reference? {}'.format(compsr(tilepath, hydromask_dict[cont])))

        except Exception:
            print("Exception in user code:")
            traceback.print_exc(file=sys.stdout)
            arcpy.ResetEnvironments()

hydrotemplate = hydromask_dict[hydromask_dict.keys()[0]]  # Grab HydroSHEDS layer for one continent as template


#----------------------------------------- Pre-Format MODIS 250m water mask ------------------------------------------------
for tile in getfilelist(mod44w_outdir, '.*[.]hdf$'):
    #Generate land-water mask
    outgrid = os.path.join(mod44w_resgdb, re.sub('[.]', '_', os.path.splitext(os.path.split(tile)[1])[0]))
    outgrid_wgs = '{}_wgs84'.format(outgrid)
    if not arcpy.Exists(outgrid):
        print(outgrid)
        arcpy.ExtractSubDataset_management(in_raster=tile, out_raster=outgrid, subdataset_index=0)
    if not arcpy.Exists(outgrid_wgs):
        print(outgrid_wgs)
        arcpy.env.snapRaster = hysogmosaic
        arcpy.ProjectRaster_management(outgrid, outgrid_wgs, out_coor_system=hydrotemplate,
                                       resampling_type='NEAREST', cell_size=arcpy.Describe(hysogmosaic).meanCellWidth)

    #Generate QA mask that also identifies water
    outQA = os.path.join(mod44w_resgdb, "QA_{}".format(re.sub('[.]', '_', os.path.splitext(os.path.split(tile)[1])[0])))
    outQA_wgs = '{}_wgs84'.format(outQA)
    if not arcpy.Exists(outQA):
        print(outQA)
        arcpy.ExtractSubDataset_management(in_raster=tile, out_raster=outQA, subdataset_index=1)
    if not arcpy.Exists(outQA_wgs):
        print(outQA_wgs)
        arcpy.env.snapRaster = hysogmosaic
        arcpy.ProjectRaster_management(outQA, outQA_wgs, out_coor_system=hydrotemplate,
                                       resampling_type='NEAREST', cell_size=arcpy.Describe(hysogmosaic).meanCellWidth)
    arcpy.ResetEnvironments()

if not arcpy.Exists(mod44w_mosaic):
    print('Mosaicking {}...'.format(mod44w_mosaic))
    arcpy.MosaicToNewRaster_management(
        getfilelist(dir=mod44w_resgdb, repattern='^(?!=QA_)MOD44W.*_wgs84$', gdbf=True, nongdbf=False),
        output_location=mod44w_resgdb,
        raster_dataset_name_with_extension=os.path.split(mod44w_mosaic)[1],
        number_of_bands=1)

if not Raster(mod44w_mosaic).hasRAT:
    arcpy.BuildRasterAttributeTable_management(mod44w_mosaic)

if not arcpy.Exists(mod44w_QAmosaic):
    print('Mosaicking {}...'.format(mod44w_QAmosaic))
    arcpy.MosaicToNewRaster_management(
        getfilelist(dir=mod44w_resgdb, repattern='^QA.*_wgs84$', gdbf=True, nongdbf=False),
        output_location=mod44w_resgdb,
        raster_dataset_name_with_extension=os.path.split(mod44w_QAmosaic)[1],
        number_of_bands=1)

if not Raster(mod44w_QAmosaic).hasRAT:
    arcpy.BuildRasterAttributeTable_management(mod44w_QAmosaic)

""" Not used in the end
# ----------------------------------------- Resample EarthEnv DEM 90 based on MODIS ------------------------------------
ee_outdir = os.path.join(datdir, 'earthenv')
ee_resgdb = os.path.join(resdir, 'earthenv.gdb')
pathcheckcreate((ee_resgdb))
ee_tilelist = getfilelist(ee_outdir, '.*[.]bil$', gdbf = False, nongdbf= True)

#Get ratio in cell size between MODIS and EarthEnv DEm 90
cellsize_ratio = arcpy.Describe(mod44w_mosaic).meanCellWidth / arcpy.Describe(ee_tilelist[0]).meanCellWidth
print('Aggregating DEM by cell size ratio of 2.5 would lead to a difference in resolution of {} mm'.format(
    11100000*(arcpy.Describe(mod44w_mosaic).meanCellWidth-round(cellsize_ratio, 1)*arcpy.Describe(ee_tilelist[0]).meanCellWidth)
))
#Make sure that the cell size ratio is a multiple of the number of rows and columns in DEM tiles to not have edge effects
float(arcpy.Describe(ee_tilelist[0]).height) / 2
float(arcpy.Describe(ee_tilelist[0]).width) / 2

delete_seatiles = False
for tile in ee_tilelist:
    if delete_seatiles:
        if not Raster(tile).hasRAT:  # Build attribute table if doesn't exist
            try:
                arcpy.BuildRasterAttributeTable_management(tile)  # Does not work
            except Exception:
                e = sys.exc_info()[1]
                print(e.args[0])
                arcpy.DeleteRasterAttributeTable_management(tile)

        tilevals = {row[0] for row in arcpy.da.SearchCursor(tile, 'Value')}

        if len(tilevals)==1:
            if list(tilevals)[0] == 0:
                tarf = '{}.tar'.format(os.path.splitext(tile)[0])
                print('Deleting {0} and {1} as only 0 values'.format(tile, tarf))
                arcpy.Delete_management(tile)
                if os.path.exists(tarf):
                    os.remove(tarf)
                ee_tilelist.remove(tile)
                pass

    outtile = re.sub('[-]', '_',
                     os.path.join(ee_resgdb, '{}_180'.format(os.path.splitext(os.path.split(tile)[1])[0])))
    if not arcpy.Exists(outtile):
        print('Aggregating to {}...'.format(outtile))
        Aggregate(tile, cell_factor=round(cellsize_ratio),
                  aggregation_type='MEDIAN', extent_handling='EXPAND').save(
            outtile)
        print('Same extent? {}'.format(arcpy.Describe(tile).extent.JSON == arcpy.Describe(outtile).extent.JSON))

#Mosaic and aggregate DEM tiles based on HydroSHEDS continent tiles at
ee_tilelist180 = getfilelist(ee_resgdb, 'EarthEnv_DEM90_[NS][0-9]{2}[WE][0-9]{3}_250$', gdbf=True, nongdbf=False)
ee_mosaic = os.path.join(ee_resgdb, 'ee_mosaic')
ee_mosaic250 = os.path.join(ee_resgdb, 'ee_mosaic250')

arcpy.MosaicToNewRaster_management(input_rasters=ee_tilelist180,
                                   output_location=os.path.split(ee_mosaic)[0],
                                   raster_dataset_name_with_extension=os.path.split(ee_mosaic)[1],
                                   pixel_type='16_BIT_SIGNED',
                                   number_of_bands=1,
                                   mosaic_method='MEAN')

arcpy.env.cellSize = mod44w_mosaic
arcpy.env.snapRaster = mod44w_mosaic
arcpy.Resample_management(ee_mosaic, ee_mosaic250,
                          cell_size=arcpy.Describe(mod44w_mosaic).meanCellWidth,
                          resampling_type='Majority')

#With focal statistics, check whether pixels are entirely surrounded by elevations > 0 #################################
#3x3 window


# ----------------------------------------- Identify sea and inland water pixels in MODIS ------------------------------
#Extend QA modis ocean mask to all contiguous areas with 0 elevation in majority-smoothed 3x3 EarthEnv DEM (to deal with ASTER noise up North)
#and classified as water in the main MODIS layer
arcpy.env.extent = arcpy.env.snapRaster = mod44w_mosaic
Con(~((Raster(mod44w_mosaic) == 1) &
      ((Raster(mod44w_QAmosaic) == 1) | (Raster(mod44w_QAmosaic) == 2)) &
      Raster(ee_mosaic250) <= 1),
    1).save(mod44w_shore)

arcpy.env.scratchWorkspace = scratchgdb
#This is parallel-enabled. No need to parallelize. However, extremely storage-hungry, so choose scratch workspace wisely
#But always crashes, try to run on tiles
mod44w_bbox = tuple(getattr(arcpy.Describe(mod44w_mosaic).Extent, i) for i in ['XMin', 'YMin', 'XMax', 'YMax'])
mod44w_bblist = divbb(bbox= mod44w_bbox, res=arcpy.Describe(mod44w_mosaic).meanCellWidth, divratio=10)

x=0
for bb in mod44w_bblist:
    try:
        outnibble = '{0}{1}'.format(mod44w_nibbled, x)
        if not arcpy.Exists(outnibble):
            print(outnibble)
            arcpy.env.extent = ' '.join(map(str, bb))
            arcpy.env.snapRaster = mod44w_mosaic
            Nibble(in_raster=Raster(mod44w_QAmosaic), in_mask_raster=Raster(mod44w_shore), nibble_values='DATA_ONLY',
                   nibble_nodata='PRESERVE_NODATA', in_zone_raster=Raster(mod44w_mosaic)).save(outnibble)

            arcpy.ClearEnvironment('extent')
        else:
            print('{} already exists...'.format(outnibble))
    except:
        traceback.print_exc()
        arcpy.ClearEnvironment('extent')
    x += 1

#Align with HYSOGS mosaic

# ----------------------------------------- Rasterize, align, and resample GLIMS ---------------------------------------
glims_outdir = os.path.join(datdir, 'glims')
glims_poly =  os.path.join(glims_outdir, 'glims_download_56134', 'glims_polygons.shp')
glims_resgdb = os.path.join(resdir, 'glims.gdb')
pathcheckcreate(glims_resgdb)
glims_ras = os.path.join(glims_resgdb, 'glims_ras')

if 'mask' not in [f.name for f in arcpy.ListFields(glims_poly)]:
    arcpy.AddField_management(glims_poly, 'mask', 'SHORT', field_precision=1)

arcpy.env.extent = arcpy.env.snapRaster = arcpy.env.cellSize = hysogmosaic
arcpy.PolygonToRaster_conversion(in_features=glims_poly,
                                 value_field = 'mask',
                                 out_rasterdataset=glims_ras,
                                 cell_assignment="MAXIMUM_AREA",
                                 cellsize=hysogmosaic)


# ---------------------------------------- Format hysogs ---------------------------------------------------------------
ee_mosaic = {}
for cont in hydrodir_list.keys():
    ee_mosaic[cont] = os.path.join(ee_resgdb, 'ee_mosaic_{}'.format(cont))
    if not arcpy.Exists(ee_mosaic[cont]):
        print('Mosaicking and resampling {}...'.format(ee_mosaic[cont]))
        arcpy.env.extent = hydromask_dict[cont]
        # Subset tiles to only keep those that intersect HydroSHEDS continent tile
        ee_seltiles = [i for i in ee_tilelist250
                       if arcpy.Describe(i).extent.overlaps(arcpy.env.extent) or
                       arcpy.Describe(i).extent.touches(arcpy.env.extent) or
                       arcpy.Describe(i).extent.within(arcpy.env.extent)]

        arcpy.env.snapRaster = mod44w_mosaic
        arcpy.MosaicToNewRaster_management(input_rasters=ee_seltiles,
                                           output_location=os.path.split(ee_mosaic[cont])[0],
                                           raster_dataset_name_with_extension=os.path.split(ee_mosaic[cont])[1],
                                           pixel_type='16_BIT_SIGNED',
                                           number_of_bands=1,
                                           mosaic_method='MEAN')
    else:
        print('{} already exists...'.format(ee_mosaic[cont]))


    # Then replace all 0s in HYSOGS with either 0 for inland water or NoData for sea

    # Check GlobeCover 30 m mask too
    arcpy.ResetEnvironments()


hysogagg = os.path.join(hysogresgdb, 'hysogs_agg')

testdat = os.path.join(hysogresgdb, 'test')

# Identify permanent ice pixels as defined by SoilGrids
#


# Identify inland water vs ocean mask
# Change the former to 0, rest as NoData



# Get unique categorical values
if not arcpy.Exists(hysogagg):
    if not Raster(hysogmosaic).hasRAT and arcpy.Describe(hysogmosaic).bandCount == 1: #Build attribute table if doesn't exist
        try:
            arcpy.BuildRasterAttributeTable_management(hysogmosaic) #Does not work
        except Exception:
            e = sys.exc_info()[1]
            print(e.args[0])
            arcpy.DeleteRasterAttributeTable_management(hysogmosaic)

    hysogvals = {row[0] for row in arcpy.da.SearchCursor(hysogmosaic, 'Value')}

    #Divide and aggregate each band
    if compsr(hysogmosaic, hydrotemplate):  # Make sure that share spatial reference with HydroSHEDS
        # Check cellsize ratio
        cellsize_ratio = arcpy.Describe(hydrotemplate).meanCellWidth / arcpy.Describe(hysogmosaic).Children[0].meanCellWidth
        print('Divide {0} into {1} bands and aggregate by rounded value of {2}'.format(
            hysogmosaic, len(hysogvals)-1, cellsize_ratio))
        arcpy.CompositeBands_management(in_rasters=catdivagg_list(inras=hysogmosaic, vals=hysogvals,
                                                                  exclude_list=[0], aggratio=round(cellsize_ratio)),
                                        out_raster=hysogagg)

hysog_500 = {}
for cont in hydrodir_list:
    hysog_500[cont] = os.path.join(hysogresgdb, 'hysogs_{}_500m'.format(cont))
    if not arcpy.Exists(hysog_500):
        print(hysog_500[cont])
        #Resample with nearest cell assignment
        arcpy.env.extent = arcpy.env.snapRaster = arcpy.env.cellSize = arcpy.env.mask = hydromask_dict[cont]
        arcpy.Resample_management(hysogagg, hysog_500[cont], cell_size=arcpy.env.cellSize, resampling_type='NEAREST')


#Notes for cleaning and formatting
#Check out the generalization toolset
#https://desktop.arcgis.com/en/arcmap/10.7/tools/spatial-analyst-toolbox/an-overview-of-the-generalization-tools.htm
#Think of using Nibble to fill-in NoData regions
#Look at Region Group.
"""