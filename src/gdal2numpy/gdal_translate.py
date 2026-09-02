# -------------------------------------------------------------------------------
# MIT License:
# Copyright (c) 2012-2021 Luzzi Valerio
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
# Name:        gdalwarp.py
# Purpose:
#
# Author:      Luzzi Valerio
#
# Created:     25/09/2024
# -------------------------------------------------------------------------------import os
import os
import numpy as np
from osgeo import gdal
from .filesystem import tempfilename, justpath, version_lower
from .filesystem import now, total_seconds_from
from .module_ogr import GetExtent
from .module_s3 import move, copy, iss3
from .module_log import Logger
from .module_GDAL2Numpy import GDAL2Numpy
from .module_Numpy2GTiff import Numpy2GTiff

dtypeOf = {
    "byte": gdal.GDT_Byte,
    "int16": gdal.GDT_Int16,
    "uint16": gdal.GDT_UInt16,
    "int32": gdal.GDT_Int32,
    "int64": gdal.GDT_Int32,  # It is not an error gdal.GDT_Int64 does not exits!
    "uint32": gdal.GDT_UInt32,
    "uint64": gdal.GDT_UInt32,  # It is not an error gdal.GDT_Int64 does not exits!
    "float32": gdal.GDT_Float32,
    "float64": gdal.GDT_Float64,
    # --- numpy types ---
    gdal.GDT_Byte: gdal.GDT_Byte,
    gdal.GDT_Int16: gdal.GDT_Int16,
    gdal.GDT_UInt16: gdal.GDT_UInt16,
    gdal.GDT_Int32: gdal.GDT_Int32,
    gdal.GDT_UInt32: gdal.GDT_UInt32,
    gdal.GDT_Float32: gdal.GDT_Float32,
    gdal.GDT_Float64: gdal.GDT_Float64,
    # ---
    np.uint8: gdal.GDT_Byte,
    np.int16: gdal.GDT_Int16,
    np.uint16: gdal.GDT_UInt16,
    np.int32: gdal.GDT_Int32,
    np.int64: gdal.GDT_Int32,  # It is not an error gdal.GDT_Int64 does not exits!
    np.uint32: gdal.GDT_UInt32,
    np.uint64: gdal.GDT_UInt32,  # It is not an error gdal.GDT_Int64 does not exits!
    np.float32: gdal.GDT_Float32,
    np.float64: gdal.GDT_Float64,
}

def gdal_translate(filein, fileout=None, ot=None, a_nodata=None, projwin=None, projwin_srs=None, format="GTiff"):
    """
    gdal_translate: gdal_translate a raster file
    """
    t0 = now()

    co = {
        "gtiff": ["BIGTIFF=YES", "TILED=YES", "BLOCKXSIZE=512", "BLOCKYSIZE=512", "COMPRESS=LZW"],
        "cog":   ["BIGTIFF=YES", "COMPRESS=LZW"],
    }

    format = format.lower() if format else "gtiff"

    creation_options = co.get(format, [])

    projwin = GetExtent(projwin) if projwin else None

    # patch projWin --------------------------------------------
    # in case of projwin = [minx, miny, maxx, maxy]
    # translate it to projwin = [ulx, uly, lrx, lry]
    if projwin and len(projwin) == 4:
        minx, miny, maxx, maxy = tuple(projwin)
        if miny < maxy:
            projwin = [minx, maxy, maxx, miny]
    # end of patch --------------------------------------------

    # Case of filein is a s3 path
    if iss3(filein):
        filein = copy(filein)

    filetmp = tempfilename(prefix="gdal_translate/tmp_", suffix=".tif")
    fileout = fileout if fileout else filetmp

    kwargs = {
        "format": format,
        "creationOptions": creation_options,
        "projWin": projwin,
        "projWinSRS": projwin_srs,
        "stats": True
    }

    if ot and ot in dtypeOf:
        # [-ot {Byte/Int8/Int16/UInt16/UInt32/Int32/UInt64/Int64/Float32/Float64/
        #  CInt16/CInt32/CFloat32/CFloat64}]
        ot = ot.lower() if isinstance(ot, str) else ot
        kwargs["outputType"] = dtypeOf[ot] #gdal.GDT_Float32
    #else:
        # dont include the outputType in the kwargs

    if a_nodata is not None:
        kwargs["noData"] = a_nodata

    #print("gdal.Translate with(projWin):", projwin)
    # assert that the folder exists
    os.makedirs(justpath(filetmp), exist_ok=True)
    # Suppress GDAL warnings and errors
    gdal.PushErrorHandler('CPLQuietErrorHandler')
    gdal.Translate(filetmp, filein, **kwargs)
    gdal.PopErrorHandler()

    # this a workaround for the error: ------------------------------
    error_message = gdal.GetLastErrorMsg()
    if error_message and "Error: Computed -srcwin" in error_message:
        # swap the order of the projwin miny with maxy
        #print(f"gdal_translate: error message: {error_message}")
        projwin = [projwin[0], projwin[3], projwin[2], projwin[1]]
        kwargs["projWin"] = projwin
        #print(f"gdal_translate: retrying with projwin swapped: {projwin}")
        gdal.Translate(filetmp, filein, **kwargs)
        #print(f"---")
    # end of workaround --------------------------------------------

    # WORKAROUND: When using nearest-neighbor resampling, the window specified by -projwin is expanded (rounded, for GDAL < 3.11) if necessary to match input pixel boundaries. For other resampling algorithms, the window is not modified. (see: https://gdal.org/en/stable/programs/gdal_translate.html#cmdoption-gdal_translate-projwin)
    tmp_extent = GetExtent(fileout)
    if version_lower(gdal.__version__, '3.11') and list(tmp_extent) != list(projwin):
        Logger.warning(f"gdal_translate: projwin {projwin} does not match the extent of the output file {tmp_extent}. This is a known issue with GDAL < 3.11 when using nearest-neighbor resampling. Forcing specified gt into output file.")
        tmp_data, tmp_gt, tmp_prj = GDAL2Numpy(filetmp, load_nodata_as=np.nan)
        # Force gt to match projwin
        tmp_gt = list(tmp_gt)
        tmp_gt[0] = projwin[0]
        tmp_gt[3] = projwin[1]
        kwargs = {
            ** ( {'save_nodata_as': a_nodata} if a_nodata is not None else dict() ),
        }
        filetmp = Numpy2GTiff(tmp_data, tmp_gt, tmp_prj, tempfilename(prefix="gdal_translate/tmp_", suffix=".tif"), **kwargs)
    # end of workaround ------------------------------------------------
        

    move(filetmp, fileout)

    Logger.debug(f"gdal_translate: completed in {total_seconds_from(t0)} s.")
    # ----------------------------------------------------------------------
    return fileout
