from utility_functions import *

hysogdir = os.path.join(datdir, 'hysog')
pathcheckcreate(hysogdir)
hysogresgdb = os.path.join(resdir, 'hysog.gdb')
pathcheckcreate(hysogresgdb)
hysogmosaic = os.path.join(hysogresgdb, 'hysog_mosaic')

#DOI of dataset is https://doi.org/10.3334/ORNLDAAC/1566
#This last number is the dataset ID to be used for search in WebMapService
sdatwcs = WebCoverageService('https://webmap.ornl.gov/ogcbroker/wcs')
print(str(len(sdatwcs.contents)) + ' layers found from ' + sdatwcs.identification.title)
# filter layers
hysog_wcsid = filter(lambda x: x.startswith('1566_'), sdatwcs.contents)[0]
print(hysog_wcsid)

hysogbblist = divbb(bbox=sdatwcs[hysog_wcsid].boundingBoxWGS84,
                    res=sdatwcs[hysog_wcsid].grid.offsetvectors[0][0],
                    divratio=10)
hysogoutlist = ['{0}_{1}.tif'.format(os.path.join(hysogdir, 'hysog'), i)
                for i in xrange(0, len(hysogbblist))]
if not all([os.path.isfile(i) for i in hysogoutlist]):
    x=0
    for bb in hysogbblist:
        #print(bb)
        outtile = hysogoutlist[x]
        if not os.path.isfile(outtile):
            print(outtile)
            hysog_wc = sdatwcs.getCoverage(identifier=hysog_wcsid,
                                           bbox=bb,
                                           crs='EPSG:4326',
                                           format='Geotiff_BYTE',
                                           interpolation='NEAREST',
                                           resx=sdatwcs[hysog_wcsid].grid.offsetvectors[0][0],
                                           resy=sdatwcs[hysog_wcsid].grid.offsetvectors[0][0])

            with open(outtile, "wb") as local_file:
                local_file.write(hysog_wc.read())
        else:
            print("{} already exists...".format(outtile))

        x+=1

# #Only keep tiles with data - only works with numpy > 1.9.3 but breaks arcpy
# for tilepath in hysogoutlist:
#     print(tilepath)
#     tiledat = gdal_array.LoadFile(tilepath)
#     if tiledat.max() == 0:
#         hysogoutlist.remove(tilepath)

#mosaic them
print('Mosaicking hysogs tiles...')
arcpy.MosaicToNewRaster_management(hysogoutlist, output_location=hysogresgdb,
                                   raster_dataset_name_with_extension= 'hysog_mosaic',
                                   pixel_type= '8_BIT_UNSIGNED',
                                   number_of_bands = 1,
                                   mosaic_colormap_mode = 'FIRST')