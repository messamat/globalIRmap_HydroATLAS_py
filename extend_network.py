from utility_functions import *

#Download ArcHYDRO
#https://downloads.esri.com/archydro/archydro/Setup/10.7/10.7.0.78/
import ArcHydroTools #Need to be downloaded and installed

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Folder structure
hydrodir = os.path.join(datdir, 'Bernhard', 'HydroATLAS')
geomdir = os.path.join(hydrodir, 'HydroATLAS_Geometry')

#Input layers
directionras = os.path.join(geomdir, 'Flow_directions', 'flow_dir_15s_global.gdb', 'flow_dir_15s')
weightras = os.path.join(geomdir,'Accu_area_grids', 'pixel_area_skm_15s.gdb', 'px_area_skm_15s')
uplandras = os.path.join(geomdir, 'Accu_area_grids', 'upstream_area_skm_15s.gdb', 'up_area_skm_15s')
disras = os.path.join(hydrodir,  "HydroATLAS_Data", "Hydrology", "discharge_wg22_1971_2000.gdb", "dis_nat_wg22_ls_year")
basinatlasl05 = os.path.join(hydrodir, 'HydroATLAS_v10_final_data', 'BasinATLAS_v10.gdb', 'BasinATLAS_v10_lev05')
hydrolakes = os.path.join(datdir, 'hydrolakes', 'HydroLAKES_polys_v10.gdb', 'HydroLAKES_polys_v10')

#Output layers
extend_resdir = os.path.join(resdir, 'extend_net.gdb')
pathcheckcreate(extend_resdir)

#Delineate streams
sras = os.path.join(extend_resdir, "streamras_o1skm")
if not arcpy.Exists(sras):
    streamras = Con(Raster(uplandras) >= 1, 1)
    streamras.save(sras)

#Generate streams polyline
sline = os.path.join(extend_resdir, "streamseg_o1skm")
if not arcpy.Exists(sline):
    StreamToFeature(sras, directionras, sline, simplify='NO_SIMPLIFY')

# ---------- Associate reaches with HydroBASIN level 06 ------
sline_b05 = os.path.join(extend_resdir, 'streamseg_o1skm_b05')
arcpy.SpatialJoin_analysis(target_features=sline, join_features=basinatlasl05,
                           out_feature_class=sline_b05, join_operation="JOIN_ONE_TO_ONE",
                           join_type = 'KEEP_ALL', match_option="HAVE_THEIR_CENTER_IN")

#Get length
arcpy.AddGeometryAttributes_management(sline_b05, Geometry_Properties='LENGTH_GEODESIC', Length_Unit='kilometers')

# ---------- Flag reaches within lakes ------
sline_lakeinters = os.path.join(extend_resdir, 'streamseg_hydrolakes_inters')
if not arcpy.Exists(sline_lakeinters):
    arcpy.Intersect_analysis(in_features = [sline_b05, hydrolakes], out_feature_class=sline_lakeinters,
                             join_attributes= 'ONLY_FID')
    arcpy.AddGeometryAttributes_management(sline_lakeinters, Geometry_Properties='LENGTH_GEODESIC', Length_Unit='kilometers')

if not 'INLAKEPERC' in [f.name for f in arcpy.ListFields(sline_b05)]:
    arcpy.AddField_management(sline_b05, 'INLAKEPERC', field_type='float')
    lendict = defaultdict(float)
    with arcpy.da.SearchCursor(sline_lakeinters, ['HYRIV_ID', 'LENGTH_GEO']) as cursor:
        for row in cursor:
            lendict[row[0]] += row[1]
    with arcpy.da.UpdateCursor(sline_b05, ['HYRIV_ID', 'LENGTH_KM','INLAKEPERC']) as cursor:
        for row in cursor:
            if row[0] in lendict:
                row[2] = lendict[row[0]]/row[1]
                cursor.updateRow(row)

# ---------- Export to CSV table ------
sline_lakeinters = os.path.join(rootdir, 'results//streamseg_o1skm.csv')
arcpy.CopyRows_management(sline_b05, sline_lakeinters)

#Move to R
#Compute average intermittency for smallest class
#Sum it all up