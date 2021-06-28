#Inspired by folderstats https://github.com/njanakiev/folderstats
#https://janakiev.com/blog/python-filesystem-analysis/
#https://gis.stackexchange.com/questions/34729/creating-table-containing-all-filenames-and-possibly-metadata-in-file-geodatab/34797#34797

import arcpy
import os
import hashlib
import pandas as pd
from datetime import datetime
from utility_functions import *
import tempfile
import codecs
import cStringIO
from xml.etree.ElementTree import ElementTree


#Look at setloghistory and getloghistory
#Set metadata type such that Item description always have tool used, parameters, dates, etc.
#https://desktop.arcgis.com/en/arcmap/latest/manage-data/metadata/a-quick-tour-of-creating-and-editing-metadata.htm

#identify dates and reformat
#get metadata directly from files

#Create a system in code that writes output files detailing the function name and code that was used to generate
#a file and with what arguments every time something is written

def calculate_hash(filepath, hash_name):
    """Calculate the hash of a file. The available hashes are given by the hashlib module. The available hashes can be listed with hashlib.algorithms_available."""

    hash_name = hash_name.lower()
    if not hasattr(hashlib, hash_name):
        raise Exception('Hash algorithm not available : {}'\
            .format(hash_name))

    with open(filepath, 'rb') as f:
        checksum = getattr(hashlib, hash_name)()
        for chunk in iter(lambda: f.read(4096), b''):
            checksum.update(chunk)

        return checksum.hexdigest()

#Describe object properties arcpy: extension,
def _recursive_folderstats_plain(folderpath, items=None, foldersize=0, num_files=0, current_idx=1,
                                 hash_name=None, ignore_hidden=False,
                                 depth=0, idx=1, parent_idx=0, verbose=False):
    if os.path.isdir(folderpath):
        foldtype = 'Plain'

    for f in os.listdir(folderpath):
        if ignore_hidden and f.startswith('.'):
            continue

        filepath = os.path.join(folderpath, f)
        stats = os.stat(filepath)
        foldersize += stats.st_size
        idx += 1

        if os.path.isdir(filepath):
            if verbose:
                print('FOLDER : {}'.format(filepath))

            idx, items, _foldersize, _num_files = _recursive_folderstats(
                filepath, items, hash_name,
                ignore_hidden, depth + 1, idx, current_idx, verbose)
            foldersize += _foldersize
            num_files += _num_files
        else:
            filename, extension = os.path.splitext(f)
            extension = extension[1:] if extension else None
            item = [idx, filepath, filename, extension, stats.st_size,
                    stats.st_atime, stats.st_mtime, stats.st_ctime,
                    False, None, depth, current_idx, stats.st_uid]
            if hash_name:
                item.append(calculate_hash(filepath, hash_name))
            items.append(item)
            num_files += 1

    stats = os.stat(folderpath)
    foldername = os.path.basename(folderpath)
    item = [current_idx, folderpath, foldername, None, foldersize,
            stats.st_atime, stats.st_mtime, stats.st_ctime,
            True, num_files, depth, parent_idx, stats.st_uid]
    if hash_name:
        item.append(None)
    items.append(item)

    return idx, items, foldersize, num_files


def _recursive_folderstats(folderpath, arcpymeta = True,
                           items=None, hash_name=None,
                           ignore_hidden=False, depth=0, idx=1, parent_idx=0,
                           verbose=False):
    """Helper function that recursively collects folder statistics and returns current id, foldersize and number of files traversed."""
    items = items if items is not None else []
    foldersize, num_files = 0, 0
    current_idx = idx

    if os.access(folderpath, os.R_OK):
        #--------- If arcpymeta == True
        if arcpymeta:
            foldesc = arcpy.Describe(folderpath)
            # --------- If arcpymeta == True and folder is an arcpy workspace
            if foldesc.dataType == 'Workspace':
                if verbose:
                    print('FOLDER : {}'.format(folderpath))

                #Get list of files in workspace
                print('{} is ArcGIS workspace...'.format(folderpath))
                filenames_list = getwkspfiles(folderpath)

                #---------- For each file within folder
                for f in filenames_list:
                    filepath = os.path.join(folderpath, f)
                    filedesc = arcpy.Describe(filepath)

                    #size
                    #time of creation
                    #time last edited


                    if table:
                        #Number of records
                        #Number of fields

                    if dataset:
                        filedesc.datasetType
                        filedesc.DSID
                        filedesc.extent
                        filedesc.spatialReference

                        if raster:
                            number of bands

                        if featureclass:
                            filedesc.featureType
                            filedesc.shapeType
                            #number of features
                            #number of fields

                        if GeometricNetwork:
                            filedesc.featureClassNames
                            filedesc.networkType


                    stats = os.stat(filepath)
                    foldersize += stats.st_size
                    idx += 1

                #---------- For folder
                foldername = os.path.basename(folderpath)
                num_files = len(foldesc.children)
                stats = os.stat(folderpath)
                #Need to work on foldersize

                item = {}
                item['id'] = current_idx
                item['path'] = folderpath
                item['name'] = foldername
                item['extension'] = None
                item['foldersize'] = foldersize
                item['atime'] = stats.st_atime #Time of last access
                item['mtime'] = stats.st_mtime #Time of last modification.
                item['ctime'] = stats.st_ctime #The “ctime” as reported by the operating system. On some systems (like Unix) is the time of the last metadata change, and, on others (like Windows), is the creation time
                item['folder'] = True
                item['folder_type'] = foldesc.workspaceType
                item['folder_extension'] = foldesc.extension
                item['num_files'] = num_files
                item['depth'] = depth
                item['parent'] = parent_idx
                item['uid'] = stats.st_uid

                if hash_name:
                    item.append(None)
                items.append(item)

            # --------- If arcpymeta == True and folder is plain type
            else:
                idx, items, foldersize, num_files = _recursive_folderstats_plain(
                    folderpath, items=items, foldersize=foldersize, num_files=num_files,
                    current_idx=current_idx, hash_name=hash_name, ignore_hidden=ignore_hidden,
                    depth=depth, idx=idx, parent_idx=parent_idx, verbose=verbose)

        #--------- If arcpymeta == False
        else:
            idx, items, foldersize, num_files = _recursive_folderstats_plain(
                folderpath, items=items, foldersize=foldersize, num_files=num_files,
                current_idx=current_idx, hash_name=hash_name, ignore_hidden=ignore_hidden,
                depth=depth, idx=idx, parent_idx=parent_idx, verbose=verbose)

        return idx, items, foldersize, num_files

    #If can't read folderpath
    else:
        raise Warning("Can't read {}...".format(folderpath))


def folderstats(folderpath, hash_name=None, microseconds=False,
                absolute_paths=False, ignore_hidden=False, parent=True,
                verbose=False):
    """Function that returns a Pandas dataframe from the folders and files from a selected folder."""
    columns = ['id', 'path', 'name', 'extension', 'size',
               'atime', 'mtime', 'ctime',
               'folder', 'num_files', 'depth', 'parent', 'uid']
    if hash_name:
        hash_name = hash_name.lower()
        columns.append(hash_name)

    idx, items, foldersize, num_files = _recursive_folderstats(
        folderpath,
        hash_name=hash_name,
        ignore_hidden=ignore_hidden,
        verbose=verbose)
    df = pd.DataFrame(items, columns=columns)

    for col in ['atime', 'mtime', 'ctime']:
        df[col] = df[col].apply(
            lambda d: datetime.fromtimestamp(d) if microseconds else \
                datetime.fromtimestamp(d).replace(microsecond=0))

    if absolute_paths:
        df.insert(1, 'absolute_path', df['path'].apply(
            lambda p: os.path.abspath(p)))

    if not parent:
        df.drop(columns=['id', 'parent'], inplace=True)

    return df

if __name__ == '__main__':
    rootdir = os.path.dirname(os.path.abspath(__file__)).split('\\src')[0]
    bernhardir = os.path.join(rootdir, 'Bernhard')
    testdir = "D:\PhD\HydroATLAS\Bernhard\HydroATLAS\HydroATLAS_Data\Climate\\actual_evapotrans_cgiar.gdb"
    folderpath = testdir
    hash_name = None; microseconds = False; absolute_paths = False; ignore_hidden = True; parent = True; verbose = True
    items = None; hash_name = None; depth = 0; idx = 1; parent_idx = 0; verbose = False
    hydroatlas_df = folderstats(bernhardir, hash_name=None, microseconds=False,
                                absolute_paths=False, ignore_hidden=True, parent=True,
                                verbose=True)
    hydroatlas_df.to_csv(os.path.join(bernhardir, 'metadata.csv'))


#################### FROM https://janakiev.com/blog/python-filesystem-analysis/
# import networkx as nx
#
# # Sort the index
# df_sorted = df.sort_values(by='id')
#
# G = nx.Graph()
# for i, row in df_sorted.iterrows():
#     if row.parent:
#         G.add_edge(row.id, row.parent)
#
# # Print some additional information
# print(nx.info(G))

# ############### FROM https://gis.stackexchange.com/questions/34729/creating-table-containing-all-filenames-and-possibly-metadata-in-file-geodatab/34797#34797
# """
# This script looks through the specified geodatabase and reports the
# names of all data elements, their schema owners and their feature
# dataset (if applicable). Certain metadata elements such as abstract,
# purpose and search keys are also reported.
#
# The output is a CSV file that can be read by Excel, ArcGIS, etc.
#
# Only geodatabases are supported, not folder workspaces.
#
# Note: If run from outside of ArcToolbox, you will need to add
# the metadata tool assemblies to the Global Assembly Cache.
# See: http://forums.arcgis.com/threads/74468-Python-Errors-in-IDLE-when-processing-metadata
#
# Parameters:
#     0 - Input workspace (file geodatabase, personal geodatabase,
#             or SDE connection file)
#     1 - Output CSV file
#
# Date updated: 2/11/2013
# """
#
# import arcpy
# import os
# import csv
# import tempfile
# import codecs
# import cStringIO
# from xml.etree.ElementTree import ElementTree
#
# def ListWorkspaceContentsAndMetadata(workspace):
#     """Generator function that lists the contents of the geodatabase including those within feature datasets.
#        Certain metadata elements are also listed. Only geodatabases are supported, not folder workspaces."""
#
#     if not arcpy.Exists(workspace):
#         raise ValueError("Workspace %s does not exist!" % workspace)
#
#     desc = arcpy.Describe(workspace)
#
#     if not desc.dataType in ['Workspace', 'FeatureDataset']:
#         if not hasattr(desc, "workspaceType") or not desc.workspaceType in ["LocalDatabase", "RemoteDatabase"]:
#             raise ValueError("Workspace %s is not a geodatabase!" % workspace)
#
#     children = desc.children
#     if desc.dataType == 'FeatureDataset':
#         validationWorkspace = os.path.dirname(workspace)
#         fdsName = arcpy.ParseTableName(desc.name, validationWorkspace).split(",")[2].strip() # Get the short name of the feature dataset (sans database/owner name)
#     else:
#         validationWorkspace = workspace
#         fdsName = ""
#
#     for child in children:
#         # Parse the full table name into database, owner, table name
#         database, owner, tableName = [i.strip() if i.strip() != "(null)" else "" for i in arcpy.ParseTableName(child.name, validationWorkspace).split(",")]
#         datasetType = child.datasetType if hasattr(child, "datasetType") else ""
#         alias = child.aliasName if hasattr(child, "aliasName") else ""
#         outrow = [owner, tableName, alias, fdsName, datasetType]
#         try:
#             outrow.extend(GetMetadataItems(child.catalogPath))
#         except:
#             pass
#         print ",".join(outrow)
#         yield outrow
#
#         # Recurse to get the contents of feature datasets
#         if datasetType == 'FeatureDataset':
#             for outrow in ListWorkspaceContentsAndMetadata(child.catalogPath):
#                 yield outrow
#
# def WriteCSVFile(csvfile, rows, header=None):
#     """Creates a CSV file from the input header and row sequences"""
#     with open(csvfile, 'wb') as f:
#         f.write(codecs.BOM_UTF8) # Write Byte Order Mark character so Excel knows this is a UTF-8 file
#         w = UnicodeWriter(f, dialect='excel', encoding='utf-8')
#         if header:
#             w.writerow(header)
#         w.writerows(rows)
#
# def CreateHeaderRow():
#     """Specifies the column names (header row) for the CSV file"""
#     return ("OWNER", "TABLE_NAME", "ALIAS", "FEATURE_DATASET", "DATASET_TYPE", "ORIGINATOR", "CONTACT_ORG", "ABSTRACT", "PURPOSE", "SEARCH_KEYS", "THEME_KEYS")
#
# def CreateDummyXMLFile():
#     """Creates an XML file with the required root element 'metadata' in
#     the user's temporary files directory. Returns the path to the file.
#     The calling code is responsible for deleting the temporary file."""
#     tempdir = tempfile.gettempdir()
#     fd, filepath = tempfile.mkstemp(".xml", text=True)
#     with os.fdopen(fd, "w") as f:
#         f.write("<metadata />")
#         f.close()
#     return filepath
#
# def GetMetadataElementTree(dataset):
#     """Creates and returns an ElementTree object from the specified
#     dataset's metadata"""
#     xmlfile = CreateDummyXMLFile()
#     arcpy.MetadataImporter_conversion(dataset, xmlfile)
#     tree = ElementTree()
#     tree.parse(xmlfile)
#     os.remove(xmlfile)
#     return tree
#
# def GetElementText(tree, elementPath):
#     """Returns the specified element's text if it exists or an empty
#     string if not."""
#     element = tree.find(elementPath)
#     return element.text if element != None else ""
#
# def GetFirstElementText(tree, elementPaths):
#     """Returns the first found element matching one of the specified
#     element paths"""
#     result = ""
#     for elementPath in elementPaths:
#         element = tree.find(elementPath)
#         if element != None:
#             result = element.text
#             break
#     return result
#
# def ListElementsText(tree, elementPath):
#     """Returns a comma+space-separated list of the text values of all
#     instances of the specified element, or an empty string if none are
#     found."""
#     elements = tree.findall(elementPath)
#     if elements:
#         return ", ".join([element.text for element in elements])
#     else:
#         return ""
#
# def GetMetadataItems(dataset):
#     """Retrieves certain metadata text elements from the specified dataset"""
#     tree = GetMetadataElementTree(dataset)
#     originator = GetElementText(tree, "idinfo/citation/citeinfo/origin") # Originator
#     pocorg = GetFirstElementText(tree, ("idinfo/ptcontac/cntinfo/cntperp/cntorg", # Point of contact organization (person primary contact)
#                                         "idinfo/ptcontac/cntinfo/cntorgp/cntorg")) # Point of contact organization (organization primary contact)
#     abstract = GetElementText(tree, "idinfo/descript/abstract") # Abstract
#     purpose = GetElementText(tree, "idinfo/descript/purpose") # Purpose
#     searchkeys = ListElementsText(tree, "dataIdInfo/searchKeys/keyword") # Search keywords
#     themekeys = ListElementsText(tree, "idinfo/keywords/theme/themekey") # Theme keywords
#     del tree
#     metadataItems = (originator, pocorg, abstract, purpose, searchkeys, themekeys)
#     return metadataItems
#
# class UnicodeWriter:
#     """
#     A CSV writer which will write rows to CSV file "f",
#     which is encoded in the given encoding.
#     """
#
#     def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
#         # Redirect output to a queue
#         self.queue = cStringIO.StringIO()
#         self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
#         self.stream = f
#         self.encoder = codecs.getincrementalencoder(encoding)()
#
#     def writerow(self, row):
#         self.writer.writerow([s.encode("utf-8") for s in row])
#         # Fetch UTF-8 output from the queue ...
#         data = self.queue.getvalue()
#         data = data.decode("utf-8")
#         # ... and reencode it into the target encoding
#         data = self.encoder.encode(data)
#         # write to the target stream
#         self.stream.write(data)
#         # empty queue
#         self.queue.truncate(0)
#
#     def writerows(self, rows):
#         for row in rows:
#             self.writerow(row)
#
# if __name__ == '__main__':
#     workspace = arcpy.GetParameterAsText(0)
#     csvFile = arcpy.GetParameterAsText(1)
#     headerRow = CreateHeaderRow()
#     print headerRow
#     datasetRows = ListWorkspaceContentsAndMetadata(workspace)
#     WriteCSVFile(csvFile, datasetRows, headerRow)

