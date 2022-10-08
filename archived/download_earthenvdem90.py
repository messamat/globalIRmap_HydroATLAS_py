from utility_functions import *

ee_outdir = os.path.join(datdir, 'earthenv')
pathcheckcreate(ee_outdir)

# Parse HTML to get all available layers
ee_https = "https://www.earthenv.org/DEM.html" #Doesn't work, return 403 with urlibb2

# xrange(0, 85, 5) #xrange(0, 60, 5)
ytileset = {'N{}'.format(str(x).zfill(2)) for x in xrange(0, 90, 5)} | \
           {'S{}'.format(str(x).zfill(2)) for x in xrange(0, 60, 5)}
xtileset = {'W{}'.format(str(x).zfill(3)) for x in xrange(0, 185, 5)} | \
           {'E{}'.format(str(x).zfill(3)) for x in xrange(0, 185, 5)}

for x in xtileset:
    for y in ytileset:
        tile = "http://mirrors.iplantcollaborative.org/earthenv_dem_data/EarthEnv-DEM90/" \
               "EarthEnv-DEM90_{0}{1}.tar.gz".format(y, x)
        outtile = os.path.join(ee_outdir, os.path.split(tile)[1])
        try:
            if not (os.path.exists(os.path.splitext(outtile)[0]) or \
                    os.path.exists("{}.bil".format(os.path.splitext(os.path.splitext(outtile)[0])[0]))):
                dlfile(url=tile, outpath=ee_outdir, ignore_downloadable = True, outfile=os.path.split(outtile)[1])
                print('Deleting {}...'.format(outtile))
                os.remove(outtile)
            else:
                print('{} was already processed...'.format(outtile))
        except:
            traceback.print_exc()
        del tile

ee_tarlist = getfilelist(ee_outdir, '.*[.]tar$', gdbf=False, nongdbf=True)
for f in ee_tarlist:
    print(f)
    if not os.path.exists('{}.bil'.format(os.path.splitext(f)[0])):
        with tarfile.open(f) as ftar:
            
            import os
            
            def is_within_directory(directory, target):
                
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
            
                prefix = os.path.commonprefix([abs_directory, abs_target])
                
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
            
                tar.extractall(path, members, numeric_owner=numeric_owner) 
                
            
            safe_extract(ftar, ee_outdir)