# -------------------------------------------------------------------------------
# Licence:
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
# Name:        module_ogr.py
# Purpose:
#
# Author:      Luzzi Valerio
#
# Created:     16/06/2021
# -------------------------------------------------------------------------------
import glob
import math
import os
import re
import json
import pkgutil
import shutil
import site
from osgeo import gdal
from osgeo import osr, ogr
from pyproj import CRS
from .filesystem import justext, juststem, forceext, justpath
from .filesystem import strtofile, filetostr, md5text, listify, normshape, parse_shape_path
from .module_open import OpenRaster
from .module_open import OpenShape
from .module_s3 import isfile, isshape, israster
from .module_log import Logger
from Levenshtein import distance

shpext = ("shp", "dbf", "shx", "prj", "qpj", "qml", "qix", "idx", "dat", "sbn", "sbx", "fbn", "fbx", "ain", "aih",
          "atx", "qlr", "mta", "qmd", "cpg")


def create_cpg(fileshp):
    """
    create_file_cpg - add a file.cpg
    :param fileshp:
    :return:
    """
    strtofile("UFT-8", forceext(fileshp, "cpg"))


def ogr_move(src, dst):
    """
    copyshp
    """
    res = shutil.move(src, dst)
    if "shp" == justext(src).lower():
        for ext in shpext:
            src = forceext(src, ext)
            dst = dst if os.path.isdir(dst) else forceext(dst, ext)
            if os.path.isfile(src):
                if os.path.isfile(forceext(dst, ext)):
                    os.unlink(forceext(dst, ext))
                shutil.move(src, dst)

    return res


def ogr_copy(src, dst):
    """
    copyshp
    """
    res = shutil.copy2(src, dst)
    if "shp" == justext(src).lower():
        for ext in shpext:
            src = forceext(src, ext)
            filedst = forceext(dst, ext)
            filedst = dst if os.path.isdir(dst) else filedst
            if os.path.isfile(src):
                if os.path.isfile(filedst):
                    os.unlink(filedst)
                shutil.copy2(src, filedst)
    return res


def ogr_remove(filename):
    """
    remove
    """
    if os.path.isfile(filename):
        if justext(filename).lower() in ("shp",):
            driver = ogr.GetDriverByName("ESRI Shapefile")
            driver.DeleteDataSource(filename)
            for ext in shpext:
                fileaux = forceext(filename, ext)
                if os.path.isfile(fileaux):
                    os.unlink(fileaux)
        else:
            os.unlink(filename)
    return not os.path.isfile(filename)


def Haversine(lat1, lon1, lat2, lon2):
    """
    Haversine Distance
    """
    R = 6371008.8  # Earth radius in kilometers

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    a = math.sin(dLat / 2) ** 2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(dLon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def GetPixelSize(filename, um="m"):
    """
    GetPixelSize
    """
    ds = OpenRaster(filename)
    if ds:
        m, n = ds.RasterYSize, ds.RasterXSize
        minx, px, _, maxy, _, py = ds.GetGeoTransform()
        prj = ds.GetProjection()
        ds = None

        # srs = osr.SpatialReference()
        # srs.ImportFromProj4(prj)
        srs = GetSpatialRef(prj)

        if srs.IsGeographic() and um == "m":
            dx = Haversine(maxy, minx, maxy, minx + px * n) / n
            dy = Haversine(maxy, minx, maxy + m * py, minx) / m
            return round(dx, 1), round(dy, 1)

        return px, abs(py)

    return None, None


def GetPixelArea(filename, um="m"):
    """
    GetPixelArea
    """
    px, py = GetPixelSize(filename, um)
    return abs(px * py)


def SamePixelSize(filename1, filename2, decimals=-1):
    """
    SamePixelSize
    """
    size1 = GetPixelSize(filename1)
    size2 = GetPixelSize(filename2)
    if decimals >= 0:
        size1 = [round(item, decimals) for item in size1]
        size2 = [round(item, decimals) for item in size2]
    return size1 == size2


def GetDataType(filename):
    """
    GetDataType
    """
    ds = OpenRaster(filename)
    if ds:
        band = ds.GetRasterBand(1)
        dtype = gdal.GetDataTypeName(band.DataType)
        ds = None
        return dtype
    return None


def AutoIdentify(wkt):
    """
    AutoIdentify
    """
    # get the file pe_hash_list.json from package data
    code = None

    if israster(wkt):
        wkt = OpenRaster(wkt).GetProjection()
    elif isshape(wkt) and isfile(forceext(wkt), "prj"):
        wkt = filetostr(forceext(wkt), "prj")
    elif isinstance(wkt, int):
        wkt = f"EPSG:{wkt}"
        return wkt
    elif isinstance(wkt, osr.SpatialReference):
        wkt = wkt.ExportToWkt()
    elif isinstance(wkt, ogr.DataSource):
        layer = wkt.GetLayer()
        wkt = layer.GetSpatialRef().ExportToWkt()
    elif isinstance(wkt, ogr.Layer):
        wkt = wkt.GetSpatialRef().ExportToWkt()
    elif isinstance(wkt, ogr.Feature):
        wkt = wkt.GetGeometryRef().GetSpatialReference().ExportToWkt()
    elif isinstance(wkt, ogr.Geometry):
        wkt = wkt.GetSpatialReference().ExportToWkt()
    elif isinstance(wkt, str) and re.match(r'^.*?\:\d{4,5}$', wkt):
        return wkt
    elif isinstance(wkt, str) and (wkt.startswith("GEOGCS") or wkt.startswith("PROJCS")):
        pass
    else:
        Logger.warning("The wkt is not a valid string or object")
        return None

    if not code:
        Logger.debug("1a) First chance to identify the wkt")
        srs = CRS.from_wkt(wkt)
        code = srs.to_epsg()
        code = f"EPSG:{code}" if code else None

    if not code:
        Logger.debug("1) First chance to identify the wkt")
        pe_hash_list = json.loads(pkgutil.get_data(
            __name__, "data/pe_hash_list.json").decode("utf-8"))
        pe_hash_list = pe_hash_list["CoordinateSystems"] if "CoordinateSystems" in pe_hash_list else {
        }
        code = pe_hash_list.get(md5text(wkt), None)

    # last chance to identify the wkt
    if not code:
        Logger.debug("2) Second chance to identify the wkt")
        spatial_res_sys_all = json.loads(pkgutil.get_data(
            __name__, "data/spatial_ref_sys_all.json").decode("utf-8"))
        spatial_res_sys_all = spatial_res_sys_all["CoordinateSystems"] if "CoordinateSystems" in spatial_res_sys_all else {
        }
        for authid, srs in spatial_res_sys_all.items():
            if srs["wkt"] == wkt or srs["proj4"] == wkt:
                code = authid
                break

    if not code:
        Logger.debug("3) Third chance to identify the wkt by the name")
        candidates = []
        for authid, srs in spatial_res_sys_all.items():
            if srs["name"] == osr.SpatialReference(wkt).GetName():
                candidates.append((authid, distance(srs["wkt"], wkt)))

        #  sort by distance
        candidates = sorted(candidates, key=lambda x: x[1])
        code = candidates[0][0] if len(candidates) > 1 else None

    return code


def isEPSG(epsg):
    """
    isEPSG - check if the string is a epsg
    """
    return isinstance(epsg, str) and epsg.lower().startswith("epsg")


def isProj4(proj4):
    """
    isProj4 - check if the string is a proj4
    """
    return isinstance(proj4, str) and proj4.lower().startswith("+proj")


def isWkt(wkt):
    """
    isWkt - check if the string is a wkt
    """
    if isinstance(wkt, str):
        for word in ("GEOGCS", "PROJCS", "COMPD_CS"):
            if wkt.upper().startswith(word):
                return True
    return False


def GetSpatialRef(filename):
    """
    GetSpatialRef
    """
    srs = None
    if isinstance(filename, osr.SpatialReference):
        srs = filename

    elif isinstance(filename, int):
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(filename)
        srs.AutoIdentifyEPSG()

    elif isEPSG(filename):
        code = int(filename.split(":")[1])
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(code)
        srs.AutoIdentifyEPSG()

    elif isProj4(filename):
        proj4text = filename
        srs = osr.SpatialReference()
        srs.ImportFromProj4(proj4text)
        srs.AutoIdentifyEPSG()

    elif isWkt(filename):
        wkt = filename
        code = AutoIdentify(wkt)
        srs = osr.SpatialReference()
        if code:
            code = int(code.split(":")[1])
            srs.ImportFromEPSG(code)
        else:
            srs.ImportFromWkt(wkt)
            srs.AutoIdentifyEPSG()

    elif isinstance(filename, str) and isshape(filename):
        ds = OpenShape(filename)
        if ds:
            srs = ds.GetLayer().GetSpatialRef()
            srs.AutoIdentifyEPSG()

    elif isinstance(filename, str) and israster(filename):
        ds = OpenRaster(filename)
        if ds:
            wkt = ds.GetProjection()
            srs = osr.SpatialReference()
            srs.ImportFromWkt(wkt)
            srs.AutoIdentifyEPSG()
    else:
        srs = osr.SpatialReference()

    return srs


def SameSpatialRef(filename1, filename2):
    """
    SameSpatialRef
    """
    srs1 = GetSpatialRef(filename1)
    srs2 = GetSpatialRef(filename2)
    if srs1 and srs2:
        return srs1.IsSame(srs2) or srs1.ExportToProj4() == srs2.ExportToProj4()
    return None


def GetGeometryType(filename):
    """
    GetGeometryType
    :param filename:
    :return:
    """
    ds = OpenShape(filename, 0)
    if ds:
        lyr = ds.GetLayer()
        if lyr:
            geomtype = lyr.GetGeomType()
            name = ogr.GeometryTypeToName(geomtype)
            ds = None
            return name
        ds = None
    return None


def Rectangle(minx, miny, maxx, maxy, deltaperc=0.0):
    """
    Rectangle - create ogr polygon from bbox
    """
    deltaperc = min(1.0, max(0.0, abs(deltaperc)))
    width = abs(maxx - minx)
    height = abs(maxy - miny)
    deltax = width * deltaperc
    deltay = height * deltaperc
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint_2D(minx-deltax, miny-deltay)
    ring.AddPoint_2D(maxx+deltax, miny-deltay)
    ring.AddPoint_2D(maxx+deltax, maxy+deltay)
    ring.AddPoint_2D(minx-deltax, maxy+deltay)
    ring.AddPoint_2D(minx-deltax, miny-deltay)
    # Create polygon
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    return poly


def TransformBBOX(bbox, s_srs=None, t_srs=None):
    """
    TransformBBOX
    """

    if SameSpatialRef(s_srs, t_srs):
        return bbox

    s_srs = GetSpatialRef(s_srs)
    t_srs = GetSpatialRef(t_srs)
    if s_srs and s_srs.IsGeographic():
        s_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if t_srs and t_srs.IsGeographic():
        t_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    transform = osr.CoordinateTransformation(s_srs, t_srs)
    # rect = Rectangle(s_minx, s_miny, s_maxx, s_maxy)
    # rect.Transform(transform)
    # t_minx, t_maxx, t_miny, t_maxy = rect.GetEnvelope()
    # transformed_bbox = (t_minx, t_miny, t_maxx, t_maxy)
    s_minx, s_miny, s_maxx, s_maxy = bbox
    minx, miny, maxx, maxy = transform.TransformBounds(s_minx, s_miny, s_maxx, s_maxy, 2)

     # patch for EPSG:6876
    if SameSpatialRef(t_srs, GetSpatialRef(6876)):
        minx, miny, maxx, maxy = miny, minx, maxy, maxx
    elif SameSpatialRef(t_srs, GetSpatialRef(3035)):
        minx, miny, maxx, maxy = miny, minx, maxy, maxx

    return minx, miny, maxx, maxy


def GetExtent(filename, t_srs=None):
    """
    GetExtent
    """
    s_srs = None
    minx, miny, maxx, maxy = 0, 0, 0, 0
    filename = normshape(filename)
    if isinstance(filename, str) and not isfile(filename):
        # replace ; with , in case of a list of coordinates
        filename = filename.replace(";", ",")
        # replace single space with , in case of a list of coordinates
        filename = re.sub(r"\s+", ",", filename)
        arr = listify(filename)
        minx, miny, maxx, maxy = [float(item) for item in arr] if len(arr) == 4 else [0, 0, 0, 0]
        s_srs = GetSpatialRef(4326)
    elif isinstance(filename, (list, tuple)) and len(filename) == 4:
        minx, miny, maxx, maxy = filename
        s_srs = GetSpatialRef(4326)
    elif isinstance(filename, ogr.Geometry):
        minx, maxx, miny, maxy = filename.GetEnvelope()
        s_srs = filename.GetSpatialReference()
    elif israster(filename):
        ds = OpenRaster(filename)
        if ds:
            "{xmin} {ymin} {xmax} {ymax}"
            m, n = ds.RasterYSize, ds.RasterXSize
            gt = ds.GetGeoTransform()
            minx, px, _, maxy, _, py = gt
            maxx = minx + n * px
            miny = maxy + m * py
            miny, maxy = min(miny, maxy), max(miny, maxy)
            wkt = ds.GetProjection()
            s_srs = osr.SpatialReference()
            s_srs.ImportFromWkt(wkt)
            ds = None

    elif isshape(filename):
        
        ds = OpenShape(filename, 0)
        if ds:
            layer = ds.GetLayer()
            s_srs = layer.GetSpatialRef()
            filename, fieldname, fieldvalue = parse_shape_path(filename)
            if fieldname and fieldname.lower() == "fid":
                fid = int(fieldvalue)
                feature = layer.GetFeature(fid)
                minx, maxx, miny, maxy = feature.GetGeometryRef().GetEnvelope()
            else:
                minx, maxx, miny, maxy = layer.GetExtent()
            
            ds = None

    if t_srs and not SameSpatialRef(s_srs, t_srs):

        minx, miny, maxx, maxy = TransformBBOX([minx, miny, maxx, maxy], s_srs, t_srs)
        #print(f"GetExtent: {minx}, {miny}, {maxx}, {maxy}")

    return minx, miny, maxx, maxy


def SameExtent(filename1, filename2, decimals=-1):
    """
    SameExtent
    """
    extent1 = GetExtent(filename1)
    extent2 = GetExtent(filename2)
    if decimals >= 0:
        extent1 = [round(item, decimals) for item in extent1]
        extent2 = [round(item, decimals) for item in extent2]
    return extent1 == extent2


def SetGDALEnv():
    """
    SetGDALEnv
    """
    os.environ["__PROJ_LIB__"] = os.environ["PROJ_LIB"] if "PROJ_LIB" in os.environ else ""
    os.environ["__GDAL_DATA__"] = os.environ["GDAL_DATA"] if "GDAL_DATA" in os.environ else ""
    os.environ["PROJ_LIB"] = find_PROJ_LIB()
    os.environ["GDAL_DATA"] = find_GDAL_DATA()


def RestoreGDALEnv():
    """
    RestoreGDALEnv
    """
    if "__PROJ_LIB__" in os.environ:
        os.environ["PROJ_LIB"] = os.environ["__PROJ_LIB__"]
    if "__GDAL_DATA__" in os.environ:
        os.environ["GDAL_DATA"] = os.environ["__GDAL_DATA__"]


def find_PROJ_LIB():
    """
    find_PROJ_LIB - the path of proj_lib
    """
    pathnames = []
    roots = ["/usr"] + site.getsitepackages()
    for root in roots:
        pathnames += glob.glob(root + "/**/proj.db", recursive=True)
        if len(pathnames):
            break
    return justpath(pathnames[0]) if len(pathnames)>0 else ""


def find_GDAL_DATA():
    """
    find_GDAL_DATA - the path of GDAL_DATA
    """
    pathnames = []
    roots = ["/usr"] + site.getsitepackages()
    for root in roots:
        pathnames += glob.glob(root + "/**/gt_datum.csv", recursive=True)
        if len(pathnames):
            break
    return justpath(pathnames[0]) if len(pathnames)>0 else ""


def CreateRectangleShape(minx, miny, maxx, maxy, srs, fileshp="tempxy...."):
    """
    CreateRectangleShape
    """
    fileshp = fileshp if fileshp else "./tempdir/rect.shp"
    # Write rest to Shapefile
    driver = ogr.GetDriverByName("ESRI Shapefile")
    if os.path.exists(fileshp):
        driver.DeleteDataSource(fileshp)
    ds = driver.CreateDataSource(fileshp)
    layer = ds.CreateLayer(fileshp, srs, geom_type=ogr.wkbPolygon)
    featureDefn = layer.GetLayerDefn()
    feature = ogr.Feature(featureDefn)
    rect = Rectangle(minx, miny, maxx, maxy)
    feature.SetGeometry(rect)
    layer.CreateFeature(feature)
    feature, layer, ds = None, None, None
    return fileshp


def CreateShapeFileLayer(fileshp, srs, geom_type=ogr.wkbPoint, cpg="UTF-8"):
    """
    CreateShapeFileLayer - wrap CreateDataSource just for shapefiles
    """
    fileshp = forceext(fileshp, "shp")
    ogr_remove(fileshp)
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ds = driver.CreateDataSource(fileshp)
    filecpg = forceext(fileshp, "cpg")
    with open(filecpg, "w") as stream:
        stream.write(cpg)
    srs = GetSpatialRef(srs)
    layer = ds.CreateLayer(juststem(fileshp), srs, geom_type=geom_type)
    ds = None
    return layer


def CopyShape(fileshp, fileout):
    """
    CopyShape
    """
    ds = gdal.VectorTranslate(fileout, fileshp, format='ESRI Shapefile',
                              accessMode='overwrite')
    ds = None  # force flush
