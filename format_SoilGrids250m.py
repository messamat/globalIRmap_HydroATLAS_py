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
mediumdirdict = {i: os.path.join(sgmediumdir, i) for i in smalldirdict}
mosaicdict = {lyr:os.path.join(sgresgdb, lyr) for lyr in mediumdirdict}

if not all([arcpy.Exists(lyr) for lyr in mosaicdict.values()]):
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

#Compute aggregate texture values by weighted average (no need for trapezoidal equation from 2019 onward (v2)) https://gis.stackexchange.com/questions/344070/depths-in-clay-content-map
mosaicdf = pd.DataFrame.from_dict(mosaicdict, orient='index').reset_index()
mosaicdf.columns = ['name', 'path']
mosaicdf_format = pd.concat([mosaicdf,
                             mosaicdf['name'].str.replace('(cm)|(_mean)', '').str.split("[_]", expand = True)],
                            axis=1).\
    rename(columns={0: "texture", 1: "horizon_top", 2 : "horizon_bottom"}).\
    sort_values(['texture', 'horizon_top'])

mosaicdf_format[["horizon_top", "horizon_bottom"]] = mosaicdf_format[["horizon_top", "horizon_bottom"]].apply(pd.to_numeric)
mosaicdf_format['thickness'] = mosaicdf_format["horizon_bottom"] - mosaicdf_format["horizon_top"]

def waverage_soilgrids(in_df, mindepth, maxdepth, outdir):
    #Subset horizons to only keep the requested depths
    df_sub = in_df[(in_df['horizon_top'] >= mindepth) & (in_df['horizon_bottom'] <= maxdepth)].\
        sort_values(['horizon_top'])

    for texture, texturegroup in df_sub.groupby('texture'):
        out_average = os.path.join(sgresgdb, '{0}_{1}_{2}_wmean'.format(texture, mindepth, maxdepth))
        if not arcpy.Exists(out_average):
            print('Processing {}...'.format(out_average))
            Divide(
                WeightedSum(
                    WSTable(
                        [[row['path'], "VALUE", row['thickness']] for index, row in texturegroup.iterrows()])),
                sum(texturegroup['thickness'])
            ).save(out_average)

waverage_soilgrids(in_df=mosaicdf_format,
                   mindepth=0,
                   maxdepth=100,
                   outdir=sgresgdb)


#Compute texture class




#Compute aggregate texture values by weighted average (no need for trapezoidal equation from 2019 onward (v2)) https://gis.stackexchange.com/questions/344070/depths-in-clay-content-map




#Check ratio of resolutions
#Re-project
#Snap
#Aggregate and/or resample
#Run accumulation


#Because there is no way to know what is inland vs. sea water, perhaps just re-project to wgs84, resample, and snap.
#Compute everything while ignoring NoData values
#Fill in NoData values with -9999 and use these in model rather than excluding these values.

#Compute soil texture class based on soiltexture R package and then compute HYSOGS250m

