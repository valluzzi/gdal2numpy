# -----------------------------------------------------------------------------
# Licence:
# Copyright (c) 2012-2023 Luzzi Valerio
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
# Name:        memory.py
# Purpose:
#
# Author:      Luzzi Valerio
#
# Created:     16/06/2023
# -----------------------------------------------------------------------------

from osgeo import gdal
from .module_log import Logger
from .module_open import OpenRaster
from .module_s3 import *


def GDALEuclideanDistance(fileline, fileout=""):
    """
    GDALEuclideanDistance - compute the euclidean distance from a line/point/polygon
    """
    creation_options = ["BIGTIFF=YES", "TILED=YES", "BLOCKXSIZE=256", "BLOCKYSIZE=256",
                        "COMPRESS=LZW"] if fileout else []
    distance_options = ["DISTUNITS=GEO", "USE_INPUT_NODATA=NO"]
    format = "GTiff" if fileout else "MEM"

    filetmp = tempname4S3(fileout) if iss3(fileout) else fileout
    
    ds = OpenRaster(fileline)
    if ds:
        srcband = ds.GetRasterBand(1)
        gt, prj = ds.GetGeoTransform(), ds.GetProjection()
        cols, rows = ds.RasterXSize, ds.RasterYSize

        #if fileout and os.path.isfile(fileout):
        #    os.remove(fileout)

        driver = gdal.GetDriverByName(format)
        dst = driver.Create(filetmp, cols, rows, 1, gdal.GDT_Float32, creation_options)

        dst.SetGeoTransform(gt)
        dst.SetProjection(prj)

        dstband = dst.GetRasterBand(1)
        # dstband.SetNoDataValue(srcband.GetNoDataValue())

        gdal.ComputeProximity(srcband, dstband, distance_options)

        dist = dstband.ReadAsArray(0, 0, cols, rows)

        srcband = None
        dstband = None
        ds = None
        dst = None

        if iss3(fileout):
            move(filetmp, fileout)
    else:
        Logger.error(f"Unable to open {fileline}")
        return None, None, None

    return dist, gt, prj