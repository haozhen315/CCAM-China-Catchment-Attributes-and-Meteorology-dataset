import numpy as np
from tqdm import tqdm
import pandas as pd
from utils import *

'''


Catchment-scale land cover fraction zonal stats based on the MODIS MCD12Q1 product (LC_Type1)

Reference:
https://lpdaac.usgs.gov/products/mcd12q1v006/

Requirement:
processed_igbp.tif: Converted IGBP classification in Raster. Source data: https://lpdaac.usgs.gov/products/mcd12q1v006/. 
However, MODIS data is divided into different tiles, which is inconvenient for processing. 
We have merged the MODIS product into a single TIF which can be downloaded here: 
https://zenodo.org/record/5137288/files/9_code_data.zip?download=1

The directory should be structured as follows:
├── igbp.py
├── shapefiles
|   ├── basin_0000.shp
|   ├── basin_0001.shp
├── data
|   ├── processed_igbp.tif
├── output


'''


def modis_land_cover_igbp_number2name(index: int):
    names = ['Evergreen needleleaf tree',
             'Evergreen broadleaf tree',
             'Deciduous needleleaf tree',
             'Deciduous broadleaf tree',
             'Mixed forest',
             'Closed shrubland',
             'Open shrubland',
             'Woody savanna',
             'Savanna',
             'Grassland',
             'Permanent wetland',
             'Cropland',
             'Urban and built-up land',
             'Cropland/natural vegetaion',
             'Snow and ice',
             'Barren',
             'Water bodies']
    try:
        return names[index - 1]
    except IndexError:
        return 'nan'


def modis_land_cover_igbp_name2number(name: str):
    names = ['Evergreen needleleaf tree',
             'Evergreen broadleaf tree',
             'Deciduous needleleaf tree',
             'Deciduous broadleaf tree',
             'Mixed forest',
             'Closed shrubland',
             'Open shrubland',
             'Woody savanna',
             'Savanna',
             'Grassland',
             'Permanent wetland',
             'Cropland',
             'Urban and built-up land',
             'Cropland/natural vegetaion',
             'Snow and ice',
             'Barren',
             'Water bodies']
    return names.index(name)


def igbp_stats(shapefile: str, igbp_tif: str, nan_value=255):
    names = ['Evergreen needleleaf tree',
             'Evergreen broadleaf tree',
             'Deciduous needleleaf tree',
             'Deciduous broadleaf tree',
             'Mixed forest',
             'Closed shrubland',
             'Open shrubland',
             'Woody savanna',
             'Savanna',
             'Grassland',
             'Permanent wetland',
             'Cropland',
             'Urban and built-up land',
             'Cropland/natural vegetaion',
             'Snow and ice',
             'Barren',
             'Water bodies']

    res = extract_raster_by_shape_file(raster=igbp_tif, shape_file=shapefile, output_file=None)
    res = res[res != -9999].flatten()
    res_list = res[res != nan_value].flatten().tolist()
    res_str = [modis_land_cover_igbp_number2name(number) for number in res_list]
    land_class, count = np.unique(res_str, return_counts=True)
    land_class_rank = [x for _, x in sorted(zip(count, land_class), reverse=True) if x != 'nan']

    res = {}
    for name in names:
        res[name] = 0
    for num, name in zip(count, land_class):
        if name != 'nan':
            res[name] = num / np.sum(count)

    # print('shapefile:', shapefile)
    # print(res)
    return res


if __name__ == '__main__':
    print('-> land cover')
    igbp_tif = "./data/processed_igbp.tif"
    shp_dir = './shapefiles'
    out = './output/igbp.xlsx'

    res = {}
    for shape_file in tqdm(file for file in absolute_file_paths(shp_dir) if file.endswith('.shp')):
        res[shp_id(shape_file)] = igbp_stats(shapefile=shape_file, igbp_tif=igbp_tif)
    res = pd.DataFrame(res).T
    res.columns = [x.lower().replace(' ', '_') for x in res.columns]
    res = res.reset_index().rename(columns={'index': 'basin_id'})
    res.to_excel(out, index=None)
