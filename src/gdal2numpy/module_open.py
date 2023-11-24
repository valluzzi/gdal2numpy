# -------------------------------------------------------------------------------
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
# Name:        module_features.py
# Purpose:
#
# Author:      Luzzi Valerio
#
# Created:     31/12/2022
# -------------------------------------------------------------------------------
import os
from osgeo import ogr, gdal
from .filesystem import isshape, isshape
from .module_log import Logger
from .module_s3 import iss3

def OpenShape(fileshp, exclusive=False):
    """
    OpenDataset
    """
    if not fileshp:
        print(f"0) {fileshp}...")
        ds = None
    elif isinstance(fileshp, str) and isshape(fileshp):
        print(f"1) Opening {fileshp}...")
        ds = ogr.Open(fileshp, exclusive)
    elif isinstance(fileshp, str) and iss3(fileshp) and fileshp.endswith(".shp"):
        print(f"2) Downloading file from s3...")
        #ds = ogr.Open(copy(fileshp), exclusive)
        fileshp = fileshp.replace("s3://", "/vsis3/")
        ds = ogr.Open(fileshp, exclusive)
    elif isinstance(fileshp, str) and fileshp.startswith("http") and fileshp.endswith(".shp"):
        print(f"3) Inspect file from https...")
        ds = ogr.Open(f"/vsicurl/{fileshp}", exclusive)
    elif isinstance(fileshp, ogr.DataSource) and GetAccess(fileshp) >= exclusive:
        print(f"4) Dataset already open...")
        ds = fileshp
    elif isinstance(fileshp, ogr.DataSource) and GetAccess(fileshp) < exclusive:
        print(f"5) Change the open mode: Open({exclusive})")
        ds = ogr.Open(fileshp.GetName(), exclusive)
    else:
        print(f"999) {fileshp} is not a valid shapefile") 
        ds = None
    return ds


def GetAccess(ds):
    """
    GetAccess - return the open mode exclusive or shared
    trying to create/delete a field
    """
    res = -1
    if ds:
        ogr.UseExceptions()
        try:
            layer = ds.GetLayer()
            layer.CreateField(ogr.FieldDefn("__test__", ogr.OFTInteger))
            j = layer.GetLayerDefn().GetFieldIndex("__test__")
            layer.DeleteField(j)
            res = 1
        except Exception as ex:
            Logger.error(ex)
            res = 0
        ogr.DontUseExceptions()
    return res


def isstring(s):
    """
    isstring
    """
    return isinstance(s, str)


def OpenRaster(filename, update=0):
    """
    OpenRaster
    """
    if not filename:
        return None
    elif isstring(filename) and filename.lower().endswith(".tif"):
        
        if os.path.isfile(filename):
            pass
        elif filename.lower().startswith("/vsis3/"):
            pass
        elif filename.lower().startswith("http"):
            filename = f"/vsicurl/{filename}"
        elif filename.lower().startswith("s3://"):
            filename = filename.replace("s3://", "/vsis3/")
        elif ".zip/" in filename.lower():
            filename = f"/vsizip/{filename}"
        elif ".gz/" in filename.lower():
            filename = f"/vsigzip/{filename}"
        elif ".tar/" in filename.lower():
            filename = f"/vsitar/{filename}"
        elif ".tar.gz/" in filename.lower():
            filename = f"/vsitar/{filename}"
        elif ".tgz/" in filename.lower():
            filename = f"/vsitar/{filename}"
        elif ".7z/" in filename.lower():
            filename = f"/vsi7z/{filename}"
        elif ".rar/" in filename.lower():
            filename = f"/vsirar/{filename}"
    else:
        return None
    
    ds = ds if isinstance(filename, gdal.Dataset) else gdal.Open(filename, update)
    return ds
