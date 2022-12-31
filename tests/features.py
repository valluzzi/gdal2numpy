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
# Name:        features.py
# Purpose:
#
# Author:      Luzzi Valerio
#
# Created:
# -------------------------------------------------------------------------------
from gdal2numpy import *
from osgeo import ogr

if __name__ == "__main__":
    workdir, _ = os.path.split(__file__)
    filename = f"{workdir}/OSM_BUILDINGS_091244.shp"

    print(GetFieldNames(filename))


    print(GetFieldNames(filename, ["Integer", "Integer64"]))
    # print(GetValues(filename, "height"))

    print(GetRange(filename, fieldname="height"))


