# -------------------------------------------------------------------------------
# MIT License:
# Copyright (c) 2012-2022 Luzzi Valerio
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
# Name:        rain.py
# Purpose:
#
# Author:      Luzzi Valerio
#
# Created:     28/02/2022
# -------------------------------------------------------------------------------
import numpy as np
from osgeo import gdal
from osgeo import ogr, osr
from .module_features import GetNumericFieldNames, Transform
from .module_s3 import copy, iss3
from .module_open import OpenRaster
from .module_open import OpenShape
from .module_log import Logger
from .module_ogr import GetSpatialRef, SameSpatialRef
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

def RasterizeLike(fileshp, filedem, fileout="", dtype=None, burn_fieldname=None, \
                  z_value=None, factor=1.0, nodata=None, buf=0.0, all_touched=False):
    """
    RasterizeLike - Rasterize a shapefile like a raster file
    """
    #gdal.SetConfigOption("SHAPE_RESTORE_SHX", "YES")
    #gdal.SetConfigOption("SHAPE_ENCODING", "UTF-8")
    burn_fieldname = burn_fieldname if burn_fieldname  else "FID"

    #filedem = copy(filedem) if iss3(filedem) else filedem
    fileshp = copy(fileshp) if iss3(fileshp) else fileshp
    fileshp = Transform(fileshp, filedem)

    ds = OpenRaster(filedem)
    vector = OpenShape(fileshp)
    if ds and vector:
        band = ds.GetRasterBand(1)
        m, n = ds.RasterYSize, ds.RasterXSize
        gt, prj = ds.GetGeoTransform(), ds.GetProjection()
        nodata = band.GetNoDataValue() if nodata is None else nodata
        dtype = dtypeOf[dtype] if dtype else band.DataType

        # Open the data source and read in the extent
        # layer = vector.GetLayer()
        # Instead of just get the layer we copy the layer on 
        # and we add a buffer and we transform each geometry
        # if needed

        vlayer = vector.GetLayer()
        s_srs = GetSpatialRef(vlayer.GetSpatialRef())
        t_srs = GetSpatialRef(prj)
        driver = ogr.GetDriverByName("MEMORY")
        source = driver.CreateDataSource("memData")
        layer = source.CreateLayer(vlayer.GetName(), t_srs, geom_type=vlayer.GetGeomType())
        # Copy the fields from the source layer to the memory layer
        layer_defn = vlayer.GetLayerDefn()
        for j in range(layer_defn.GetFieldCount()):
            layer.CreateField(layer_defn.GetFieldDefn(j))
        layer.CreateField(ogr.FieldDefn("FID", ogr.OFTInteger))
        # Copy the features from the source layer to the memory layer

        for feature in vlayer:

            # f is the feature in the memory layer & it has FID field
            f = ogr.Feature(layer.GetLayerDefn())
            geom = feature.GetGeometryRef()
            if geom:
                # # Transform the geometry if it is not in the same projection as the raster
                if not SameSpatialRef(s_srs, t_srs):
                    # Logger.debug(f"Transforming geometry from {s_srs} to {t_srs}")
                    transform = osr.CoordinateTransformation(s_srs, t_srs)
                    geom.Transform(transform)

                # add buffer
                # solo per i poligoni
                if buf > 0 and geom.GetGeometryType() == ogr.wkbPolygon or geom.GetGeometryType() == ogr.wkbMultiPolygon:
                    buffer = geom.Buffer(buf)
                else:
                    buffer = geom

                f.SetFrom(feature)
                f.SetGeometry(buffer)
                f.SetField("FID", feature.GetFID())
                for j in range(layer_defn.GetFieldCount()):
                    f.SetField(layer_defn.GetFieldDefn(j).GetNameRef(), feature.GetField(j))
                layer.CreateFeature(f)
        #-----------------------------------------------------------------------
        # Create the destination data source
        options = [
            "BIGTIFF=YES", 
            "TILED=YES",
            "BLOCKXSIZE=256", 
            "BLOCKYSIZE=256", 
            "COMPRESS=LZW"
        ] if fileout else []
        format = "GTiff" if fileout else "MEM"
        driver = gdal.GetDriverByName(format)
        target_ds = driver.Create(fileout if fileout else "", n, m, 1, dtype, options)
        if gt is not None:
            target_ds.SetGeoTransform(gt)
        if prj is not None:
            target_ds.SetProjection(prj)
        band = target_ds.GetRasterBand(1)
        band.SetNoDataValue(nodata)
        band.Fill(nodata)

        fieldnames = GetNumericFieldNames(fileshp)+["FID"]
        # Rasterize
        if factor == 0.0:
            # if factor is 0 then burn 0, may be this does not have much sense
            gdal.RasterizeLayer(target_ds, [1], layer, burn_values=[0.0], options=[f"ALL_TOUCHED={all_touched}"])
        elif burn_fieldname and burn_fieldname in fieldnames and factor==1.0 and z_value is None:
            # if factor is 1 then burn the field value
            gdal.RasterizeLayer(target_ds, [1], layer, options=[f"ATTRIBUTE={burn_fieldname.upper()}", f"ALL_TOUCHED={all_touched}"])
        elif burn_fieldname and burn_fieldname in fieldnames and factor!=1.0:
            # if factor is not 1 then burn the field value multiplied by factor
            # in case of fieldname we have to pre multiply the each feature value by factor
            # To not modify the original layer we have to copy it in memory
            driver = ogr.GetDriverByName("MEMORY")
            memds = driver.CopyDataSource(vector, "tmp")
            layercpy = memds.GetLayer()
            for feature in layercpy:
                feature.SetField(burn_fieldname, feature.GetField(burn_fieldname) * factor)
                layercpy.SetFeature(feature)
            gdal.RasterizeLayer(target_ds, [1], layercpy, options=["ATTRIBUTE=%s" % (burn_fieldname.upper()), f"ALL_TOUCHED={all_touched}"])
            memds, layercpy = None, None
        elif z_value is not None:
            # in case we hav not fieldname we burn the z_value
            gdal.RasterizeLayer(target_ds, [1], layer, burn_values=[z_value*factor], options=[f"ALL_TOUCHED={all_touched}"])
        else:
            # in all other cases we burn 1
            gdal.RasterizeLayer(target_ds, [1], layer, burn_values=[1], options=[f"ALL_TOUCHED={all_touched}"])

        data = band.ReadAsArray(0, 0, n, m)

        # this cause a error beacuse fileout is already Created 
        # if fileout:
        #     Numpy2GTiff(data, gt, prj, fileout, save_nodata_as=nodata)

        ds, vector, target_ds = None, None, None
        return data, gt, prj

    Logger.error(f"file <{fileshp}> or <{filedem}> does not exist!")
    return None, None, None
