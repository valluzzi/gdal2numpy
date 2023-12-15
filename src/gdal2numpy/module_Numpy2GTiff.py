# -------------------------------------------------------------------------------
# Licence:
# Copyright (c) 2012-2022 Valerio for Gecosistema S.r.l.
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
# Name:        module_Numpy2GTiff.py
# Purpose:
#
# Author:      Luzzi Valerio
#
# Created:
# -------------------------------------------------------------------------------
import os
import numpy as np
from osgeo import gdal, gdalconst
from .filesystem import justpath, mkdirs
from .module_open import OpenRaster
from .module_ogr import GetSpatialRef
from .module_s3 import *
from .module_log import Logger


def CalculateOverviews(ds):
    """
    CalculateOverviews - Calculate overviews
    :param ds:
    :return:
    """
    m, n = ds.RasterYSize, ds.RasterXSize
    s = 2
    overviews = []
    while m // s > 1 and n // s > 1:
        overviews.append(s)
        s *= 2
    return overviews


def GTiff2Cog(filetif, fileout=None, algo="NEAREST", verbose=False):
    """
    GTiff2Cog - Convert a GTiff to COG
    algo = one of "AVERAGE", "AVERAGE_MAGPHASE", "RMS", "BILINEAR", "CUBIC", "CUBICSPLINE", "GAUSS", "LANCZOS", "MODE", "NEAREST", or "NONE"
    """
    ds = OpenRaster(filetif, gdalconst.GA_Update) # open the file in write mode to build overviews
    if not ds:
        return None
    
    # Inplace conversion if fileout is None
    filetmp = fileout if fileout else tempfilename(prefix="cog_", suffix=".tif") 

    # Set the statistics
    dtype = ds.GetRasterBand(1).DataType
    arr = ds.GetRasterBand(1).ReadAsArray()
    nodata = ds.GetRasterBand(1).GetNoDataValue()
    if dtype in (gdal.GDT_Float32, gdal.GDT_Float64):
        arr[arr <= -9999] = np.nan
        minValue = float(np.nanmin(arr))
        maxValue = float(np.nanmax(arr))
        meanValue = float(np.nanmean(arr))
        stdValue = float(np.nanstd(arr))
        #(f"minValue={minValue}, maxValue={maxValue}, meanValue={meanValue}, stdValue={stdValue}")
        ds.GetRasterBand(1).SetStatistics(minValue, maxValue, meanValue, stdValue)

    driver = gdal.GetDriverByName("COG")
    if driver:
        COMPRESSION = "DEFLATE"
        CO = [f"COMPRESS={COMPRESSION}", ]
        Logger.debug(f"Creating a COG..{CO}")
        #ds.BuildOverviews('NEAREST', [2, 4, 8, 16, 32])
        ds.BuildOverviews(algo, CalculateOverviews(ds))
        dst_ds = driver.CreateCopy(filetmp, ds, False, CO)
        dst_ds = None
    else:
        BLOCKSIZE = 512
        COMPRESSION = "DEFLATE"
        CO = ["BIGTIFF=YES",
              "TILED=YES",
              f"BLOCKXSIZE={BLOCKSIZE}",
              f"BLOCKXSIZE={BLOCKSIZE}",
              f"COMPRESS={COMPRESSION}", "-ro"]
        driver = gdal.GetDriverByName("GTiff")  # GTiff or MEM
        dst_ds = driver.CreateCopy(filetmp, ds, False, CO)
        dst_ds = None
    
    ds = None

    #Inplace conversion if fileout is None
    if fileout is None:
        fileout = filetif
        
    move(filetmp, fileout)

    return fileout if os.path.isfile(fileout) else None


def Numpy2GTiff(arr, gt, prj, fileout, format="GTiff", save_nodata_as=-9999, metadata=None, verbose=False):
    """
    Numpy2GTiff - Write a numpy array in  a GTiff file
    :param arr: the numpy array
    :param gt:  the geotransform array (x0, px, r0, y0, r1, py)
    :param prj: the proj4 string
    :param fileout: the output filename
    :param format: the format GTiff/COG/etc...
    :param save_nodata_as: the nodata
    :param metadata:
    :return: returns the pathname
    """
    GDT = {
        'uint8': gdal.GDT_Byte,
        'uint16': gdal.GDT_UInt16,
        'uint32': gdal.GDT_UInt32,
        'int16': gdal.GDT_Int16,
        'int32': gdal.GDT_Int32,

        'float32': gdal.GDT_Float32,
        'float64': gdal.GDT_Float64
    }

    


    if format.upper() == "GTIFF":
        CO = ["BIGTIFF=YES", "TILED=YES", "BLOCKXSIZE=512", "BLOCKYSIZE=512", "COMPRESS=LZW"]
    elif format.upper() == "COG":
        CO = ["BIGTIFF=YES", "COMPRESS=DEFLATE", "NUM_THREADS=ALL_CPUS"]
    else:
        CO = []


    if isinstance(arr, np.ndarray):
        rows, cols = arr.shape
        if rows > 0 and cols > 0:
            dtype = str(arr.dtype).lower()
            dtype = GDT[dtype] if dtype in GDT else gdal.GDT_Float64

            driver = gdal.GetDriverByName("COG")
            cog = driver and f"{format}".upper() == "COG"

            drivername = "GTiff" if not cog else "MEM"
            MEM_CO = CO if not cog else []

            # Check if fileout is a S3 path
            filetif = tempname4S3(fileout) if iss3(fileout) else fileout
            # ----
            # Create the path to fileout if not exists
            mkdirs(justpath(filetif))

            # Create the output dataset
            driver = gdal.GetDriverByName(drivername)  # GTiff or MEM
            ds = driver.Create(filetif, cols, rows, 1, dtype, MEM_CO)  # fileout is ignore if MEM

            if gt is not None:
                ds.SetGeoTransform(gt)
            if prj is not None:
                if not f"{prj}".upper().startswith("PROJCS["):
                    srs = GetSpatialRef(prj)
                    prj = srs.ExportToWkt()
                ds.SetProjection(prj)
            if metadata is not None:
                ds.SetMetadata(metadata)
                # ds.GetRasterBand(1).SetMetadata(metadata) set metadata to the specified band

            # Set the statistics
            if dtype in (gdal.GDT_Float32, gdal.GDT_Float64):
                data = np.array(arr)
                data[data == save_nodata_as] = np.nan
                minValue = float(np.nanmin(data))
                maxValue = float(np.nanmax(data))
                meanValue = float(np.nanmean(data))
                stdValue = float(np.nanstd(data))
                ds.GetRasterBand(1).SetStatistics(minValue, maxValue, meanValue, stdValue)
            # ---

            ds.GetRasterBand(1).SetNoDataValue(save_nodata_as)
            ds.GetRasterBand(1).WriteArray(arr)

            if cog:
                Logger.debug(f"Creating a COG..{CO}")
                driver = gdal.GetDriverByName("COG")
                # ds.BuildOverviews('NEAREST', [2, 4, 8, 16, 32])
                ds.BuildOverviews("NEAREST", CalculateOverviews(ds))
                dst_ds = driver.CreateCopy(filetif, ds, False, CO)
                ds = dst_ds

            ds.FlushCache()
            ds = None

            if iss3(fileout):
                move(filetif, fileout)

            return filetif
    return None


def Numpy2AAIGrid(data, gt, prj, filename, save_nodata_as=-9999, format=" %.5g"):
    """
    Numpy2AAIGrid
    """
    ## projection is not used
    (x0, pixelXSize, rot, y0, rot, pixelYSize) = gt
    (rows, cols) = data.shape
    data = np.where(np.isnan(data), save_nodata_as, data)
    stream = open(filename, "w")
    stream.write("ncols         %d\r\n" % (cols))
    stream.write("nrows         %d\r\n" % (rows))
    stream.write("xllcorner     %d\r\n" % (x0))
    stream.write("yllcorner     %d\r\n" % (y0 + pixelYSize * rows))
    stream.write("cellsize      %f\r\n" % (pixelXSize))
    stream.write("NODATA_value  %d\r\n" % (save_nodata_as))
    template = (format * cols) + "\r\n"
    for row in data:
        line = template % tuple(row.tolist())
        stream.write(line)
    stream.close()
    return filename


def Numpy2Gdal(data, gt, prj, filename, save_nodata_as=-9999):
    """
    Numpy2Gdal
    """
    ext = os.path.splitext(filename)[1][1:].strip().lower()
    mkdirs(justpath(filename))
    if ext == "tif" or ext == "tiff":
        return Numpy2GTiff(data, gt, prj, filename, save_nodata_as)
    elif ext == "asc":
        return Numpy2AAIGrid(data, gt, prj, filename, save_nodata_as)
    else:
        return ""
