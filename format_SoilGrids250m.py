from utility_functions import *
from format_HydroSHEDS import *

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

#Define NoData value
nodatavalue = -9999

########################################## MOSAIC TILES ################################################################
#Create a list of files for each texture and depth
checkproj = False
sg_subdirl = defaultdict(list)
print('Getting list of tiles...')
for f in getfilelist(sg_outdir, 'tileSG.*tif$'):
    print(f)
    sg_subdirl[os.path.split(f)[0]].append(f)
    if checkproj:
        if arcpy.Describe(f).SpatialReference.name=='Unknown':
            arcpy.DefineProjection_management(f, goode_sr)

tileinterval  = 100
smalldirdict = {os.path.split(partdepth)[1]: os.path.join(sgsmalldir, os.path.split(partdepth)[1]) for partdepth in sg_subdirl}
mediumdirdict = {i: os.path.join(sgmediumdir, i) for i in smalldirdict}
mosaicdict = {lyr:os.path.join(sgresgdb, lyr) for lyr in mediumdirdict}
formatdict = {lyr:os.path.join(sgresgdb, '{}_format'.format(lyr)) for lyr in mediumdirdict}

if not all([arcpy.Exists(lyr) for lyr in formatdict.values()]):
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
                arcpy.MosaicToNewRaster_management(input_rasters=sg_subdirl[partdepth][tilel[0]:tilel[1]],
                                                   output_location=os.path.split(outtile)[0],
                                                   raster_dataset_name_with_extension= os.path.split(outtile)[1],
                                                   number_of_bands=1,
                                                   pixel_type='16_BIT_SIGNED')
            else:
                print('{} already exists...'.format(outtile))

    #Remosaick using MAX
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
                                                   mosaic_method='MAXIMUM',
                                                   pixel_type='16_BIT_SIGNED')
            else:
                print('{} already exists...'.format(outtile))

    #Last remosaicking
    for dir in mosaicdict:
        tilel = getfilelist(mediumdirdict[dir], '.*[.]tif$')
        outmosaic =mosaicdict[dir]
        if tilel is not None and not arcpy.Exists(outmosaic):
            print('Processing {}...'.format(outmosaic))
            arcpy.MosaicToNewRaster_management(input_rasters=tilel,
                                               output_location=os.path.split(outmosaic)[0],
                                               raster_dataset_name_with_extension=os.path.split(outmosaic)[1],
                                               number_of_bands=1,
                                               mosaic_method='MAXIMUM',
                                               pixel_type='16_BIT_SIGNED')

########################################## Compute aggregate texture values by weighted average #########################
#No need for trapezoidal equation from 2019 onward (v2)) https://gis.stackexchange.com/questions/344070/depths-in-clay-content-map
formatdf = pd.DataFrame.from_dict(formatdict, orient='index').reset_index()
formatdf.columns = ['name', 'path']
formatdf_format = pd.concat([formatdf,
                             formatdf['name'].str.replace('(cm)|(_mean)', '').str.split("[_]", expand = True)],
                            axis=1).\
    rename(columns={0: "texture", 1: "horizon_top", 2 : "horizon_bottom"}).\
    sort_values(['texture', 'horizon_top'])

formatdf_format[["horizon_top", "horizon_bottom"]] = formatdf_format[["horizon_top", "horizon_bottom"]].apply(pd.to_numeric)
formatdf_format['thickness'] = formatdf_format["horizon_bottom"] - formatdf_format["horizon_top"]

def waverage_soilgrids(in_df, mindepth, maxdepth, outdir):
    #Subset horizons to only keep the requested depths
    df_sub = in_df[(in_df['horizon_top'] >= mindepth) & (in_df['horizon_bottom'] <= maxdepth)].\
        sort_values(['horizon_top'])

    for texture, texturegroup in df_sub.groupby('texture'):
        out_average = os.path.join(sgresgdb, '{0}_{1}_{2}_wmean'.format(texture, mindepth, maxdepth))
        if not arcpy.Exists(out_average):
            print('Processing {}...'.format(out_average))
            wsum = WeightedSum(
                WSTable(
                    [[row['path'], "VALUE", row['thickness']] for index, row in texturegroup.iterrows()]))
            (wsum/sum(texturegroup['thickness'])).save(out_average)

waverage_soilgrids(in_df=formatdf_format,
                   mindepth=0,
                   maxdepth=100,
                   outdir=sgresgdb)

##########################################Aggregate to HydroSHEDS resolution and extent ##############################
#Get list of rasters to project
sg_wmean = getfilelist(sgresgdb, '.*_wmean')
#The original cell size is exactly twice that of HydroSHEDS, so can project and snap, perform euclidean allocation, and then aggregate

#Re-project and snap (as exactly half the resolution of HydroSHEDS)
arcpy.env.mask = arcpy.env.extent = hydrotemplate
for lyr in sg_wmean:
    outproj = os.path.join(sgresgdb, '{}proj'.format(sg_wmean))
    if not arcpy.Exists(outproj):
        print('Processing {}...'.format(outproj))
        arcpy.ProjectRaster_management(lyr, outproj,
                                       out_coor_system=hydrotemplate,
                                       resampling_type='NEAREST',
                                       cell_size=1/480.0, #From Hengl et al. 2017
                                       )
    else:
        print('{} already exists...'.format(outproj))

    # Euclidean allocation in all NoData areas within 5 km of the coast from HydroSHEDS
    outnib = os.path.join(sgresgdb, '{}nibble'.format(sg_wmean))
    if not arcpy.Exists(outnib):
        print('Processing {}...'.format(outnib))
        try:
            arcpy.env.cellsize = outproj
            mismask = Con((IsNull(outproj) | (outproj == 0)) & (~IsNull(coast_10pxband)), coast_10pxband)

            # Perform euclidean allocation to those pixels
            Nibble(in_raster=Con(~IsNull(mismask), nodatavalue, outproj),
                   # where mismask is not NoData (pixels for which outproj is NoData but coast_10pxband has data), assign nodatavalue (provided by user, not NoData), otherwise, keep outproj data (see Nibble tool)
                   in_mask_raster=outproj,
                   nibble_values='DATA_ONLY',
                   nibble_nodata='PRESERVE_NODATA').save(outnib)

        except Exception:
            print("Exception in user code:")
            traceback.print_exc(file=sys.stdout)
            del mismask
            arcpy.ResetEnvironments()

    else:
        print('{} already exists...'.format(outnib))

    arcpy.ResetEnvironments()

    #Aggregate pixel size to that of HydroSHEDS
    arcpy.env.mask = arcpy.env.extent = hydrotemplate
    outagg = os.path.join(sgresgdb, '{}agg'.format(sg_wmean))
    if not arcpy.Exists(outagg):
        print('Processing {}...'.format(outagg))
        Aggregate(in_raster=outnib,
                  cell_factor=2,
                  aggregation_type='MEAN',
                  extent_handling='EXPAND',
                  ignore_nodata='DATA')
    else:
        print('{} already exists...'.format(outagg))


#Compute soil texture class based on soiltexture R package and then compute HYSOGS250m
