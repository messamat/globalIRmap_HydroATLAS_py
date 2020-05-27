#pip install gsutil --ignore-installed six

import os
import arcpy
from arcpy.sa import *
import sys
import re
import subprocess
from utility_functions import *
import json
from cookielib import CookieJar
from urllib import urlencode
import urllib2
from bs4 import BeautifulSoup
import urlparse
import math
import numpy as np
from collections import defaultdict
import tarfile
import lxml
from functools import reduce
import time
from functools import wraps
import cPickle as pickle

def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck, e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print msg
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry

@retry(urllib2.URLError, tries=4, delay=3, backoff=2)
def urlopen_with_retry(in_url):
    return urllib2.urlopen(in_url)

#pip install pyproj==1.9.6 owslib==0.18 - 0.19 dropped python 2.7
#from owslib.wcs import WebCoverageService  # OWSlib module to access WMS services from SDAT

#Folder structure
rootdir = os.path.dirname(os.path.abspath(__file__)).split('\\src')[0]
datdir = os.path.join(rootdir, 'data')
resdir = os.path.join(rootdir, 'results')
glad_dir = os.path.join(datdir, 'GLAD')
pathcheckcreate(glad_dir)

# ------------------------------- Download SoilGrids250 m data -------------------------------------------------------------
#How to make the soil mask? https://github.com/ISRICWorldSoil/SoilGrids250m/blob/1a04d4214c0efabfe15abd621a6c299c173e402c/grids/GlobCover30/soilmask_250m.R

#Create output directory
sg_outdir = os.path.join(datdir, 'SOILGRIDS250')
pathcheckcreate(sg_outdir)

#Parse HTML to get all available layers
sg_https = "https://files.isric.org/soilgrids/data/recent/"
sg_r = urllib2.urlopen(sg_https)
sg_soup = BeautifulSoup(sg_r, features="html.parser")

#Get a list of all directories that contain variables in HTTP server
sg_dirdict = defaultdict(list)
for link in sg_soup.findAll('a', attrs={'href': re.compile("^[a-z]*[/]$")}):
    sg_dirdict[re.search("^[a-zA-Z1-9]+(?=[/])", link.get('href')).group()].append(
        urlparse.urljoin(sg_https, link.get('href')))

#Within each directory, get list of depth mean values dirs, vrt and ovr files
sg_lyrdict = defaultdict(list)
for dir in sg_dirdict:
    print(dir)
    dirurl = sg_dirdict[dir][0]
    sgdir_r = urllib2.urlopen(dirurl)
    sgdir_soup = BeautifulSoup(sgdir_r, features="html.parser")
    for link in sgdir_soup.findAll('a', attrs={'href': re.compile(".*_mean[/.].*")}):
        sg_lyrdict[dir].append(urlparse.urljoin(dirurl, link.get('href')))

#Get tiling example for a given theme
tilesuffix_pickle = os.path.join(sg_outdir, 'tilsuffixl.pkl')

if not os.path.exists(tilesuffix_pickle):
    sanddir_r = urllib2.urlopen(sg_lyrdict['sand'][2])
    sanddir_soup = BeautifulSoup(sanddir_r, features="html.parser")
    tilesuffixl = list()
    for link in sanddir_soup.findAll('a', attrs={'href': re.compile("tileSG.*")}):
        print(link)
        bigtiledir = urlparse.urljoin(sg_lyrdict['ocs'][2], link.get('href'))
        bigtiledir_r = urlopen_with_retry(bigtiledir)
        bigtiledir_soup = BeautifulSoup(bigtiledir_r, features="html.parser")
        for smalltile in bigtiledir_soup.findAll('a', attrs={'href': re.compile("tileSG.*")}):
            tilesuffixl.append(urlparse.urljoin(link.get('href'), smalltile.get('href')))

    #Pickle the suffix list
    with open(tilesuffix_pickle, "wb") as f:
        pickle.dump(tilesuffixl,f)

else:
    with open(tilesuffix_pickle, 'rb') as f:
        tilesuffixl = pickle.load(f)

#Download tile for each particle size of interest
for partsize in ['silt', 'sand', 'clay']:
    partizedir = os.path.join(sg_outdir, partsize)
    pathcheckcreate(partizedir)
    for link in sg_lyrdict[partsize]:
        if re.search('.*_mean[/]$', link): #If directory of soil property value tiles
            depthdir = os.path.join(partizedir,
                                    re.sub('[-]', '_',
                                           link.rsplit('/', 2)[1]))
            pathcheckcreate(depthdir)
            for suffix in tilesuffixl:
                tile_url = urlparse.urljoin(link, suffix)
                outlyr = os.path.split(tile_url)[1]
                if not os.path.exists(os.path.join(depthdir, outlyr)):
                    dlfile(url=tile_url, outpath=depthdir, outfile=outlyr, ignore_downloadable=True)

        else:# .vrt or .vrt.ovr files
            depthdir = os.path.join(partizedir,
                                    re.sub('[-]', '_',
                                           os.path.splitext(link.rsplit('/', 2)[-1])[0]))
            pathcheckcreate(depthdir)
            tile_url = link
            outlyr = os.path.split(tile_url)[1]

            if re.search('.*_mean[.]vrt[.]ovr$', link): #.vrt.ovr file
                dlfile(url=tile_url, outpath=depthdir, outfile=outlyr, ignore_downloadable=True)

            else: #.vrt file
                vrtrequest = requests.get(tile_url, allow_redirects=True)
                print('Downloading {}...'.os.path.join(outlyr))
                with open(os.path.join(depthdir, outlyr), 'wb') as f:
                    f.write(vrtrequest.text)












#Download all layers of interest
#for lyrk in sg_lyrdict.keys():
lyrk = "SLGWRB"
if lyrk not in ["TAXNWRB", "TAXOUSDA"]:
    outdir = os.path.join(sg_outdir, lyrk)
    pathcheckcreate(outdir)

    for lyrurl in sg_lyrdict[lyrk]:
        print(lyrurl)
        #dlfile(url=lyrurl, outpath=outdir, outfile=os.path.split(lyrurl)[1], fieldnames=None)

# ----------------------------- Download ESA water bodies Ocean vs Inland vs Land --------------------------------------

# ----------------------------- Download 2015 ESA Land Cover data to match SoilGrids250 --------------------------------
#http://maps.elie.ucl.ac.be/CCI/viewer/download.php



# ----------------------------- Download ALOS DEM data ----------------------------------------------------------------------
#Main page https://www.eorc.jaxa.jp/ALOS/en/aw3d30/
alos_outdir = os.path.join(datdir, 'ALOS2')
pathcheckcreate(alos_outdir)

# Import user credentials that will be used to authenticate access to the data
with open("configs.json") as json_data_file:  # https://martin-thoma.com/configuration-files-in-python/
    authdat = json.load(json_data_file)

#Get list of tiles
# Create a password manager to deal with the 401 reponse that is returned from Earthdata Login
password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
password_manager.add_password(None,
                              "https://www.eorc.jaxa.jp",
                              authdat['alos']['username'],
                              authdat['alos']['password'])

# Create a cookie jar for storing cookies. This is used to store and return the session cookie given to use by
# the data server (otherwise it will just keep sending us back to Earthdata Login to authenticate).
# Ideally, we should use a file based cookie jar to preserve cookies between runs. This will make it much more efficient.
cookie_jar = CookieJar()

# Install all the handlers.
opener = urllib2.build_opener(
    urllib2.HTTPBasicAuthHandler(password_manager),
    # urllib2.HTTPHandler(debuglevel=1),    # Uncomment these two lines to see
    # urllib2.HTTPSHandler(debuglevel=1),   # details of the requests/responses
    urllib2.HTTPCookieProcessor(cookie_jar))
urllib2.install_opener(opener)

alos_map = urllib2.urlopen("https://www.eorc.jaxa.jp/ALOS/en/aw3d30/data/index.htm")
alos_soup = BeautifulSoup(alos_map, features="html.parser")
errorlinks = []
for link in alos_soup.findAll('area', attrs={'title': re.compile("[NS][0-9]{3}[WE][0-9]{3}_[NS][0-9]{3}[WE][0-9]{3}")}):
    bigtile = urlparse.urljoin("https://www.eorc.jaxa.jp/ALOS/en/aw3d30/data/", link.get('href'))
    print(bigtile)
    bigtile_soup = BeautifulSoup(urllib2.urlopen(bigtile).read(), features="html.parser")

    #Check for high latitue tiles
    mediumtiles_urls = {}
    for link2 in bigtile_soup.findAll('img', attrs={'onclick': re.compile("comp_anterctica.*")}):
        mediumids = re.sub("[']",
                           "",
                           re.search("(?<=comp_anterctica[(]['])[NS][0-9]{3}[WE][0-9]{3}"
                                     "['][,][']"
                                     "[NS][0-9]{3}[WE][0-9]{3}",
                                     link2.get('onclick')).group()
                           ).split(",")

        mediumtiles_urls['{0}_{1}'.format(mediumids[0], mediumids[1])] =\
            "https://www.eorc.jaxa.jp/ALOS/aw3d30/data/release_v2003/{0}_{1}.tar.gz".format(
                mediumids[0], mediumids[1])

    for link2 in bigtile_soup.findAll('img', attrs={'onclick': re.compile("comp\(.*")}):
        #print(link2)
        mediumids = re.sub("[']",
                           "",
                           re.search("(?<=comp[(]['])[NS][0-9]{3}[WE][0-9]{3}"
                                     "['][,][']"
                                     "[NS][0-9]{3}[WE]{1,2}[0-9]{3}",
                                     link2.get('onclick')).group()
                           ).split(",")
        #Correct one glitch
        if mediumids[1] == 'N035EW010':
            print('Corrrecting N035EW10 to N035W010...')
            mediumids[1] = 'N035W010'

        mediumtiles_urls['{0}_{1}'.format(mediumids[0], mediumids[1])] = \
            "https://www.eorc.jaxa.jp/ALOS/aw3d30/data/release_v2003/{0}_{1}.zip".format(
                mediumids[0], mediumids[1])

    for alos_tileurl in mediumtiles_urls.values():
        alos_outtile = os.path.join(alos_outdir, os.path.split(alos_tileurl)[1])

        try:
            if not (os.path.exists(alos_outtile) or
                    os.path.exists(os.path.splitext(alos_outtile)[0])):
                dlfile(url=alos_tileurl,
                       outpath=os.path.split(alos_outtile)[0],
                       outfile=os.path.split(alos_outtile)[1],
                       fieldnames=None,
                       ignore_downloadable=False,
                       loginprompter="https://www.eorc.jaxa.jp",
                       username=authdat['alos']['username'], password=authdat['alos']['password'])
            else:
                print('{} was already processed...'.format(alos_outtile))
        except:
            errorlinks.append(alos_tileurl)
            traceback.print_exc()

for e in errorlinks:
    print(e)

errorlink_correct = [
    "N025W015_N030W010.zip",
    "N030W010_N035W005.zip",
    "N025W020_N030W015.zip",
    "N045W130_N050W125.zip",
    "N045W125_N050W120.zip",
    "N040W125_N045W120.zip",
    "N030W125_N035W120.zip",
    "N065E005_N065E010",
    "N045W090_N050W085","N045W085_N050W080","N045W080_N050W075","N045W075_N050W070",
    "N045W070_N050W065","N045W065_N050W060","N040W090_N045W085","N040W085_N045W080",
    "N040W080_N045W075","N040W075_N045W070","N040W070_N045W065","N040W065_N045W060",
    "N035W090_N040W085","N035W085_N040W080","N035W080_N040W075","N035W075_N040W070",
    "N030W090_N035W085","N030W085_N035W080","N030W080_N035W075","N030W065_N035W060",
    "N025W090_N030W085","N025W085_N030W080","N025W080_N030W075","N020W090_N025W085",
    "N020W085_N025W080","N020W080_N025W075","N020W075_N025W070",
    "N015W170_N020W165","N015W160_N020W155","N015W155_N020W150","N005W165_N010W160",
    "N000W180_N005W175","N000W165_N005W160","N000W160_N005W155","S005W175_N000W170",
    "S005W165_N000W160","S005W160_N000W155","S005W155_N000W150","S010W175_S005W170",
    "S010W165_S005W160","S010W160_S005W155","S010W155_S005W150",
    "S055E000_S050E005","S070E015_S065E020","S070E025_S065E030",
    "S045W080_S040W075","S045W075_S040W070","S045W070_S040W065","S045W065_S040W060",
    "S050W080_S045W075","S050W075_S045W070","S050W070_S045W065","S055W080_S050W075",
    "S055W075_S050W070","S055W070_S050W065","S055W065_S050W060","S060W075_S055W070",
    "S060W070_S055W065","S065W065_S060W060","S070W080_S065W075","S070W075_S065W070",
    "S070W070_S065W065","S070W065_S065W060",
]

errorlink_correct_gz = ["https://www.eorc.jaxa.jp/ALOS/aw3d30/data/release_v2003/{}.tar.gz".format(i) for i in errorlink_correct]
errorlink_correct_zip = ["https://www.eorc.jaxa.jp/ALOS/aw3d30/data/release_v2003/{}.zip".format(i) for i in errorlink_correct]


for alos_tileurl in errorlink_correct_gz + errorlink_correct_zip:
    alos_outtile = os.path.join(alos_outdir, os.path.split(alos_tileurl)[1])

    try:
        if not (os.path.exists(alos_outtile) or
                os.path.exists(os.path.splitext(alos_outtile)[0])):
            dlfile(url=alos_tileurl,
                   outpath=os.path.split(alos_outtile)[0],
                   outfile=os.path.split(alos_outtile)[1],
                   fieldnames=None,
                   ignore_downloadable=False,
                   loginprompter="https://www.eorc.jaxa.jp",
                   username=authdat['alos']['username'], password=authdat['alos']['password'])
        else:
            print('{} was already processed...'.format(alos_outtile))
    except:
        print(alos_tileurl)
        traceback.print_exc()

# ------------------------------- Download EarthEnv-DEM90 data -------------------------------------------------------------
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
            ftar.extractall(ee_outdir)  # specify which folder to extract to

#-------------------------------- Download GlobeLand30 -----------------------------------------------------------------

#"https://web.archive.org/web/20170710051151/http://globallandcover.com:80/user/ReturnPassword.aspx" Try and retrieve password?
#Try WMS service e.g. https://gis.stackexchange.com/questions/283900/getting-wms-server-from-globeland30-landcover-interactive-map
#http://218.244.250.80:8080/erdas-apollo/coverage/CGLC?LAYERS=cglc30_2010_0&TRANSPARENT=TRUE&FORMAT=image%2Fpng&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&SRS=EPSG%3A900913&BBOX=-176110.91314453,6124746.201582,-156543.03390625,6144314.0808203&WIDTH=256&HEIGHT=256
#http://218.244.250.80:8080/erdas-apollo/coverage/CGLC?service=wms&request=getCapabilities

#------------------------------- Download MODIS 250 m land and water mask to enhance SoilGrids -------------------------
# Create output directory
mod44w_outdir = os.path.join(datdir, 'mod44w')
pathcheckcreate(mod44w_outdir)

# Download metadata
dlfile(url='https://lpdaac.usgs.gov/documents/109/MOD44W_User_Guide_ATBD_V6.pdf', outpath=mod44w_outdir)

# Parse HTML to get all available layers
mod44w_https = "https://e4ftl01.cr.usgs.gov/MOLT/MOD44W.006/2015.01.01/"
mod44w_r = urllib2.urlopen(mod44w_https)
mod44w_soup = BeautifulSoup(mod44w_r, features="html.parser")

# The user credentials that will be used to authenticate access to the data
with open("configs.json") as json_data_file:  # https://martin-thoma.com/configuration-files-in-python/
    authdat = json.load(json_data_file)

# Download all layers of interest
for lyrurl in [urlparse.urljoin(mod44w_https, link.get('href')) for link in
               mod44w_soup.findAll('a', attrs={'href': re.compile("MOD44W.*[.]hdf([.]xml)*")})]:

        dlfile(url=lyrurl, outpath=mod44w_outdir, outfile=os.path.split(lyrurl)[1], fieldnames=None,
               loginprompter="https://urs.earthdata.nasa.gov",
               username=authdat['earthdata']['username'], password=authdat['earthdata']['password'])

#Convert HDF tiles to TIF and project them using

#------------------------------- Download HydroLAKES -------------------------------------------------------------------
hydrolakesdir = os.path.join(datdir, "hydrolakes")
pathcheckcreate(hydrolakesdir)
dlfile(url="https://97dc600d3ccc765f840c-d5a4231de41cd7a15e06ac00b0bcc552.ssl.cf5.rackcdn.com/HydroLAKES_polys_v10.gdb.zip",
       outpath=hydrolakesdir,
       ignore_downloadable=True)

#------------------------------- Download GLIMS ------------------------------------------------------------------------
# Create output directory
glims_outdir = os.path.join(datdir, 'glims')
pathcheckcreate(glims_outdir)

outglims = os.path.join(glims_outdir, 'glims.zip')
f= requests.get("http://www.glims.org/download/latest", allow_redirects=True) #no extension and content-type is plain text, tough to parse
try:  # Try writing to local file
    with open(outglims, "wb") as local_file:
        local_file.write(f.raw.read())
    # Unzip downloaded file
    try:
        unzip(outglims + '.zip')
    except:
        z = zipfile.ZipFile(io.BytesIO(f.content))
        if isinstance(z, zipfile.ZipFile):
            z.extractall(os.path.split(outglims)[0])
except:
    traceback.print_exc()

#------------------------------- Download HYSOGS250 m data -------------------------------------------------------------
hysogdir = os.path.join(datdir, 'hysog')
pathcheckcreate(hysogdir)
hysogresgdb = os.path.join(resdir, 'hysog.gdb')
pathcheckcreate(hysogresgdb)
hysogmosaic = os.path.join(hysogresgdb, 'hysog_mosaic')

#DOI of dataset is https://doi.org/10.3334/ORNLDAAC/1566
#This last number is the dataset ID to be used for search in WebMapService
sdatwcs = WebCoverageService('https://webmap.ornl.gov/ogcbroker/wcs')
print(str(len(sdatwcs.contents)) + ' layers found from ' + sdatwcs.identification.title)
# filter layers
hysog_wcsid = filter(lambda x: x.startswith('1566_'), sdatwcs.contents)[0]
print(hysog_wcsid)

hysogbblist = divbb(bbox=sdatwcs[hysog_wcsid].boundingBoxWGS84,
                    res=sdatwcs[hysog_wcsid].grid.offsetvectors[0][0],
                    divratio=10)
hysogoutlist = ['{0}_{1}.tif'.format(os.path.join(hysogdir, 'hysog'), i)
                for i in xrange(0, len(hysogbblist))]
if not all([os.path.isfile(i) for i in hysogoutlist]):
    x=0
    for bb in hysogbblist:
        #print(bb)
        outtile = hysogoutlist[x]
        if not os.path.isfile(outtile):
            print(outtile)
            hysog_wc = sdatwcs.getCoverage(identifier=hysog_wcsid,
                                           bbox=bb,
                                           crs='EPSG:4326',
                                           format='Geotiff_BYTE',
                                           interpolation='NEAREST',
                                           resx=sdatwcs[hysog_wcsid].grid.offsetvectors[0][0],
                                           resy=sdatwcs[hysog_wcsid].grid.offsetvectors[0][0])

            with open(outtile, "wb") as local_file:
                local_file.write(hysog_wc.read())
        else:
            print("{} already exists...".format(outtile))

        x+=1

# #Only keep tiles with data - only works with numpy > 1.9.3 but breaks arcpy
# for tilepath in hysogoutlist:
#     print(tilepath)
#     tiledat = gdal_array.LoadFile(tilepath)
#     if tiledat.max() == 0:
#         hysogoutlist.remove(tilepath)

#mosaic them
print('Mosaicking hysogs tiles...')
arcpy.MosaicToNewRaster_management(hysogoutlist, output_location=hysogresgdb,
                                   raster_dataset_name_with_extension= 'hysog_mosaic',
                                   pixel_type= '8_BIT_UNSIGNED',
                                   number_of_bands = 1,
                                   mosaic_colormap_mode = 'FIRST')


# ----------------------------- Download GLAD data ----------------------------------------------------------------------
glad_dtype = "class99_19.tif"
gsutil_ls_cmd = "gsutil ls gs://earthenginepartners-hansen/water/*/{}".format(glad_dtype)
glad_cloudout = subprocess.check_output(gsutil_ls_cmd)
glad_cloudlist = glad_cloudout.split('\n')

for tile in glad_cloudlist:
    out_tilen = os.path.join(glad_dir, '{0}_{1}.tif'.format(
        os.path.splitext(glad_dtype)[0], tileroot))
    if not os.path.isfile(out_tilen):
        print(tile)
        tileroot = os.path.split(os.path.split(tile)[0])[1]
        gsutil_cp_cmd = "gsutil cp {0} {1}".format(tile, glad_dir)
        subprocess.check_output(gsutil_cp_cmd)
        os.rename(os.path.join(glad_dir, glad_dtype), out_tilen)




