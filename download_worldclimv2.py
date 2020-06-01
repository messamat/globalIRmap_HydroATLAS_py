from utility_functions import *

wcdir = os.path.join(datdir, 'worlclimv2')
pathcheckcreate(wcdir)

#Historical climate data
wc_historical = urllib2.urlopen("https://www.worldclim.org/data/worldclim21.html")
wc_soup = BeautifulSoup(wc_historical, features="html.parser")

errorlinks = []
for link in alos_soup.findAll('area', attrs={'title': re.compile("[NS][0-9]{3}[WE][0-9]{3}_[NS][0-9]{3}[WE][0-9]{3}")}):
"http://biogeo.ucdavis.edu/data/worldclim/v2.1/base/wc2.1_30s_tmin.zip"
#Historical monthly weather data
"https://www.worldclim.org/data/monthlywth.html"

