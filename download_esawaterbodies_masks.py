from utility_functions import *

esalccdir = os.path.join(datdir, "ESA_LCC")
pathcheckcreate(esalccdir)
dlfile(url="https://storage.googleapis.com/cci-lc-v207/ESACCI-LC-L4-LCCS-Map-300m-P1Y-2015-v2.0.7.zip",
       outpath=esalccdir,
       ignore_downloadable=True)