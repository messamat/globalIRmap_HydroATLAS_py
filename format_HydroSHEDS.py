from utility_functions import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

hydrogeomdir = os.path.join(datdir, 'Bernhard', 'HydroATLAS', 'HydroATLAS_Geometry')
hydrotemplate = os.path.join(hydrogeomdir, 'Masks', 'hydrosheds_landmask_15s.gdb', 'hys_land_15s')
hydrocoast = os.path.join(hydrogeomdir, 'Ocean_correction', 'ocean_mask_20km_global.gdb', 'oc_mask_20km')

hydroresdir = os.path.join(resdir, 'HydroSHEDS')
hydroresgdb = os.path.join(resdir, 'hydrosheds.gdb')

coast_10pxband = os.path.join(hydroresgdb, 'coast_10pxband')
hydroregions = os.path.join(hydroresgdb, 'hys_land_regions_15s')
hydroregions_poly = os.path.join(hydroresgdb,'hys_land_regions_polysimple')


if __name__ == '__main__':
    pathcheckcreate(hydroresdir)
    pathcheckcreate(hydroresgdb)

    #Create 5 km extension inland around HydroSHEDS coastlines
    Con(IsNull(hydrocoast) & (~IsNull(hydrotemplate)),
        Expand(hydrocoast, number_cells=10, zone_values=1)).save(coast_10pxband)

    # Create HydroSHEDS regions
    if not arcpy.Exists(hydroregions):
        RegionGroup(in_raster=hydrotemplate,
                    number_neighbors='EIGHT',
                    zone_connectivity='WITHIN',
                    add_link='NO_LINK').save(hydroregions)

    # Convert regions to polygons
    if not arcpy.Exists(hydroregions_poly):
        arcpy.RasterToPolygon_conversion(hydroregions, hydroregions_poly, simplify='SIMPLIFY', raster_field='Value')

    # Assign ID of nearest reach for every



