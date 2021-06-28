'''download the Advanced Land Observing Satellite (ALOS)
global digital elevation model (this can take days and requires hundreds of GB)'''
from utility_functions import *

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
