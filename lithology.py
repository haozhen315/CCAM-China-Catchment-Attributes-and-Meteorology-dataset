import numpy as np
import pandas as pd
from tqdm import tqdm
import re
import os
import fiona
import rasterio
import rasterio.mask

'''

Catchment-scale zonal stats of lithology based on the GliM data set.
Reference: Hartmann, J., Moosdorf, N., 2012. The new global lithological map database GLiM: A representation of rock 
properties at the Earth surface. Geochemistry, Geophysics, Geosystems, 13. DOI: 10.1029/2012GC004370

Requirement: 
(1) processed_glim.tif: Converted GliM Raster. There are two ways to obtain this file, first is to download our preprocessed 
https://zenodo.org/record/5137288/files/9_code_data.zip?download=1

Alternatively, you can download the original GLiM dataset and convert it to raster:
1. Download the glim dataset: https://www.dropbox.com/s/9vuowtebp9f1iud/LiMW_GIS%202015.gdb.zip?dl=0; 
2. Import the dataset to ArcMap/QGis;
3. Export GLiM to GeoTIFF format (we specify the cell size as 0.024424875);
4. Reproject the exported GLiM to EPSG: 4326 using the following script:
-> from utils import *
-> reproject_tif(path_glim_tif, path_output, out_crc='EPSG:4326')

(2) glim_cate_number_mapping.csv: mapping number to lithology category
(3) glim_name_short_long.txt: mapping short name to long name of lithology categories

The directory should be structured as follows:
├── glim.py
├── shapefiles
|   ├── basin_0000.shp
|   ├── basin_0001.shp
├── data
|   ├── processed_glim.tif
|   ├── glim_cate_number_mapping.csv
|   ├── glim_name_short_long.txt


'''


def absolute_file_paths(directory):
    def nest(nest_directory):
        for path, _, filenames in os.walk(nest_directory):
            for f in filenames:
                yield os.path.abspath(os.path.join(path, f))

    return list(nest(directory))


def shp_id(shpfile: str):
    '''

    :param shpfile: shapefile path e.g. ./0000.shp
    :return: shapefile id e.g. 0000
    '''
    return re.findall(r'[\d]+', shpfile)[-1]


def extract_raster(raster: str, shape_file: str, output_file=None, nodata=-9999):
    with fiona.open(shape_file, "r") as shapefile:
        shapes = [feature["geometry"] for feature in shapefile]
    with rasterio.open(raster) as src:
        out_image, out_transform = rasterio.mask.mask(src, shapes, nodata=nodata, crop=True)
        out_meta = src.meta
    if output_file is None:
        return out_image
    else:
        out_meta.update({"driver": "GTiff",
                         "height": out_image.shape[1],
                         "width": out_image.shape[2],
                         "transform": out_transform})
        with rasterio.open(output_file, "w", **out_meta) as dest:
            dest.write(out_image)
        return out_image


class Glim():
    def __init__(self, glim_raster_tif: str, glim_cate_number_mapping_file: str, short2long_name_txt: str,
                 nan_value=65535):
        self.glim_raster_tif = glim_raster_tif
        self.short2long_dataframe = pd.read_table(short2long_name_txt, sep=',')
        self.glim_mapping_dataframe = pd.read_table(glim_cate_number_mapping_file, sep=',')
        self.glim_mapping_dataframe['xx'] = [s[:2] for s in self.glim_mapping_dataframe['Litho']]
        self.nan_value = nan_value

    def glim_number2geol_mapping(self, value: int):
        return self.glim_mapping_dataframe[self.glim_mapping_dataframe['Value'] == value]['Litho'].values[0][:2]

    def glim_geol2number_mapping(self, geol: str):
        return self.glim_mapping_dataframe[self.glim_mapping_dataframe['xx'] == geol]['Value'].values

    def short2long_name(self, short_name: str):
        return self.short2long_dataframe[self.short2long_dataframe['short'] == short_name]['long'].values[0]

    def extract_basin_attributes_glim_all(self, shape_file: str) -> dict:
        res = extract_raster(raster=self.glim_raster_tif, shape_file=shape_file, output_file=None)
        res = res[res < 1000].flatten()
        res_list = res[res != self.nan_value].flatten().tolist()

        res_str = [self.glim_number2geol_mapping(number) for number in res_list]

        geol_class, count = np.unique(res_str, return_counts=True)

        res = {}
        for name, c in zip(geol_class, count):
            res[name] = c / np.sum(count)

        return res

    def extract_basin_attributes_glim(self, shape_file: str) -> dict:
        res = extract_raster(raster=self.glim_raster_tif, shape_file=shape_file, output_file=None)
        res = res[res < 1000].flatten()
        res_list = res[res != self.nan_value].flatten().tolist()

        res_str = [self.glim_number2geol_mapping(number) for number in res_list]

        geol_class, count = np.unique(res_str, return_counts=True)

        geol_class_rank = [x for _, x in sorted(zip(count, geol_class), reverse=True)]
        if len(geol_class_rank) == 0:
            return {'geol_class_1st: ': None,
                    'geol_class_1st_frac: ': None,
                    'geol_class_2nd: ': None,
                    'geol_class_2nd_frac: ': None,
                    'carb_rocks_frac: ': None}
        geol_class_1st = geol_class_rank[0]
        geol_class_1st_count = count[geol_class == geol_class_1st]
        geol_class_1st_frac = (geol_class_1st_count / np.sum(count))[0]
        if len(geol_class_rank) > 1:
            geol_class_2nd = geol_class_rank[1]
            geol_class_2nd_count = count[geol_class == geol_class_2nd]
            geol_class_2nd_frac = (geol_class_2nd_count / np.sum(count))[0]
        else:
            geol_class_2nd = None
            geol_class_2nd_frac = 0

        carb_rocks_count = count[geol_class == 'sc']
        if len(carb_rocks_count) == 0:
            carb_rocks_frac = 0
        else:
            carb_rocks_frac = (carb_rocks_count / np.sum(count))[0]

        return {'geol_class_1st: ': geol_class_1st,
                'geol_class_1st_frac: ': geol_class_1st_frac,
                'geol_class_2nd: ': geol_class_2nd,
                'geol_class_2nd_frac: ': geol_class_2nd_frac,
                'carb_rocks_frac: ': carb_rocks_frac}


if __name__ == '__main__':
    print('-> calculating lithology')

    glim_raster_tif = "data/processed_glim.tif"
    glim_cate_number_mapping_file = "data/glim_cate_number_mapping.csv"
    short2long_name_txt = "data/glim_name_short_long.txt"
    nan_value = 65535

    glimer = Glim(glim_raster_tif=glim_raster_tif, glim_cate_number_mapping_file=glim_cate_number_mapping_file,
                  short2long_name_txt=short2long_name_txt, nan_value=nan_value)

    res = {}
    for shape_file in tqdm([file for file in absolute_file_paths('./shapefiles') if file.endswith('.shp')]):
        res[shp_id(shape_file)] = glimer.extract_basin_attributes_glim_all(shape_file=shape_file)
    res = pd.DataFrame(res).T.reset_index().rename(columns={'index': 'basin_id'})
    res.to_excel('output/glim.xlsx', index=None)
