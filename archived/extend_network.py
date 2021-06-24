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
if not arcpy.Exists(sline_b05):
    arcpy.SpatialJoin_analysis(target_features=sline, join_features=basinatlasl05,
                               out_feature_class=sline_b05, join_operation="JOIN_ONE_TO_ONE",
                               join_type = 'KEEP_ALL', match_option="HAVE_THEIR_CENTER_IN")

#Get length
if ('LENGTH_GEO' not in [f.name for f in arcpy.ListFields(sline_b05)]):
    arcpy.AddGeometryAttributes_management(sline_b05, Geometry_Properties='LENGTH_GEODESIC', Length_Unit='kilometers')

# ---------- Flag reaches within lakes ------
sline_lakejoin = os.path.join(extend_resdir, 'streamseg_hydrolakes_join')
if not arcpy.Exists(sline_lakejoin):
    arcpy.SpatialJoin_analysis(target_features=sline_b05, join_features=hydrolakes,
                               out_feature_class=sline_lakejoin, join_operation="JOIN_ONE_TO_ONE",
                               join_type = 'KEEP_ALL', match_option="COMPLETELY_WITHIN")

# ---------- Get reach discharge ------
spourpoint = os.path.join(extend_resdir, 'ppourpoints_o1skm')
if not arcpy.Exists(spourpoint):
    arcpy.FeatureVerticesToPoints_management(sline_lakejoin, spourpoint, 'END')
    ExtractMultiValuesToPoints(in_point_features=spourpoint, in_rasters=disras, bilinear_interpolate_values='NONE')

if ('dis_m3_pyr' in [f.name for f in arcpy.ListFields(sline_b05)]):
    arcpy.DeleteField_management(sline_lakejoin, 'dis_m3_pyr')
    arcpy.AddField_management(sline_lakejoin, 'dis_m3_pyr', 'DOUBLE')
    disdict = {row[0]:row[1] for row in arcpy.da.SearchCursor(spourpoint, ['arcid', 'dis_m3_pyr'])}

    with arcpy.da.UpdateCursor(sline_lakejoin, ['arcid', 'dis_m3_pyr']) as cursor:
        for row in cursor:
            row[1] = disdict[row[0]]
            cursor.updateRow(row)

# ---------- Export to CSV table ------


sline_tab = os.path.join(rootdir, 'results//streamseg_o1skm.csv')
arcpy.CopyRows_management(sline_lakejoin, sline_tab)

#Move to R
#Compute average intermittency for smallest class
#Sum it all up