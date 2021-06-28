from utility_functions import *
from format_HydroSHEDS import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

scratchgdb = os.path.join(resdir, 'scratch.gdb')
pathcheckcreate(scratchgdb)
arcpy.env.scratchWorkspace = scratchgdb

et0_outdir = os.path.join(datdir, 'GAIv2')
et0resgdb = os.path.join(resdir, 'et0.gdb')
pathcheckcreate(et0resgdb)

et0var = {os.path.splitext(os.path.split(lyr)[1])[0]:lyr for lyr in getfilelist(et0_outdir,'(ai_)*et0(_[0-9]{2})*[.]tif$')}

wc_outdir = os.path.join(datdir, 'WorldClimv2')
precdict = {int(re.search('(?<=prec_)[0-9]{1,2}', lyr).group()):lyr for lyr in getfilelist(wc_outdir,'.*prec_[0-9]{1,2}.tif$')}
etdict = {int(re.search('(?<=et0_)[0-9]{1,2}', lyr).group()):lyr for lyr in getfilelist(et0_outdir,'et0_[0-9]{2}[.]tif$')}

#Output paths
cmidict = {"cmi_{}".format(str(mnth).zfill(2)): os.path.join(et0resgdb, 'cmi_{}'.format(str(mnth).zfill(2))) for mnth in xrange(1,13)}

et0var.update(cmidict)
et0_mismask = os.path.join(et0resgdb, 'et0hys_missmask')
et0rsmp = {var:os.path.join(et0resgdb, '{}_resample'.format(var)) for var in et0var}
et0template = et0rsmp['et0_01']
et0nib = {var:os.path.join(et0resgdb, '{}_nibble'.format(var)) for var in et0var}

#Compute CMI
#CMI = (P / PET) - 1 when P < PET] or [CMI = 1 - (PET / P) when P >= PET
for mnth in xrange(1, 13):
    print(mnth)
    if not arcpy.Exists(cmidict["cmi_{}".format(str(mnth).zfill(2))]):
        Int(0.5 + 100 *
            Con(Raster(etdict[mnth]) > Raster(precdict[mnth]),
                (Raster(precdict[mnth]) / Float(Raster(etdict[mnth]))) - 1,
                1 - (Raster(etdict[mnth]) / Float(Raster(precdict[mnth])))
                )
            ).save(cmidict["cmi_{}".format(str(mnth).zfill(2))])

#Resample to match HydroSHEDS land mask using nearest neighbors
hydroresample(in_vardict=et0var, out_vardict=et0rsmp, in_hydrotemplate=hydrotemplate, resampling_type='NEAREST')

#Perform euclidean allocation for all pixels that are NoData in WorldClim layers but have data in HydroSHEDS land mask
hydronibble(in_vardict=et0rsmp, out_vardict=et0nib, in_hydrotemplate=hydrotemplate, nodatavalue=-9999)

#No need to inspect as same mask as WorldClimv2 (see format_WorldClim2)