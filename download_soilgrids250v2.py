from utility_functions import *

#How to make the soil mask? https://github.com/ISRICWorldSoil/SoilGrids250m/blob/1a04d4214c0efabfe15abd621a6c299c173e402c/grids/GlobCover30/soilmask_250m.R

#Create output directory
sg_outdir = os.path.join(datdir, 'SOILGRIDS250')
pathcheckcreate(sg_outdir)

#Parse HTML to get all available layers
sg_https = "https://files.isric.org/soilgrids/latest/data/"
sg_r = urlopen_with_retry(sg_https)
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
    sgdir_r = urlopen_with_retry(dirurl)
    sgdir_soup = BeautifulSoup(sgdir_r, features="html.parser")
    for link in sgdir_soup.findAll('a', attrs={'href': re.compile(".*_mean[/.].*")}):
        sg_lyrdict[dir].append(urlparse.urljoin(dirurl, link.get('href')))

#Get tiling example for a given theme
tilesuffix_pickle = os.path.join(sg_outdir, 'tilsuffixl.pkl')

if not os.path.exists(tilesuffix_pickle):
    sanddir_r = urlopen_with_retry(sg_lyrdict['silt'][2])
    sanddir_soup = BeautifulSoup(sanddir_r, features="html.parser")
    tilesuffixl = list()
    for link in sanddir_soup.findAll('a', attrs={'href': re.compile("tileSG.*")}):
        try:
            print(link)
            bigtiledir = urlparse.urljoin(sg_lyrdict['ocs'][2], link.get('href'))
            bigtiledir_r = urlopen_with_retry(bigtiledir)
            bigtiledir_soup = BeautifulSoup(bigtiledir_r, features="html.parser")
            for smalltile in bigtiledir_soup.findAll('a', attrs={'href': re.compile("tileSG.*")}):
                tilesuffixl.append(urlparse.urljoin(link.get('href'), smalltile.get('href')))
        except:
            traceback.print_exc()
            pass

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
            print(link)
            depthdir = os.path.join(partizedir,
                                    re.sub('[-]', '_',
                                           link.rsplit('/', 2)[1]))
            pathcheckcreate(depthdir)
            for suffix in tilesuffixl:
                tile_url = urlparse.urljoin(link, suffix)
                outlyr = os.path.split(tile_url)[1]
                if not os.path.exists(os.path.join(depthdir, outlyr)):
                    dlfile(url=tile_url, outpath=depthdir, outfile=outlyr, ignore_downloadable=True)
                else:
                    print('{} already exists...'.format(outlyr))

for partsize in ['silt', 'sand', 'clay']:
    partizedir = os.path.join(sg_outdir, partsize)
    pathcheckcreate(partizedir)
    for link in sg_lyrdict[partsize]:
        if not (re.search('.*_mean[/]$', link)):  # If directory of soil property value tiles
            # .vrt or .vrt.ovr files
            depthdir = os.path.join(partizedir,
                                    re.sub('[-]', '_',
                                           os.path.splitext(link.rsplit('/', 2)[-1])[0]))

            pathcheckcreate(depthdir)
            tile_url = link
            outlyr = os.path.split(tile_url)[1]

            if re.search('.*_mean[.]vrt[.]ovr$', link): #ignore .vrt.ovr file
                print('.vrt.ovr file, skipping...')

            else: #.vrt file
                outlyr_full = os.path.join(depthdir, outlyr)
                if not os.path.exists(outlyr_full):
                    vrtrequest = requests.get(tile_url, allow_redirects=True)
                    print('Downloading {}...'.format(os.path.join(outlyr)))
                    with open(outlyr_full, 'wb') as f:
                        f.write(vrtrequest.text)
                else:
                    print('{} already exists...'.format(outlyr))