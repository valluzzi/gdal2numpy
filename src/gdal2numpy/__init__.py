#-------------------------------------------------------------------------------
# MIT License:
# Copyright (c) 2012-2020 Valerio for Gecosistema S.r.l.
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
# Name:        module.py_
# Purpose:
#
# Author:      Luzzi Valerio
#
# Created:
#-------------------------------------------------------------------------------
from .filesystem import *
from .module_types import *
from .module_geolocate import *
from .module_GDAL2Numpy import *
from .module_Numpy2GTiff import *
from .module_cog import *
from .module_meta import *
from .module_ogr import *
from .module_features import *
from .module_esri_shape import *
from .module_geojson import ShapeFileFromGeoJSON
from .module_s3 import *
from .module_http import *
from .module_open import get
from .rasterlike import RasterLike
from .rasterizelike import RasterizeLike
from .polygonize import Polygonize
from .dissolve import Dissolve
from .module_gdal import *
from .gdalwarp import gdalwarp
from .gdal_translate import gdal_translate
from .gdal_merge import gdal_merge
from .module_log import *
from .module_xml import *
from .module_extrusion import *
from .module_secrets import *

