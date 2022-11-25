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
# Name:        test3.py
# Purpose:     SetTag
#
# Author:      Luzzi Valerio
#
# Created:
# -------------------------------------------------------------------------------
import os
from src.gdal2numpy import *

if __name__ == "__main__":

    workdir, _ = os.path.split(__file__)
    filename = f"{workdir}/CLSA_LiDAR.tif"
    fileout = f"{workdir}/dem.tif"
    #data, gt, prj = GDAL2Numpy(filename)

    #Numpy2GTiff(data, gt, prj, fileout, save_nodata_as=-9999, metadata={"UM": "meters", "type": "DTM"})

    SetTag(filename, "UM", "meters", 1)
    SetTag(filename, "type", "DTM")

    print(GetMetaData(filename)["metadata"])


    print(GetTag(filename, "UM", 1))