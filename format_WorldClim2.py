from utility_functions import *
from format_HydroSHEDS import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

# BIO1 = Annual Mean Temperature
# BIO2 = Mean Diurnal Range (Mean of monthly (max temp - min temp))
# BIO3 = Isothermality (BIO2/BIO7) (×100)
# BIO4 = Temperature Seasonality (standard deviation ×100)
# BIO5 = Max Temperature of Warmest Month
# BIO6 = Min Temperature of Coldest Month
# BIO7 = Temperature Annual Range (BIO5-BIO6)
# BIO8 = Mean Temperature of Wettest Quarter
# BIO9 = Mean Temperature of Driest Quarter
# BIO10 = Mean Temperature of Warmest Quarter
# BIO11 = Mean Temperature of Coldest Quarter
# BIO12 = Annual Precipitation
# BIO13 = Precipitation of Wettest Month
# BIO14 = Precipitation of Driest Month
# BIO15 = Precipitation Seasonality (Coefficient of Variation)
# BIO16 = Precipitation of Wettest Quarter
# BIO17 = Precipitation of Driest Quarter
# BIO18 = Precipitation of Warmest Quarter
# BIO19 = Precipitation of Coldest Quarter

wc_outdir = os.path.join(datdir, 'WorldClimv2')
wcresgdb = os.path.join(resdir, 'worldclimv2.gdb')
pathcheckcreate(wcresgdb)

climvar = {re.search('(bio|prec)_[0-9]{1,2}', lyr).group():lyr for lyr in getfilelist(wc_outdir,'.*(bio|prec)_[0-9]{1,2}.tif$')}

#Output paths
wc_mismask = os.path.join(wcresgdb, 'wchys_missmask')
wc_mismask_inspect = os.path.join(wcresgdb,'wchys_missmask_inspect')
climrsmp = {var:os.path.join(wcresgdb, '{}_resample'.format(var)) for var in climvar}
wctemplate = climrsmp['bio_1']
climnib = {var:os.path.join(wcresgdb, '{}_nibble'.format(var)) for var in climvar}

########################################## analysis ####################################################################
#Resample to match HydroSHEDS land mask using nearest neighbors
hydroresample(in_vardict=climvar, out_vardict=climrsmp, in_hydrotemplate=hydrotemplate, resampling_type='NEAREST')

#Perform euclidean allocation for all pixels that are NoData in WorldClim layers but have data in HydroSHEDS land mask
hydronibble(in_vardict=climrsmp, out_vardict=climnib, in_hydrotemplate=hydrotemplate, nodatavalue=-9999)

########################################## correct glitch in bio6 ######################################################
Con(IsNull(Raster(climnib['bio_6'])), 0, Raster(climnib['bio_6'])).save('{}2'.format(climnib['bio_6']))
arcpy.Delete_management(climnib['bio_6'])
arcpy.Rename_management(in_data='{}2'.format(climnib['bio_6']), out_data=climnib['bio_6'])

#Inspect regions for which cell count hydroregions = wc_mismaskand > 10
#Create a mismatch raster using hydrosheds land mask regions
Con((IsNull(wctemplate)) & (~IsNull(hydrotemplate)), hydroregions).save(wc_mismask)

if not arcpy.Exists():
    arcpy.MakeTableView_management(hydroregions, 'fullregiontab')
    arcpy.AddJoin_management('fullregiontab', in_field='Value', join_table=wc_mismask, join_field='Value')
    regionsql= "(VAT_{0}.Count = VAT_{1}.Count) AND (VAT_{1}.Count > 10)".format(
        os.path.split(hydroregions)[1], os.path.split(wc_mismask)[1])
    arcpy.SelectLayerByAttribute_management('fullregiontab', selection_type='NEW_SELECTION', where_clause= regionsql)
    inspectl = [row[0] for row in
                arcpy.da.SearchCursor('fullregiontab', 'VAT_{0}.Value'.format(os.path.split(hydroregions)[1]))]

    arcpy.MakeFeatureLayer_management(hydroregions_poly, 'polyreg')
    arcpy.SelectLayerByAttribute_management('polyreg', selection_type='NEW_SELECTION',
                                            where_clause= 'gridcode IN {}'.format(str(tuple(inspectl))))
    arcpy.CopyFeatures_management('polyreg', wc_mismask_inspect)