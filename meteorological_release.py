import pandas as pd
import shapefile
from shapely.geometry import Point, Polygon
import numpy as np
import os


def absoluteFilePaths(directory):
    import os
    def absoluteFilePaths(directory):
        for dirpath, _, filenames in os.walk(directory):
            for f in filenames:
                yield os.path.abspath(os.path.join(dirpath, f))

    return list(absoluteFilePaths(directory))


def area_overlap(shp, cn_shps):
    res = {}
    poly = Polygon(shapefile.Reader(shp).shapeRecord(0).shape.points).buffer(0)
    for shp_cn in cn_shps:
        cn_poly = Polygon(shapefile.Reader(shp_cn).shapeRecord(0).shape.points).buffer(0)
        if cn_poly.is_valid and cn_poly.intersection(poly).area != 0:
            id_cn = shp_cn.split('_')[-1].split('.')[0]
            res[id_cn] = cn_poly.intersection(poly).area
    return res


def shp_climate(shp, out_path, cn_shps_folder, cn_climate_folder):
    cn_shps = [x for x in absoluteFilePaths(cn_shps_folder) if x.endswith('.shp')]
    tmp_res = area_overlap(shp, cn_shps)
    res = {}
    for k, v in tmp_res.items():
        path = os.path.join(cn_climate_folder, k + '.txt')
        if os.path.isfile(path):
            res[k] = v
    v_sum = np.sum(list(res.values()))
    for k in res:
        res[k] /= v_sum

    if 'res_df' in locals():
        del res_df
    for k, v in res.items():
        path = os.path.join(cn_climate_folder, k + '.txt')
        if 'res_df' in locals():
            res_df += pd.read_csv(path).set_index('Date').sort_index() * v
        else:
            res_df = pd.read_csv(path).set_index('Date').sort_index() * v

    res_df.to_csv(out_path)
    return res_df


if __name__ == '__main__':
    cn_climate_folder = './1_meteorological'
    cn_shps_folder = './0_catchment_boundary'
    shp = './7_HydroMLYR/0_basin_boundary/0000.shp'
    res = shp_climate(shp, 'tmp.txt', cn_shps_folder, cn_climate_folder)
