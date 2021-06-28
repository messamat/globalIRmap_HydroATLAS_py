from utility_functions import *
from format_HydroSHEDS import *

wp_outdir = os.path.join(datdir, 'worldpop_100m')
wp_resdir = os.path.join(resdir, 'worldpop.gdb')
pathcheckcreate(wp_resdir)
#wpraw = os.path.join(wp_outdir, 'ppp_2020_1km_Aggregated.tif')

hydrolink = os.path.join(hydrogeomdir, 'Link_zone_grids', 'link_stream.gdb', 'link_str_arc')
linkhyriv = os.path.join(hydrogeomdir, 'Link_shapefiles', 'link_hyriv_v10.gdb', 'link_hyriv_v10')

#Output data
wp_mosaic = os.path.join(wp_resdir, 'wp_mosaicked')
wp_ag = os.path.join(wp_resdir, 'wp_aggregated')
link_o001 = os.path.join(wp_resdir, 'link_str_arc001')
hydrolinknib = os.path.join(wp_resdir, 'link_nibble')
hydrolinkpop = os.path.join(wp_resdir, 'link_worldpop')

wptiles_raw = getfilelist(wp_outdir, repattern='[a-z]{3}_ppp_2020_constrained.tif')

#Aggregate worldpop tiles
cellsize_ratio = arcpy.Describe(hydrolink).meanCellWidth / arcpy.Describe(wptiles_raw[0]).meanCellWidth
print('Aggregating worldpop by cell size ratio of {0} would lead to a difference in resolution of {1} m'.format(
    math.floor(cellsize_ratio),
    111000 * (arcpy.Describe(hydrolink).meanCellWidth - math.floor(cellsize_ratio) * arcpy.Describe(
        wptiles_raw[0]).meanCellWidth)
))


arcpy.env.snapRaster = hydrolink
for country_path in wptiles_raw:
    wp_ag_country = os.path.join(wp_resdir,
                                 "{0}_aggregated".format(os.path.splitext(os.path.split(country_path)[1])[0]))
    #print(wp_ag_country)
    if not arcpy.Exists(wp_ag_country):
        Aggregate(in_raster=country_path, cell_factor= int(round(cellsize_ratio)), aggregation_type='SUM'
                  ).save(wp_ag_country)


#Mosaick worlpop tiles
wptiles_agg = getfilelist(wp_resdir, repattern='[a-z]{3}_ppp_2020_constrained_aggregated$')
for i in range(0, len(wptiles_agg), 4):
    in_tiles = wptiles_agg[i:(i+4)]
    print(in_tiles)
    out_mosaick = "{0}_{1}".format(wp_mosaic, i)
    if not arcpy.Exists(out_mosaick):
        arcpy.MosaicToNewRaster_management(input_rasters=in_tiles,
                                           output_location=os.path.split(out_mosaick)[0],
                                           raster_dataset_name_with_extension=os.path.split(out_mosaick)[1],
                                           pixel_type = '32_BIT_FLOAT',
                                           number_of_bands= 1,
                                           mosaic_method = 'SUM')

wptiles_mosaicked = getfilelist(wp_resdir, repattern='wp_mosaicked_[0-9]{1,3}$')
arcpy.MosaicToNewRaster_management(input_rasters=wptiles_mosaicked ,
                                           output_location=os.path.split(wp_mosaic)[0],
                                           raster_dataset_name_with_extension=os.path.split(wp_mosaic)[1],
                                           pixel_type = '32_BIT_FLOAT',
                                           number_of_bands= 1,
                                           mosaic_method = 'SUM')

#Remove reaches with < 0.1 m3/s
arcpy.MakeFeatureLayer_management(linkhyriv, 'link_lyr', where_clause='DIS_AV_CMS >= 0.1')
arcpy.PolylineToRaster_conversion(in_features='link_lyr', value_field='HYRIV_ID',
                                  out_rasterdataset=link_o001, cell_assignment='MAXIMUM_COMBINED_LENGTH',
                                  priority_field='DIS_AV_CMS', cellsize=hydrolink)

#Run nibble to fill all
if not arcpy.Exists(hydrolinknib):
    Nibble(in_raster=Con(~IsNull(Raster(wp_mosaic)) & IsNull(Raster(link_o001)), 0, Raster(link_o001)),
           in_mask_raster=link_o001,
           nibble_values='DATA_ONLY',
           nibble_nodata='PRESERVE_NODATA').save(hydrolinknib)

#Get zonal statistics to compute the population that is closest to each river reach
if not arcpy.Exists(hydrolinkpop):
    ZonalStatisticsAsTable(in_zone_data=hydrolinknib,
                           zone_field='VALUE',
                           in_value_raster=wp_mosaic,
                           out_table=hydrolinkpop,
                           ignore_nodata='DATA',
                           statistics_type='SUM')
# #Add HYRIV_ID to table
# linkhryiv_dict = {row[0]:row[1] for row in arcpy.da.SearchCursor(linkhyriv, ['LINK_RIV', 'HYRIV_ID'])}
# arcpy.AddField_management(hydrolinkpop, 'HYRIV_ID', 'LONG')
# with arcpy.da.UpdateCursor(hydrolinkpop, ['VALUE', 'HYRIV_ID']) as cursor:
#     for row in cursor:
#         if row[0] in linkhryiv_dict:
#             row[1] = linkhryiv_dict[row[0]]
#             cursor.updateRow(row)