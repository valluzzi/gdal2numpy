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
# Name:        module_features.py
# Purpose:
#
# Author:      Luzzi Valerio, Marco Renzi
#
# Created:     31/12/2022
# -------------------------------------------------------------------------------
import os
import math
import json
import numpy as np
import tempfile
from osgeo import ogr, osr
from .filesystem import listify, md5sum, md5text, juststem
from .module_ogr import SameSpatialRef, GetSpatialRef
from .module_log import Logger
from .module_open import OpenShape


def GetFeatures(fileshp, filter=None, format=None):
    """
    GetFeatures - get all features from file
    """
    res = []
    ds = OpenShape(fileshp)
    if ds:
        # filter features by fid
        filter = listify(filter)
        if filter and len(filter) > 0:
            res = [ds.GetLayer().GetFeature(fid) for fid in filter]
        else:
            res = ds.GetLayer()

        if format is None:
            res = list(res)
        elif format in ("json", "geojson"):
            res = [json.loads(feature.ExportToJson()) for feature in res]
        else:
            res = [feature.ExportToJson() for feature in res]
    return res


def GetFeatureCount(fileshp):
    """
    GetFeatureCount
    """
    n = -1
    ds = OpenShape(fileshp)
    if ds:
        n = ds.GetLayer(0).GetFeatureCount()
    return n


def GetFeatureByFid(fileshp, layername=0, fid=0):
    """
    GetFeatureByFid
    """
    feature = None
    ds = OpenShape(fileshp)
    if ds:
        layer = ds.GetLayer(layername)
        feature = layer.GetFeature(fid)
    ds = None
    return feature


def GetFieldNames(fileshp, filter=None):
    """
    GetFieldNames
    filter: one of Integer|Integer64|Real|String
    """
    ds = OpenShape(fileshp)
    if ds:
        defn = ds.GetLayer().GetLayerDefn()
        fields = [defn.GetFieldDefn(j) for j in range(defn.GetFieldCount())]
        if filter is not None:
            return [field.GetName() for field in fields if ogr.GetFieldTypeName(field.GetType()) in filter]
        # return all
        return [field.GetName() for field in fields]
    return []


def GetNumericFieldNames(fileshp):
    """
    GetNumericFieldNames
    """
    return GetFieldNames(fileshp, ["Integer", "Integer64", "Real"])


def GetValues(fileshp, fieldname):
    """
    GetValues - Get all values of field
    """
    if fieldname in GetFieldNames(fileshp):
        return [feature.GetField(fieldname) for feature in GetFeatures(fileshp)]
    return []


def GetRange(fileshp, fieldname):
    """
    GetRange - returns the min-max values
    """
    minValue, maxValue = np.inf, -np.inf
    if fieldname in GetFieldNames(fileshp, ["Integer", "Integer64", "Real"]):
        for feature in GetFeatures(fileshp):
            value = feature.GetField(fieldname)
            if value is not None:
                minValue = min(value, minValue)
                maxValue = max(value, maxValue)
    return minValue, maxValue


def FieldExists(fileshp, fieldname):
    """
    FieldExists
    """
    idx = -1
    ds = OpenShape(fileshp)
    closeOnExit = type(ds) != type(fileshp)
    if ds:
        layer = ds.GetLayer()
        # idx = -1
        idx = layer.GetLayerDefn().GetFieldIndex(fieldname)
        # layerdefn = layer.GetLayerDefn()
        # n = layerdefn.GetFieldCount()
        # for j in range(n):
        #    fielddefn = layerdefn.GetFieldDefn(j)
        #    if fielddefn.GetName().upper() == f"{fieldname}".upper():
        #        idx = j
        # Logger.info(f"searching field {fieldname}={idx}")
        ds = None if closeOnExit else ds
    return idx


def DeleteField(fileshp, fieldname):
    """
    DeleteField
    """
    res = False
    ds = OpenShape(fileshp, True)
    closeOnExit = type(ds) != type(fileshp)
    j = FieldExists(ds, fieldname)
    if j >= 0:
        Logger.debug(f"Deleting...{fieldname}({j})")
        ds.GetLayer().DeleteField(j)
        res = True
    ds = None if closeOnExit else ds
    return res


def AddField(fileshp, fieldname, dtype=np.float32, width=-1, precision=-1, defaultValue=None, verbose=False):
    """
    AddField
    """
    NUMPY2OGR = {
        np.int8: {"dtype": ogr.OFTInteger, "width": 3, "precision": 0},
        np.int16: {"dtype": ogr.OFTInteger, "width": 5, "precision": 0},
        np.int32: {"dtype": ogr.OFTInteger, "width": 10, "precision": 0},
        np.int64: {"dtype": ogr.OFTInteger64, "width": 20, "precision": 0},
        np.uint8: {"dtype": ogr.OFTInteger, "width": 3, "precision": 0},
        np.uint16: {"dtype": ogr.OFTInteger, "width": 5, "precision": 0},
        np.uint32: {"dtype": ogr.OFTInteger, "width": 10, "precision": 0},
        np.uint64: {"dtype": ogr.OFTInteger64, "width": 20, "precision": 0},
        np.float16: {"dtype": ogr.OFTReal, "width": 10, "precision": 3},
        np.float32: {"dtype": ogr.OFTReal, "width": 19, "precision": 4},
        np.float64: {"dtype": ogr.OFTReal, "width": 24, "precision": 6},
        np.bool_: {"dtype": ogr.OFTInteger, "width": 1, "precision": 0},
        np.str_: {"dtype": ogr.OFTString, "width": 254, "precision": 0},
        str: {"dtype": ogr.OFTString, "width": 254, "precision": 0},
    }
    res = False
    ds = OpenShape(fileshp, True)
    closeOnExit = type(fileshp) != type(ds)
    if ds:
        layer = ds.GetLayer()
        field = NUMPY2OGR[dtype] if dtype in NUMPY2OGR else {
            "dtype": ogr.OFTString, "width": 254, "precision": 0}
        width = width if width > 0 else field["width"]
        precision = precision if precision >= 0 else field["precision"]
        newfield = ogr.FieldDefn(fieldname, field["dtype"])
        newfield.SetWidth(width)
        newfield.SetPrecision(precision)
        if defaultValue is not None:
            newfield.SetDefault(f"{defaultValue}")

        # Check the field not exists
        j = FieldExists(ds, fieldname)
        fielddef = layer.GetLayerDefn().GetFieldDefn(j) if j >= 0 else None

        # Nessun cambiamento
        if fielddef and fielddef.GetType() == field["dtype"] \
                and fielddef.GetWidth() == width \
                and fielddef.GetPrecision() == precision:
            res = False
        # Stesso tipo o verso strighe
        elif fielddef and (fielddef.GetType() == field["dtype"] or field["dtype"] == ogr.OFTString):
            Logger.info(
                f"Altering field definition of {fieldname}({width}:{precision})")
            layer.AlterFieldDefn(
                j, newfield, ogr.ALTER_TYPE_FLAG | ogr.ALTER_WIDTH_PRECISION_FLAG)
            res = True
        else:
            Logger.info(
                f"Creating a new field {fieldname}({width}:{precision})")
            layer.CreateField(newfield)
            res = True

        # setting the default value
        if res and defaultValue is not None:
            # layer.StartTransaction()
            for feature in layer:
                feature.SetField(fieldname, defaultValue)
                layer.SetFeature(feature)
            # layer.CommitTransaction()
        # ----

    ds = None if closeOnExit else ds
    return res


def Transform(fileshp, t_srs, fileout=None):
    """
    Transform - reproject the shapefile
    t_srs: target spatial reference Can be also a template filepath
    """
    if SameSpatialRef(fileshp, t_srs):
        Logger.debug("Nothing to do. The srs is the same.")
        return fileshp

    t_srs = GetSpatialRef(t_srs)

    fileout = fileout if fileout else f"{tempfile.gettempdir()}/{md5sum(fileshp)}_{md5text(t_srs.GetName())}.shp"

    ds = OpenShape(fileshp)
    if ds:
        layer = ds.GetLayer()

        # set spatial reference and transformation
        defn = layer.GetLayerDefn()
        s_srs = layer.GetSpatialRef()
        s_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        t_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        transform = osr.CoordinateTransformation(s_srs, t_srs)

        driver = ogr.GetDriverByName("Esri Shapefile")
        dw = driver.CreateDataSource(fileout)
        outlayer = dw.CreateLayer('', t_srs, defn.GetGeomType())

        # Copy each field
        for j in range(defn.GetFieldCount()):
            fielddefn = defn.GetFieldDefn(j)
            outlayer.CreateField(fielddefn)

        # Copy and transform each feature
        for feature in layer:
            transformed = feature.GetGeometryRef()
            if transformed:
                transformed.Transform(transform)

                geom = ogr.CreateGeometryFromWkb(transformed.ExportToWkb())
                defn = outlayer.GetLayerDefn()
                new_feature = ogr.Feature(defn)
                for j in range(defn.GetFieldCount()):
                    new_feature.SetField(j, feature.GetField(j))
                new_feature.SetGeometry(geom)
                outlayer.CreateFeature(new_feature)
                new_feature = None

        ds, dw = None, None
        return fileout
    return False


def QueryByPoint(file_shp, point):
    """
    QueryByPoint - Search the closest geometry to the point
    fileshp: shapefile path
    point: [lon, lat] in EPSG:4326
    """
    closest_geometry_id = None

    lon, lat = point
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(lon, lat)  # Replace 'x' and 'y' with your point coordinates
    # Open the shapefile
    ds = OpenShape(file_shp, 0)
    if ds:
        layer = ds.GetLayer(0)
        t_srs = layer.GetSpatialRef()

        s_srs = osr.SpatialReference()
        s_srs.ImportFromEPSG(4326)
        s_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

        # Transform the point into the same projection system as the layer
        if not SameSpatialRef(t_srs, s_srs):
            transform = osr.CoordinateTransformation(s_srs, t_srs)
            point.Transform(transform)

        closest_distance = float('inf')

        layer.ResetReading()
        for feature in layer:
            geometry = feature.GetGeometryRef()
            # Corto citcuito if the point is inside the geometry
            if point.Intersects(geometry):
                return feature.GetFID()

            distance = point.Distance(geometry)
            if distance < closest_distance:
                closest_distance = distance
                closest_geometry_id = feature.GetFID()

    return closest_geometry_id


def QueryByOsmid(file_shp, osmid):
    """
    QueryByAttribute - Search for alla features that have the attribute osmid=value
    fileshp: shapefile path
    osmid: the value of the attribute
    """
    # Open the shapefile
    features = []
    ds = OpenShape(file_shp, 0)
    if ds:
        layer = ds.GetLayer(0)
        layer.ResetReading()
        layer.SetAttributeFilter(f"osmid={osmid}")
        features = [feature for feature in layer]
        ds = None
        
    return features




def CreateGeometryFromJson(geojson):
    """
    CreateGeometryFromJson
    :param json:
    :return:
    """
    if not isinstance(geojson, str):
        geojson = json.dumps(geojson)
    return ogr.CreateGeometryFromJson(geojson)


def SaveFeatures(features, fileshp):
    """
    SaveFeature

        {
            'type': 'FeatureCollection',
            "crs": { "type": "name", "properties": { "name": 3857 } },
            "features":[ {
                            'type': 'Feature',
                            'geometry': {'type': 'Polygon', 
                                'coordinates': [[[306305.6026338241, 4882527.4138626065], 
                                ... [306305.6026338241, 4882527.4138626065]]]},
                            'properties': None
                       }]
        }
    """
    if features and features["crs"]:
        crs = GetSpatialRef(features["crs"]["properties"]["name"])
    else:
        crs = 4326

    DATATYPE = {
        "Point": ogr.wkbPoint,
        "LineString": ogr.wkbLineString,
        "Polygon": ogr.wkbPolygon,
        "MultiPoint": ogr.wkbMultiPoint,
        "MultiLineString": ogr.wkbMultiLineString,
        "MultiPolygon": ogr.wkbMultiPolygon,
        "int": ogr.OFTInteger,
        "float": ogr.OFTReal,
        "str": ogr.OFTString,
        "text": ogr.OFTString
    }
    layername = juststem(fileshp)

    if not os.path.isfile(fileshp):
        driver = ogr.GetDriverByName("ESRI Shapefile")
        ds = driver.CreateDataSource(fileshp)
        feature = features["features"][0] if features["features"] else None
        if feature:
            dtype = feature["geometry"]["type"]
            layer = ds.CreateLayer(layername, crs, DATATYPE[dtype])
            

            properties = feature["properties"] if feature["properties"] else {}
            
            # properties = { "dtm":1.5 , "hello":"world"}
            for name in properties:
                dtype, dwidth = (f"{properties[name]}:0").split(":")
                p, w = math.modf(float(dwidth))
                p, w = int(p), int(w)
                field_name = ogr.FieldDefn(name, DATATYPE[dtype])
                p = 255 if p == 0 and dtype == "str" else p
                if w:
                    field_name.SetWidth(w)
                if p:
                    field_name.SetPrecision(p)
                layer.CreateField(field_name)
                # Save and close the data source
            ds = None

    ds = ogr.Open(fileshp, 1)
    if ds:
        layer = ds.GetLayer()
        crs = layer.GetSpatialRef()

        layer_definition = layer.GetLayerDefn()
        fieldnames = [layer_definition.GetFieldDefn(
            j).GetName() for j in range(layer_definition.GetFieldCount())]

        for feature in features["features"]:
            f = ogr.Feature(layer_definition)
            geom = CreateGeometryFromJson(feature["geometry"])
            f.SetGeometry(geom)

            for name in listify(feature["properties"]):
                if name in fieldnames:
                    f.SetField(name, properties[name])

            layer.CreateFeature(f)
        ds = None
