from utility_functions import *

glad_dir = os.path.join(datdir, 'GLAD')
pathcheckcreate(glad_dir)

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





