from utility_functions import *

GAIv2dir = os.path.join(datdir, 'GAIv2')
pathcheckcreate(GAIv2dir)

#https://figshare.com/articles/Global_Aridity_Index_and_Potential_Evapotranspiration_ET0_Climate_Database_v2/7504448/3
dlfile(url = "https://ndownloader.figshare.com/files/14118800",
       outpath = GAIv2dir,
       outfile = 'GAIv2.zip',
       ignore_downloadable=True)