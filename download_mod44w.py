from utility_functions import *

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