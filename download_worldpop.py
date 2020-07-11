from utility_functions import *

wp_outdir = os.path.join(datdir, 'worldpop')
pathcheckcreate(wp_outdir)

url="ftp://ftp.worldpop.org.uk/GIS/Population/Global_2000_2020/2020/0_Mosaicked/ppp_2020_1km_Aggregated.tif"
outfile=os.path.join(wp_outdir, os.path.split(url)[1])
urlp = urlparse.urlparse(os.path.split(url)[0])
ftp = ftplib.FTP(urlp.netloc)
ftp.login()
ftp.cwd(urlp.path)

if not os.path.exists(outfile):
    # Download it
    with open(outfile, 'wb') as fobj:  # using 'w' as mode argument will create invalid zip files
        ftp.retrbinary('RETR {}'.format(os.path.split(outfile)[1]), fobj.write)