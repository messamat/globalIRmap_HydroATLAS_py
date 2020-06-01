from utility_functions import *

hydrolakesdir = os.path.join(datdir, "hydrolakes")
pathcheckcreate(hydrolakesdir)
dlfile(url="https://97dc600d3ccc765f840c-d5a4231de41cd7a15e06ac00b0bcc552.ssl.cf5.rackcdn.com/HydroLAKES_polys_v10.gdb.zip",
       outpath=hydrolakesdir,
       ignore_downloadable=True)