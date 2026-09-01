import os
import unittest
import warnings
from gdal2numpy import *

workdir = justpath(__file__)


filedem = f"{workdir}/data/CLSA_LiDAR.tif"
fileout = f"{workdir}/test_out.tif"


class Test(unittest.TestCase):
    """
    Tests
    """
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)


    def tearDown(self):
        warnings.simplefilter("default", ResourceWarning)


    def test_raster(self):
        """
        test_raster: 
        """
        data, _, _ = GDAL2Numpy(filedem, load_nodata_as=np.nan)
        print(f"Memory read:{data.size*4 / 1024**2:.2f} MB")
        self.assertTrue(data.size>0)


    def test_s3(self):
        """
        test_save: 
        """
        filedem = "s3://saferplaces.co/test/lidar_rimini_building_2.tif"
        data, _, prj = GDAL2Numpy(filedem, load_nodata_as=np.nan)
        print(prj)
        self.assertTrue(data.size>0)

   
    def test_vsicurl(self):
        """
        test_save: 
        """
        filedem = "https://s3.us-east-1.amazonaws.com/saferplaces.co/test/lidar_rimini_building_2.tif"
        data, _, _ = GDAL2Numpy(filedem, load_nodata_as=np.nan)
        self.assertTrue(data.size>0)


if __name__ == '__main__':
    unittest.main()



