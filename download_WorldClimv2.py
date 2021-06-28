'''Purpose: download WorldClim version 2'''
from utility_functions import *

#Create output directory
wc_outdir = os.path.join(datdir, 'WorldClimv2')
pathcheckcreate(wc_outdir)

#Download historical data
wc_histurl = "https://www.worldclim.org/data/worldclim21.html"
wc_histr = urlopen_with_retry(wc_histurl)
wc_histsoup = BeautifulSoup(wc_histr, features="html.parser")

#Get a list of all directories that contain variables in the HTTP server
wc_histdict = {}
for link in wc_histsoup.findAll('a', attrs={'href': re.compile(
        "https*[:][/][/]biogeo[.]ucdavis[.]edu[/]data[/]worldclim[/]v2.1[/]base[/]wc2[.]1_30s_.*[.]zip$")}):
    #print(link)
    wc_histdict[re.search("[a-z]{3,4}(?=[.]zip$)", link.get('href')).group()]= link.get('href')

for lyr in wc_histdict:
    if lyr !='elev':
        print('Downloading {}'.format(wc_histdict[lyr]))
        dlfile(wc_histdict[lyr], outpath=wc_outdir,outfile="{}.zip".format(lyr), ignore_downloadable=True)