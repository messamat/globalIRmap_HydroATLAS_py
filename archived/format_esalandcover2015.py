from utility_functions import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

outdir = os.path.join(datdir, 'ESA_LCC')
resgdb = os.path.join(resdir, 'esa_lcc.gdb')
pathcheckcreate(resgdb)

lccraw = os.path.join(outdir, 'product', "ESACCI-LC-L4-LCCS-Map-300m-P1Y-2015-v2.0.7.tif")
oceanmask = os.path.join(outdir, "ESACCI-LC-L4-WB-Ocean-Land-Map-150m-P13Y-2000-v4.0.tif")