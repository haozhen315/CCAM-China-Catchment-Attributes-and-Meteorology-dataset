import numpy as np
import pandas as pd
from tqdm import tqdm
from utils import *


class GLHYMPS():

    def __init__(self, permeabilit_no_permafrost_raster_tif: str, porosity_raster_tif: str, nan_value=65535):
        self.permeabilit_no_permafrost_raster_tif = permeabilit_no_permafrost_raster_tif
        self.porosity_raster_tif = porosity_raster_tif
        self.nan_value = nan_value

    def zonal_stats_glhymps(self, shape_file: str) -> dict:
        permeability = zonal_stats_singletif(tif_file=self.permeabilit_no_permafrost_raster_tif, shape_file=shape_file,
                                             valid_min=-self.nan_value, valid_max=self.nan_value)
        porosity = zonal_stats_singletif(tif_file=self.porosity_raster_tif, shape_file=shape_file,
                                         valid_min=-self.nan_value, valid_max=self.nan_value)

        return {'permeability': permeability, 'porosity': porosity}


def shp_id(shpfile: str):
    return re.findall(r'[\d]+', shpfile)[-1]


if __name__ == '__main__':
    print('-> calculating permeability and porosity')
    permeability_no_permafrost_raster_tif = r"./data/processed_permeability.tif"
    porosity_raster_tif = r'./data/processed_porosity.tif'
    nan_value = 65535

    glhympser = GLHYMPS(permeability_no_permafrost_raster_tif, porosity_raster_tif, nan_value=nan_value)

    res = {}
    for shape_file in tqdm([file for file in absolute_file_paths('./shapefiles') if file.endswith('.shp')]):
        res[shp_id(shape_file)] = glhympser.zonal_stats_glhymps(shape_file=shape_file)
    res = pd.DataFrame(res).T.reset_index().rename(columns={'index': 'basin_id'})
    res.to_excel('./output/glhymps.xlsx', index=None)
