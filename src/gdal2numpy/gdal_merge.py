# -----------------------------------------------------------------------------
# MIT License:
# Copyright (c) 2012-2024 Luzzi Valerio
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
#
# Name:        gdalmerge.py
# Purpose:
#
# Author:      Luzzi Valerio
#
# Created:     07/10/2024
# -----------------------------------------------------------------------------
import os
import inspect
import numpy as np
from osgeo import gdal, gdalconst
from .module_s3 import copy, move
from .filesystem import tempfilename, forceext, justpath, listify
from .filesystem import remove
from .module_log import Logger


def average(in_ar, out_ar, xoff, yoff, xsize, ysize, raster_xsize, raster_ysize, buf_radius, gt, **kwargs):
    """
    average - average the input arrays
    """
    nodata_value = -9999.0
    # Initialize the output array with NoData value
    # tmp = np.empty_like(out_ar)
    # tmp.fill(nodata_value)
    # for arr in in_ar:
    #     arr[np.isnan(arr)] = nodata_value
    #     tmp[tmp == nodata_value] = arr[tmp == nodata_value]
    # out_ar[:] = tmp[:]

    out_ar.fill(nodata_value)
    for arr in in_ar:
        arr[np.isnan(arr)] = nodata_value
        out_ar[out_ar == nodata_value] = arr[out_ar == nodata_value]

resampling_function_text = f'''<VRTRasterBand dataType="Float32" band="1" subClass="VRTDerivedRasterBand">
    <PixelFunctionType>average</PixelFunctionType>
    <PixelFunctionLanguage>Python</PixelFunctionLanguage>
    <PixelFunctionCode><![CDATA[
import numpy as np

{inspect.getsource(average)}
]]>
    </PixelFunctionCode>
'''


def gdal_merge(filelist, fileout, format="GTiff"):
    """
    gdal_merge
    """
    filetmp = tempfilename(prefix="gdal_merge/tmp_", suffix=".tif")
    tmpdir = justpath(filetmp)

    fileout = fileout or filetmp

    # copy the filelist into a temporary directory
    filelist = listify(filelist)
    filelist_tmp = copy(filelist, tmpdir)

    filevrt = forceext(fileout, "vrt")
    os.makedirs(tmpdir, exist_ok=True)

    co = {
        "gtiff": ["BIGTIFF=YES", "TILED=YES", "BLOCKXSIZE=512", "BLOCKYSIZE=512", "COMPRESS=LZW"],
        "cog":   ["BIGTIFF=YES", "COMPRESS=LZW"],
    }

    format = format.lower() or "gtiff"

    creation_options = co.get(format, [])
    print("List of temporary files:", filelist_tmp)

    ds = gdal.BuildVRT(filevrt, filelist_tmp, **{"srcNodata": -9999})
    if ds is None:
        Logger.error("gdal_merge: no valid input rasters in %s", filelist)
        remove(filelist_tmp)
        return None
    ds.FlushCache()
    del ds

    # read the filevrt file
    content = ""
    with open(filevrt, "r", encoding="utf-8") as f:
        content = f.read()
        content = content.replace(
            '<VRTRasterBand dataType="Float32" band="1">', resampling_function_text)
    # write the filevrt file
    with open(filevrt, "w", encoding="utf-8") as f:
        f.write(content)

    kwargs = {
        "format": format,
        "creationOptions": creation_options,
        "resampleAlg": gdalconst.GRIORA_Average,
        "noData": -9999,
        "stats": True,
    }

    try:
        gdal.UseExceptions()
        gdal.PushErrorHandler('CPLQuietErrorHandler')
        gdal.SetConfigOption("GDAL_VRT_ENABLE_PYTHON", "YES")
        gdal.Translate(filetmp, filevrt, **kwargs)
    except Exception as ex:
        Logger.error(ex)
    finally:
        gdal.SetConfigOption("GDAL_VRT_ENABLE_PYTHON", "")
        gdal.PopErrorHandler()

    # move the filetmp to s3 or locally
    move(filetmp, fileout)

    # cleanup
    filelist_tmp.append(filevrt)
    remove(filelist_tmp)

    return fileout
