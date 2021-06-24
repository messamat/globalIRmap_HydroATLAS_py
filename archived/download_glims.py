from utility_functions import *

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