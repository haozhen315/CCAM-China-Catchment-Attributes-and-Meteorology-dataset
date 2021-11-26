import subprocess

import numpy as np
import netCDF4
from osgeo import gdal, osr
import cv2
import xarray

from utils import *

'''
Calculate catchment aggregated soil characteristics.

The directory should be structured as follows:
├── soil.py
├── shapefiles
|   ├── basin_0000.shp
|   ├── basin_0001.shp
├── data
|   ├── soil_souce_data
|   |   ├── tif
|   |   ├── netcdf
|   |   ├── binary

### Data sources ###

1. Dai, Y., Q. Xin, N. Wei, Y. Zhang, W. Shangguan, H. Yuan, S. Zhang, S. Liu, and X. Lu (2019b), 
A global high-resolution dataset of soil hydraulic and thermal properties for land surface modeling, 
J. Adv. Model. Earth System, accepted.

Download link:
http://globalchange.bnu.edu.cn/research/soil5.jsp (binary)
We used the column "Data for SoilGrids" for producing the BACC dataset

2. Shangguan, W., Y. Dai, B. Liu, A. Zhu, Q. Duan, L. Wu, D. Ji, A. Ye, H. Yuan, Q. Zhang, D. Chen, M. Chen, 
J. Chu, Y. Dou, J. Guo, H. Li, J. Li, L. Liang, X. Liang, H. Liu, S. Liu, C. Miao, and Y. Zhang (2013), 
A China Dataset of Soil Properties for Land Surface Modeling, Journal of Advances in Modeling Earth Systems, 
5: 212-224.

Download link:
http://globalchange.bnu.edu.cn/research/soil2 (netCDF)

3. Hengl T, Mendes de Jesus J, Heuvelink GBM, Ruiperez Gonzalez M, Kilibarda M, Blagotić A, et al. (2017) 
SoilGrids250m: Global gridded soil information based on machine learning. PLoS ONE 12(2): e0169748. 
doi:10.1371/journal.pone.0169748

Download link:
https://files.isric.org/soilgrids/former/2017-03-10/data/ 

List of descriptions:
https://github.com/ISRICWorldSoil/SoilGrids250m/blob/master/grids/models/META_GEOTIFF_1B.csv


### Instruction ###

The soil data comes from different data sources. The original data of SoilGrids is in GeoTIFF format, 
while other data sources first need to be converted to GeoTIFF and then zonal stats are performed to obtain 
the basin average.

When you have prepared the relevant data, this code can run normally "without modification". However, since there are 
so many soil types data, users may want to deal with data types that are not included in the source 
data set. Therefore, the following steps introduces a general method of processing soil source data into a watershed 
area average using this python script:
(1) Download the attribute source files that you need, put them in the corresponding folders according to their types; 
(2) For nc file, you will need to find the variable name using function nc_var_description for extracting array from nc 
and then converting the array to tif, specify the variable name in L179, you may need to create a mapping dictionary 
from file names to variable names if you are processing multiple variables simultaneously;
(3) You will need to specify the valid value ranges for the converted tif files in L196, similarly, a file_name -> value 
range mapping might be needed if you are processing multiple variable simultaneously.

'''


def read_nc_data(ncfile: str):
    """
    Read .nc data and return two dictionaries. The first dictionary contains variable names and variables,
    and the second dictionary contains descriptions of the variable names

    Parameters
    ----------
    ncfile: The path of the .nc file

    Returns
    -------
    (dict1, dict2)

    dict1: {variable name: variable}
    dict2: {variable name: description}
    """
    try:
        with netCDF4.Dataset(ncfile) as file:
            file.set_auto_mask(False)
            variables = {x: file[x][()] for x in file.variables}
        with xarray.open_dataset(ncfile) as file:
            longnames = {}
            for x in file.variables:
                if 'longname' in file[x].attrs:
                    longnames[x] = file[x].longname
                else:
                    longnames[x] = file[x].long_name
            units = {}
            for x in file.variables:
                if 'units' in file[x].attrs:
                    units[x] = file[x].units
        return variables, longnames, units

    except IOError:
        print(f"File corrupted: {ncfile}")


def nc_var_description(ncfile: str):
    return read_nc_data(ncfile)[1]


def tif_from_array(mag_grid: np.array, output_file: str):
    '''
    For data from:
    Dai, Y., Q. Xin, N. Wei, Y. Zhang, W. Shangguan, H. Yuan, S. Zhang, S. Liu, and X. Lu (2019b),
    A global high-resolution dataset of soil hydraulic and thermal properties for land surface modeling,
    J. Adv. Model. Earth System, accepted.
    '''
    lats = np.arange(-90, 90, 0.08333333333333333)
    lons = np.arange(-180, 180, 0.08333333333333333)
    xres = lons[1] - lons[0]
    yres = lats[1] - lats[0]
    ysize = len(lats)
    xsize = len(lons)
    ulx = -180
    uly = -90
    driver = gdal.GetDriverByName('GTiff')
    ds = driver.Create(output_file, xsize, ysize, 1, gdal.GDT_Float32)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetProjection(srs.ExportToWkt())
    gt = [ulx, xres, 0, uly, 0, yres]
    ds.SetGeoTransform(gt)
    outband = ds.GetRasterBand(1)
    outband.SetStatistics(np.min(mag_grid), np.max(mag_grid), np.average(mag_grid), np.std(mag_grid))
    outband.WriteArray(mag_grid)
    ds = None


def tif_from_nc(ncfile: str, variable_key: str, output_file: str):
    """ Convert a variable of the .nc file to a tif file.

    netCDF source data:
    Shangguan, W., Y. Dai, B. Liu, A. Zhu, Q. Duan, L. Wu, D. Ji, A. Ye, H. Yuan, Q. Zhang, D. Chen, M. Chen,
    J. Chu, Y. Dou, J. Guo, H. Li, J. Li, L. Liang, X. Liang, H. Liu, S. Liu, C. Miao, and Y. Zhang (2013),
    A China Dataset of Soil Properties for Land Surface Modeling, Journal of Advances in Modeling Earth Systems,
    5: 212-224.

    Parameters
    ----------
    ncfile: The path of the .nc file
    variable_key: The variable name of the .nc file to be written to the tif file
    output_file: path of the output tif file
    """

    variables = read_nc_data(ncfile)[0]
    desc = read_nc_data(ncfile)[1]
    target_variable = variables[variable_key]
    if len(target_variable.shape) == 3:
        target_variable = target_variable[0]  # Only count the first layer
    mag_grid = np.float64(target_variable)
    lats = np.arange(18.004168, 53.995834, 0.008331404166666667)
    lons = np.arange(73.004166, 135.99583, 0.0083333)

    xres = lons[1] - lons[0]
    yres = lats[1] - lats[0]
    ysize = len(lats)
    xsize = len(lons)
    ulx = 73.004166
    uly = 18.004168
    driver = gdal.GetDriverByName('GTiff')
    ds = driver.Create(output_file, xsize, ysize, 1, gdal.GDT_Float32)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetProjection(srs.ExportToWkt())
    gt = [ulx, xres, 0, uly, 0, yres]
    ds.SetGeoTransform(gt)
    outband = ds.GetRasterBand(1)
    outband.SetStatistics(np.min(mag_grid), np.max(mag_grid), np.average(mag_grid), np.std(mag_grid))
    outband.WriteArray(mag_grid)
    ds = None


def binary2tif(file, out_path):
    '''
    :param file: /path/to/binary
    :param out_path: out/tif/path
    '''
    data = np.fromfile(file, dtype=np.float64).reshape((21600, 43200))
    data[data == data.min()] = -9999
    tif_from_array(cv2.flip(np.rot90(cv2.resize(data, (43200 // 10, 21600 // 10)), 2), 1), out_path)


if __name__ == '__main__':
    print('-> soil')

    # binary
    print('-> binary to tif')
    files = absolute_file_paths('./data/soil_source_data/binary')
    for file in tqdm(files):
        if '.' in file:
            continue
        if file + '.tif' in files:
            continue
        binary2tif(file, file + '.tif')

    # netcdf
    print('-> nc to tif')
    filename_varname_mapping = {
        'PDEP.nc': 'PDEP1',
        'SOM.nc': 'SOM',
        'GRAV.nc': 'GRAV',
        'POR.nc': 'POR',
        'SA.nc': 'SA',
        'CL.nc': 'CL',
        'SI.nc': 'SI'
    }
    files = absolute_file_paths('./data/soil_source_data/netcdf')
    for file in tqdm(files):
        # print(file)
        output_path = file.replace('.nc', '.tif')
        if output_path in files:
            continue
        variable_name = filename_varname_mapping[os.path.basename(file)]
        tif_from_nc(file, variable_name, output_path)

    # zonal stats
    print('-> zonal stats')
    res = {}
    files = [x for x in absolute_file_paths('./data/soil_source_data') if x.endswith('.tif')]
    shps = [x for x in absolute_file_paths('./shapefiles') if x.endswith('.shp')]
    for file in files:
        try:
            for shp in shps:
                if not shp_id(shp) in res:
                    res[shp_id(shp)] = {}
                var_name = os.path.basename(file).split('.')[0].replace('_downscaled', '')
                res[shp_id(shp)][var_name] = zonal_stats_singletif(file, shp, valid_min=0, valid_max=None)
        except Exception as e:
            print(e)
            continue
    res = pd.DataFrame(res).T
    res.columns = [x.lower().replace(' ', '_') for x in res.columns]
    res.reset_index().rename(columns={'index': 'basin_id'}).to_excel('./output/soil.xlsx')
