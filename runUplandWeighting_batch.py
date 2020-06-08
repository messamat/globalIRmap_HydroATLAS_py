from utility_functions import *
from runUplandWeighting import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Folder structure
geomdir = os.path.join(datdir, 'Bernhard', 'HydroATLAS', 'HydroATLAS_Geometry')

#Input layers
directionras = os.path.join(geomdir, 'Flow_directions', 'flow_dir_15s_global.gdb', 'flow_dir_15s')
weightras = os.path.join(geomdir,'Accu_area_grids', 'pixel_area_skm_15s.gdb', 'px_area_skm_15s')
uplandras = os.path.join(geomdir, 'Accu_area_grids', 'upstream_area_skm_15s.gdb', 'up_area_skm_15s')

#Value grids
worldclim_value = getfilelist(os.path.join(resdir, 'worldclimv2.gdb'), '.*nibble$')

def hydroUplandWeighting(value_grid, direction_grid, weight_grid, upland_grid, scratch_dir, out_dir, overwrite=False):
    #Check that directories exist, otherwise, create them
    pathcheckcreate(scratch_dir)
    pathcheckcreate(out_dir)
    arcpy.env.scratchWorkspace = scratch_dir

    #UPLAND WEIGHT GRID
    nameroot = os.path.splitext(os.path.split(value_grid)[1])[0]
    out_grid = os.path.join(out_dir, '{}_acc'.format(nameroot))
    xpxarea = os.path.join(out_dir, '{}_xpxarea'.format(nameroot))
    xpxarea_ac1 = os.path.join(out_dir, '{}_xpxarea_ac1'.format(nameroot))
    xpxarea_ac_fin = os.path.join(out_dir, '{}_xpxarea_ac_fin'.format(nameroot))

    if (not arcpy.Exists(out_grid)) or (overwrite == True):
        try:
            set_environment(out_dir, direction_grid)

            # Multiply input grid by pixel area
            print('Processing {}...'.format(xpxarea))
            valueXarea = Times(r"" + value_grid, r"" + weight_grid)
            valueXarea.save(xpxarea)

            # Flow accumulation of value grid and pixel area product
            print('Processing {}...'.format(xpxarea_ac1))
            outFlowAccumulation = FlowAccumulation(direction_grid, xpxarea, "FLOAT")
            outFlowAccumulation.save(xpxarea_ac1)

            print('Processing {}...'.format(xpxarea_ac_fin))
            outFlowAccumulation_2 = Plus(xpxarea_ac1, xpxarea)
            outFlowAccumulation_2.save(xpxarea_ac_fin)

            # Divide by the accumulated pixel area grid
            print('Processing {}...'.format(out_grid))
            UplandGrid = Divide(xpxarea_ac_fin, upland_grid)
            UplandGrid.save(out_grid)

        except Exception, e:
            # If an error occurred, print line number and error message
            import traceback, sys
            tb = sys.exc_info()[2]
            arcpy.AddMessage("Line %i" % tb.tb_lineno)
            arcpy.AddMessage(str(e.message))

        print('Deleting intermediate grids...')
        for lyr in [xpxarea, xpxarea_ac1, xpxarea_ac_fin]:
            if arcpy.Exists(lyr):
                arcpy.Delete_management(lyr)
    else:
        print('{} already exists and overwrite==False...'.format(out_grid))

for wc_valuegrid in worldclim_value:
    hydroUplandWeighting(value_grid = wc_valuegrid,
                         direction_grid = directionras,
                         weight_grid = weightras,
                         upland_grid = uplandras,
                         scratch_dir = os.path.join(resdir, 'scratch.gdb'),
                         out_dir = os.path.join(resdir, 'worldclimv2.gdb'))