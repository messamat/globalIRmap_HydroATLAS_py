from utility_functions import *
from format_HydroSHEDS import *

wp_outdir = os.path.join(datdir, 'worldpop')
wp_resdir = os.path.join(resdir, 'worldpop.gdb')
pathcheckcreate(wp_resdir)
wpraw = os.path.join(wp_outdir, 'ppp_2020_1km_Aggregated.tif')

hydrolink = os.path.join(hydrogeomdir, 'Link_zone_grids', 'link_stream.gdb', 'link_str_arc')
wp_resmp = os.path.join(wp_resdir, 'wp_resample')
hydrolinknib = os.path.join(wp_resdir, 'link_nibble')
hydrolinkpop = os.path.join(wp_resdir, 'link_worldpop')

#Resample worldpop
arcpy.env.snapRaster = hydrolink
if not arcpy.Exists(wp_resmp):
    arcpy.Resample_management(in_raster=wpraw,
                              out_raster=wp_resmp,
                              cell_size = arcpy.Describe(hydrolink).meanCellWidth,
                              resampling_type= 'NEAREST')

#Run nibble to fill all
if not arcpy.Exists(hydrolinknib):
    Nibble(in_raster=Con(~IsNull(Raster(wp_resmp)) & IsNull(Raster(hydrolink)), 0, Raster(hydrolink)),
           in_mask_raster=hydrolink,
                  nibble_values='DATA_ONLY',
                  nibble_nodata='PRESERVE_NODATA').save(hydrolinknib)

#Get zonal statistics to compute the population that is closest to each river reach
if not arcpy.Exists(hydrolinkpop):
    ZonalStatisticsAsTable(in_zone_data=hydrolinknib,
                           zone_field='VALUE',
                           in_value_raster=wp_resmp,
                           out_table=hydrolinkpop,
                           ignore_nodata='DATA',
                           statistics_type='SUM')