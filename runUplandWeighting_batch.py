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

def hydroUplandWeighting(value_grid, direction_grid, weight_grid, upland_grid, scratch_dir,
                        out_dir, shiftval=0, overwrite=False):
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
            valueXarea = Times(Raster(value_grid) + float(shiftval), Raster(weight_grid))
            valueXarea.save(xpxarea)

            # Flow accumulation of value grid and pixel area product
            print('Processing {}...'.format(xpxarea_ac1))
            outFlowAccumulation = FlowAccumulation(direction_grid, Raster(xpxarea), "FLOAT")
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


############################ Worlclim v2 ###############################################################################
#Value grids
worldclim_value = getfilelist(os.path.join(resdir, 'worldclimv2.gdb'), '.*nibble$')

for wc_valuegrid in worldclim_value:
    hydroUplandWeighting(value_grid = wc_valuegrid,
                         direction_grid = directionras,
                         weight_grid = weightras,
                         upland_grid = uplandras,
                         scratch_dir = os.path.join(resdir, 'scratch.gdb'),
                         out_dir = os.path.join(resdir, 'worldclimv2.gdb'))


############################ Global Aridity Index and CMI v2 ###########################################################
et0_outdir = os.path.join(datdir, 'GAIv2')
et0resgdb = os.path.join(resdir, 'et0.gdb')
et0var = {os.path.splitext(os.path.split(lyr)[1])[0]:lyr for lyr in getfilelist(et0_outdir,'(ai_)*et0(_[0-9]{2})*[.]tif$')}
cmidict = {"cmi_{}".format(str(mnth).zfill(2)): os.path.join(et0resgdb, 'cmi_{}'.format(str(mnth).zfill(2))) for mnth in xrange(1,13)}
et0var.update(cmidict)
et0nib = {var:os.path.join(et0resgdb, '{}_nibble2'.format(var)) for var in et0var}

for etcmi_valuegrid in cmidict:
    hydroUplandWeighting(value_grid = etcmi_valuegrid,
                         direction_grid = directionras,
                         weight_grid = weightras,
                         upland_grid = uplandras,
                         scratch_dir = os.path.join(resdir, 'scratch.gdb'),
                         out_dir = et0resgdb,
                         shiftval = 100)


############################ SoilGrids250m v2 ##########################################################################
sgresgdb = os.path.join(resdir, 'soilgrids250.gdb')
sgdict = getfilelist(sgresgdb, '.*_wmeanagg2$')

for sg_valuegrid in sgdict:
    hydroUplandWeighting(value_grid = sg_valuegrid,
                         direction_grid = directionras,
                         weight_grid = weightras,
                         upland_grid = uplandras,
                         scratch_dir = os.path.join(resdir, 'scratch.gdb'),
                         out_dir = sgresgdb)