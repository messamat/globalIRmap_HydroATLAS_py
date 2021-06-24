"""Developer: Mathis L. Messager
Purpose:
 - import key modules
 - define utility functions used throughout the analysis
 - define the basic folder structure of the analysis
"""

#pip install gsutil --ignore-installed six
#pip install pyproj==1.9.6 owslib==0.18 - 0.19 dropped python 2.7
#from owslib.wcs import WebCoverageService  # OWSlib module to access WMS services from SDAT

import arcpy
from arcpy.sa import *
from bs4 import BeautifulSoup
from collections import defaultdict
from cookielib import CookieJar
import cPickle as pickle
import csv
import ftplib
from functools import wraps
from functools import reduce
import gzip
import io
import itertools
import json
import math
import numpy as np
import os
import pandas as pd
import random
import re
import requests
import shutil
import subprocess
import sys
import tarfile
import time
import traceback
from urllib import urlencode
import urllib2
import urlparse
import zipfile

#Folder structure
rootdir = os.path.dirname(os.path.abspath(__file__)).split('\\src')[0]
datdir = os.path.join(rootdir, 'data')
resdir = os.path.join(rootdir, 'results')

# Resample a dictionary of rasters (in_vardict) to the resolution of a template raster (in_hydrotemplate), outputting
# the resampled rasters to paths contained in another dictionary (out_vardict) by keys
#See resample tool for resampling_type options (BILINEAR, CUBIC, NEAREST, MAJORITY)
def hydroresample(in_vardict, out_vardict, in_hydrotemplate, resampling_type='NEAREST'):
    templatedesc = arcpy.Describe(in_hydrotemplate)

    # Check that all in_vardict keys are in out_vardict (that each input path has a matching output path)
    keymatch = {l: l in out_vardict for l in in_vardict}
    if not all(keymatch.values()):
        raise ValueError('All keys in in_vardict are not in out_vardict: {}'.format(
            [l for l in keymatch if not keymatch[l]]))

    # Iterate through input rasters
    for var in in_vardict:
        outresample = out_vardict[var]

        if not arcpy.Exists(outresample):
            print('Processing {}...'.format(outresample))
            arcpy.env.extent = arcpy.env.snapRaster = in_hydrotemplate
            arcpy.env.XYResolution = "0.0000000000000001 degrees"
            arcpy.env.cellSize = templatedesc.meanCellWidth
            print('%.17f' % float(arcpy.env.cellSize))

            try:
                arcpy.Resample_management(in_raster=in_vardict[var],
                                          out_raster=outresample,
                                          cell_size=templatedesc.meanCellWidth,
                                          resampling_type=resampling_type)
            except Exception:
                print("Exception in user code:")
                traceback.print_exc(file=sys.stdout)
                arcpy.ResetEnvironments()

        else:
            print('{} already exists...'.format(outresample))

        # Check whether everything is the same
        maskdesc = arcpy.Describe(outresample)

        extentcomp = maskdesc.extent.JSON == templatedesc.extent.JSON
        print('Equal extents? {}'.format(extentcomp))
        if not extentcomp: print("{0} != {1}".format(maskdesc.extent, templatedesc.extent))

        cscomp = maskdesc.meanCellWidth == templatedesc.meanCellWidth
        print('Equal cell size? {}'.format(cscomp))
        if not cscomp: print("{0} != {1}".format(maskdesc.meanCellWidth, templatedesc.meanCellWidth))

        srcomp = compsr(outresample, in_hydrotemplate)
        print('Same Spatial Reference? {}'.format(srcomp))
        if not srcomp: print("{0} != {1}".format(maskdesc.SpatialReference.name, templatedesc.SpatialReference.name))

    arcpy.ResetEnvironments()

# Perform euclidean allocation on all rasters whose path is provided in a dictionary (in_vardict)
# for all pixels that are NoData in in_vardict but have data in in_hydrotemplate.
def hydronibble(in_vardict, out_vardict, in_hydrotemplate, nodatavalue=-9999):
    arcpy.env.extent = arcpy.env.snapRaster = in_hydrotemplate
    arcpy.env.XYResolution = "0.0000000000000001 degrees"
    arcpy.env.cellSize = arcpy.Describe(in_hydrotemplate).meanCellWidth

    # Perform euclidean allocation to HydroSHEDS land mask pixels with no WorldClim data
    for var in in_vardict:
        if arcpy.Exists(in_vardict[var]):
            outnib = out_vardict[var]
            if not arcpy.Exists(outnib):
                print('Processing {}...'.format(outnib))
                try:
                    mismask = Con((IsNull(in_vardict[var])) & (~IsNull(in_hydrotemplate)), in_hydrotemplate)

                    #Perform euclidean allocation to those pixels
                    Nibble(in_raster=Con(~IsNull(mismask), nodatavalue, in_vardict[var]), #where mismask is not NoData (pixels for which var is NoData but hydrotemplate has data), assign nodatavalue (provided by user, not NoData), otherwise, keep var data (see Nibble tool)
                           in_mask_raster=in_vardict[var],
                           nibble_values='DATA_ONLY',
                           nibble_nodata='PRESERVE_NODATA').save(outnib)

                    del mismask

                except Exception:
                    print("Exception in user code:")
                    traceback.print_exc(file=sys.stdout)
                    del mismask
                    arcpy.ResetEnvironments()

            else:
                print('{} already exists...'.format(outnib))
        else:
            print('Input - {} does not exists...'.format(in_vardict[var]))

    arcpy.ResetEnvironments()

#Retry three times if urllib2.urlopen fails
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

#Take the extent from a dataset and return the extent in the projection of choice
def project_extent(in_dataset, out_coor_system, out_dataset=None):
    """
    :param in_dataset: dataset whose extent to project
    :param out_coor_system: output coordinate system for extent (this can also be a dataset whose CS will be used)
    :param out_dataset (optional): path to dataset that will contain projected extent as a point-based bounding box
                                    (otherwise, output dataset is written to scratch gdb and deleted)
    :return: extent object of in_dataset in out_coor_system projection
    """
    # Create multipoint geometry with extent
    modext = arcpy.Describe(in_dataset).extent
    modtilebbox = arcpy.Polygon(
        arcpy.Array([modext.lowerLeft, modext.lowerRight, modext.upperLeft, modext.upperRight,
                     modext.lowerRight,modext.lowerLeft, modext.upperLeft]),
        arcpy.Describe(in_dataset).spatialReference)

    # Project extent
    if not out_dataset==None:
        outext = arcpy.Describe(
            arcpy.Project_management(in_dataset=modtilebbox,
                                     out_dataset=out_dataset,
                                     out_coor_system=arcpy.Describe(out_coor_system).spatialReference)).extent
    else:
        out_dataset=os.path.join(arcpy.env.scratchWorkspace, 'extpoly{}'.format(random.randrange(1000)))
        outext = arcpy.Describe(
            arcpy.Project_management(in_dataset=modtilebbox,
                                     out_dataset=out_dataset,
                                     out_coor_system=arcpy.Describe(out_coor_system).spatialReference)).extent
        arcpy.Delete_management(out_dataset)

    return(outext)

#Given an input extent and a comparison list of datasets, return a new list with only those datasets that intersect
#extent polygon (overlp, touch, or within)
def get_inters_tiles(ref_extent, tileiterator, containsonly=False):
    outlist = []

    # If tile iterator is a list of paths
    if isinstance(tileiterator, list) or isinstance(tileiterator, set):
        for i in tileiterator:
            tileext = arcpy.Describe(i).extent

            if containsonly==True and tileext.contains(ref_extent):
                outlist.append(i)

            elif tileext.overlaps(ref_extent) or tileext.touches(ref_extent) \
                    or tileext.within(ref_extent) or tileext.contains(ref_extent):
                outlist.append(i)

    #if tile iterator is a dictionary of extents, append key
    elif isinstance(tileiterator, dict):
        for k, v in tileiterator.iteritems():
            # print(k)
            # print(v)
            if containsonly==True and v.contains(ref_extent):
                outlist.append(k)

            elif v.overlaps(ref_extent) or v.touches(ref_extent) \
                    or v.within(ref_extent) or v.contains(ref_extent):
                outlist.append(k)

    else:
        raise ValueError('tileiterator is neither a list, a set, nor a dict')

    #If tile iterator is a dictionary
    return(outlist)

# Divide and aggregate each band in a raster by cell size ratio
def catdivagg_list(inras, vals, exclude_list, aggratio):
    return (
        [Aggregate((Con(Raster(inras) == v, 1)),
                   aggratio, aggregation_type='SUM', extent_handling='EXPAND', ignore_nodata='DATA')
         for v in vals if v not in exclude_list])

#Compare whether two layers' spatial references are the same
def compsr(lyr1, lyr2):
    return(arcpy.Describe(lyr1).SpatialReference.exportToString() ==
           arcpy.Describe(lyr2).SpatialReference.exportToString())

#Given the bounding box of a given dataset, the resolution of the dataset and a division ratio
#Output a list of bounding boxes that equally divide the input bounding box by rows and columns
#For instance, with a global dataset and a divratio of 10, this would divide the input dataset into 100 equally sized
#tile without cutting pixels off
def divbb(bbox, res, divratio):
    box_lc_x, box_lc_y, box_rc_x, box_rc_y = bbox
    coln = (box_rc_x - box_lc_x) / float(res)
    rown = (box_rc_y - box_lc_y) / float(res)

    xbblist = np.arange(box_lc_x, box_rc_x + (float(res) * coln / divratio),
                        float(res) * coln / divratio)
    ybblist = np.arange(box_lc_y, box_rc_y + (float(res) * rown / divratio),
                        float(res) * rown / divratio)

    if abs(xbblist[-1]) > abs(box_rc_x):
        xbblist[-1] = box_rc_x

    if abs(ybblist[-1]) > abs(box_rc_y):
        ybblist[-1] = box_rc_y

    xbblist = np.unique(xbblist)
    ybblist = np.unique(ybblist)

    fullbblist = []
    for pairx in zip(xbblist[:-1], xbblist[1:]):
        for pairy in zip(ybblist[:-1], ybblist[1:]):
            fullbblist.append((pairx[0], pairy[0], pairx[1], pairy[1]))

    return (fullbblist)

#Get all files in a ArcGIS workspace (file or personal GDB)
def getwkspfiles(dir, repattern=None):
    arcpy.env.workspace = dir
    filenames_list = (arcpy.ListDatasets() or []) +\
                     (arcpy.ListTables() or []) +\
                     (arcpy.ListFeatureClasses() or []) # Either LisDatsets or ListTables may return None so need to create empty list alternative
    if not repattern == None:
        filenames_list = [os.path.join(dir, filen)
                          for filen in filenames_list if re.search(repattern, filen)]
    return (filenames_list)
    arcpy.ClearEnvironment('workspace')

def getfilelist(dir, repattern=None, gdbf=True, nongdbf=True):
    """Function to iteratively go through all subdirectories inside 'dir' path
    and retrieve path for each file that matches "repattern"
    gdbf and nongdbf allows the user to choose whether to consider ArcGIS workspaces (GDBs) or not or exclusively"""

    try:
        if arcpy.Describe(dir).dataType == 'Workspace':
            if gdbf == True:
                print('{} is ArcGIS workspace...'.format(dir))
                filenames_list = getwkspfiles(dir, repattern)
            else:
                raise ValueError(
                    "A gdb workspace was given for dir but gdbf=False... either change dir or set gdbf to True")
        else:
            filenames_list = []

            if gdbf == True:
                for (dirpath, dirnames, filenames) in os.walk(dir):
                    for in_dir in dirnames:
                        fpath = os.path.join(dirpath, in_dir)
                        if arcpy.Describe(fpath).dataType == 'Workspace':
                            print('{} is ArcGIS workspace...'.format(fpath))
                            filenames_list.extend(getwkspfiles(dir=fpath, repattern=repattern))

            if nongdbf == True:
                for (dirpath, dirnames, filenames) in os.walk(dir):
                    for file in filenames:
                        if repattern is None:
                            filenames_list.append(os.path.join(dirpath, file))
                        else:
                            if re.search(repattern, file):
                                filenames_list.append(os.path.join(dirpath, file))
        return (filenames_list)

    # Return geoprocessing specific errors
    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
    # Return any other type of error
    except:
        # By default any other errors will be caught here
        e = sys.exc_info()[1]
        print(e.args[0])

def pathcheckcreate(path, verbose=True):
    """"Function that takes a path as input and:
      1. Checks which directories and .gdb exist in the path
      2. Creates the ones that don't exist"""

    dirtocreate = []
    # Loop upstream through path to check which directories exist, adding those that don't exist to dirtocreate list
    while not os.path.exists(os.path.join(path)):
        dirtocreate.append(os.path.split(path)[1])
        path = os.path.split(path)[0]

    dirtocreate.reverse()

    # After reversing list, iterate through directories to create starting with the most upstream one
    for dir in dirtocreate:
        # If gdb doesn't exist yet, use arcpy method to create it and then stop the loop to prevent from trying to create anything inside it
        if os.path.splitext(dir)[1] == '.gdb':
            if verbose:
                print('Create {}...'.format(dir))
            arcpy.CreateFileGDB_management(out_folder_path=path,
                                           out_name=dir)
            break

        # Otherwise, if it is a directory name (no extension), make a new directory
        elif os.path.splitext(dir)[1] == '':
            if verbose:
                print('Create {}...'.format(dir))
            path = os.path.join(path, dir)
            os.mkdir(path)

#Concatenate csv files
def mergedel(dir, repattern, outfile, delete=False, verbose=False):
    flist = getfilelist(dir, repattern)
    pd.concat([pd.read_csv(file, index_col=[0], parse_dates=[0])
               for file in flist],
              axis=0) \
        .sort_index() \
        .to_csv(outfile)
    print('Merged and written to {}'.format(outfile))

    if delete == True:
        for tab in flist:
            os.remove(tab)
            if verbose == True:
                print('Delete {}'.format(tab))

def is_downloadable(url):
    """
    Does the url contain a downloadable resource
    """
    try:
        h = requests.head(url, allow_redirects=True)
        header = h.headers
        content_type = header.get('content-type')
        if 'html' in content_type.lower():
            return False
        return True
    except Exception as e:
        traceback.print_exc()
        return False

def get_filename_from_cd(url):
    """
    Get filename from content-disposition
    """
    r = requests.get(url, allow_redirects=True)
    cd = r.headers.get('content-disposition')
    if not cd:
        return None
    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    return fname[0]

def unzip(infile):
    # Unzip folder
    if zipfile.is_zipfile(infile):
        print('Unzipping {}...'.format(os.path.split(infile)[1]))
        with zipfile.ZipFile(infile) as zipf:
            zipfilelist = [info.filename for info in zipf.infolist()]
            listcheck = [f for f in zipfilelist if os.path.exists(os.path.join(infile, f))]
            if len(listcheck) > 0:
                print('Overwriting {}...'.format(', '.join(listcheck)))
            zipf.extractall(os.path.split(infile)[0])
        del zipf
    else:
        raise ValueError('Not a zip file')

def format_dlname(url, outpath, outfile):
    # Get output file name
    if outfile is None:
        outfile = get_filename_from_cd(url)
        if outfile is not None:
            out = os.path.join(outpath, re.sub("""('|")""", '', outfile))
        else:
            out = os.path.join(outpath, os.path.split(url)[1])
    else:
        if len(os.path.splitext(url)[1]) > 0:
            if os.path.splitext(url)[1] == os.path.splitext(outfile)[1]:
                out = os.path.join(outpath, outfile)
            else:
                out = os.path.join(outpath, "{0}{1}".format(outfile + os.path.splitext(url)[1]))
        else:
            out = os.path.join(outpath, outfile)
    del outfile

    return(out)

def dlfile(url, outpath, outfile=None, ignore_downloadable=False,
           fieldnames=None,
           loginprompter=None, username=None, password=None):
    """Function to download file from URL path and unzip it.
    URL (required): URL of file to download
    outpath (required): the full path including
    outfile (optional): the output name without file extension, otherwise gets it from URL. If the file is heavy, this may take a while
    fieldnames (optional): fieldnames in output table if downloading plain text"""

    try:
        if is_downloadable(url) or ignore_downloadable==True:  # check that url is not just html
            # Get output file name
            if outfile is None:
                outfile = get_filename_from_cd(url)
                if outfile is not None:
                    out = os.path.join(outpath, re.sub("""('|")""",'', outfile))
                else:
                    out = os.path.join(outpath, os.path.split(url)[1])
            else:
                if len(os.path.splitext(url)[1]) > 0:
                    if os.path.splitext(url)[1]== os.path.splitext(outfile)[1]:
                        out = os.path.join(outpath, outfile)
                    else:
                        out = os.path.join(outpath, "{0}{1}".format(outfile + os.path.splitext(url)[1]))
                else:
                    out = os.path.join(outpath, outfile)
            del outfile

            # http request
            if username != None and password != None:
                # Create a password manager to deal with the 401 reponse that is returned from Earthdata Login
                password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
                password_manager.add_password(None, loginprompter, username, password)

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

                # Create and submit the request. There are a wide range of exceptions that
                # can be thrown here, including HTTPError and URLError. These should be
                # caught and handled.

                request = urllib2.Request(url)
                f = urllib2.urlopen(request)
                print "downloading " + url
            else:
                f = requests.get(url, allow_redirects=True)
                print "downloading " + url

            # Open local file for writing
            if not os.path.exists(out):
                if 'content-type' in f.headers:
                    if 'csv' in f.headers.get('content-type').lower():  # If csv file
                        df = pd.read_csv(io.StringIO(f.text))
                        df.to_csv(out, index=False)

                    elif 'tiff' in f.headers.get('content-type').lower():
                        with open(out, "wb") as local_file:
                            local_file.write(f.content)

                    elif 'x-hdf' in f.headers.get('content-type').lower():
                        #CHUNK = 16 * 1024
                        with open(out, 'wb') as local_file:
                            shutil.copyfileobj(f, local_file)#, CHUNK)

                    elif f.headers.get('content-type').lower() == 'text/plain':  # If plain text
                        dialect = csv.Sniffer().sniff(f.text)
                        txtF = csv.DictReader(f.text.split('\n'),
                                              delimiter=dialect.delimiter,
                                              fieldnames=fieldnames)
                        with open(out, "wb") as local_file:
                            writer = csv.DictWriter(local_file, fieldnames=fieldnames)
                            writer.writeheader()
                            for row in txtF:
                                writer.writerow(row)

                    elif f.headers.get('content-type').lower() == 'application/x-gzip':
                        outunzip = os.path.splitext(out)[0]

                        # Very inelegant. But trying to download and decompress in memory always messes up files
                        response = requests.get(url, stream=True)
                        if response.status_code == 200:
                            with open(out, 'wb') as f:
                                f.write(response.raw.read())
                        with gzip.GzipFile(out, 'rb') as input:
                            print('Unzipping {0} to {1}'.format(out, outunzip))
                            s = input.read()
                            with open(outunzip, 'wb') as output:
                                output.write(s)

                    elif f.headers.get('content-type').lower() == 'application/zip':
                        with open(out, "wb") as local_file:
                            local_file.write(f.read())
                        # Unzip downloaded file
                        try:
                            unzip(out)
                        except:
                            z = zipfile.ZipFile(io.BytesIO(f.content))
                            if isinstance(z, zipfile.ZipFile):
                                z.extractall(os.path.split(out)[0])

                    elif f.headers.get('content-type').lower() == 'application/javascript':
                        with open(out, "w") as local_file:
                            for line in f.read():
                                # write line to output file
                                local_file.write(line)

                elif os.path.splitext(url)[1] == '.gz':
                    outunzip = os.path.splitext(out)[0]
                    if not os.path.exists(outunzip):
                        # Very inelegant. But trying to download and decompress in memory always messes up files
                        response = requests.get(url, stream=True)
                        if response.status_code == 200:
                            with open(out, 'wb') as f:
                                f.write(response.raw.read())
                        with gzip.GzipFile(out, 'rb') as input:
                            print('Unzipping {0} to {1}'.format(out, outunzip))
                            s = input.read()
                            with open(outunzip, 'wb') as output:
                                output.write(s)
                    else:
                        print('{} already exists...'.format(outunzip))


                else:  # Otherwise, just try reading
                    try:  # Try writing to local file
                        with open(out, "wb") as local_file:
                            local_file.write(f.read())
                        # Unzip downloaded file
                        try:
                            unzip(out + '.zip')
                        except:
                            z = zipfile.ZipFile(io.BytesIO(f.content))
                            if isinstance(z, zipfile.ZipFile):
                                z.extractall(os.path.split(out)[0])
                    except Exception:
                        os.remove(out)
                        if os.path.splitext(url)[1] == '.zip':  # If fails and is zip, directly download zip in memory
                            print('Try downloading zip in memory...')
                            z = zipfile.ZipFile(io.BytesIO(f.content))

                if not os.path.exists(out):
                    raise Warning('No error was generated but {} was not downloaded. '
                                  'Check that file type is included '
                                  'in function options'.format(out))

            else:
                print('{} already exists...'.format(out))
        else:
            print('File not downloadable...')
        return(out)

    # handle errors
    except requests.exceptions.HTTPError, e:
        print "HTTP Error:", e.code, url
    except Exception:
        traceback.print_exc()
        if os.path.exists(out):
            os.remove(out)


                ######DID NOT WORK
                # urllib.urlretrieve(url, out)
                ######KEPT HANGING
                # try:
                #     r = urllib2.urlopen(url)