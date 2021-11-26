from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import shapefile
import random
from datetime import datetime
from multiprocessing import Process
import pandas as pd
from tqdm import tqdm
import os

'''

Calculate catchment-scale meteorological time series from the interpolated raster with multiprocessing

The directory should be structured as follows:
├── shapefiles
|   ├── basin_0000.shp
|   ├── basin_0001.shp
├── data
|   ├── interpolated_raster
|   |   ├── 20-20时累计降水量
|   |   |   ├── 1954-1-1-20-20时累计降水量
|   |   |   ├── 1954-1-2-20-20时累计降水量
|   ├── 大型蒸发量
|   |   |   ├── ...
├── output

'''

# interpolated raster extent, no need to change
lat_start = 15
lat_end = 55
lon_start = 70
lon_end = 140
degree = 0.1

xi = np.round(np.arange(lat_start, lat_end, degree), 1)
yi = np.round(np.arange(lon_start, lon_end, degree), 1)


def load_list(path):
    score = []
    with open(path, "r") as f:
        for line in f:
            score.append(line.strip())
    return score


def load_json(path):
    import json
    with open(path, "r", encoding='utf8') as read_file:
        data = json.load(read_file)
    return data


def absoluteFilePaths(directory):
    import os
    def absoluteFilePaths(directory):
        for dirpath, _, filenames in os.walk(directory):
            for f in filenames:
                yield os.path.abspath(os.path.join(dirpath, f))

    return list(absoluteFilePaths(directory))


def read_tif(tif_file):
    from PIL import Image
    im = Image.open(tif_file)
    return np.array(im)


def shp_points(shp):
    import shapefile
    return shapefile.Reader(shp).shape(0).points


def tif_shp_index_mean(tif, points, num_sample):
    arr = read_tif(tif)
    if len(points) > num_sample:
        points = random.sample(points, num_sample)
    values = []
    for sample in points:
        y, x = sample
        x_index = np.where(xi == x)
        y_index = np.where(yi == y)
        values.append(arr[x_index, y_index])
    return np.mean(values)


def one_shp(name, num_sample, tifs, shp_points_d, outdir):
    res = {}
    for tif in tifs:
        if '降水量' in tif:
            year, month, day = tuple(tif.split('\\')[-1].split('.')[0].split('-'))[:3]
            var = '20-20时累计降水量'
        else:
            year, month, day, var = tuple(tif.split('\\')[-1].split('.')[0].split('-'))
        year = int(year)
        month = int(month)
        day = int(day)

        if datetime(year, month, day) not in res:
            res[datetime(year, month, day)] = {}
        res[datetime(year, month, day)][var] = tif_shp_index_mean(tif, shp_points_d[name], num_sample=num_sample)
    # if not os.path.isdir(f'{outdir}/{name}'):
    #     os.mkdir(f'{outdir}/{name}')
    pd.DataFrame(res).T.sort_index().to_excel(f'{outdir}/{name}.xlsx')


def multi_shp(names, num_sample, tifs, shp_points_d, outdir):
    for name in tqdm(names):
        one_shp(name, num_sample=num_sample, tifs=tifs, shp_points_d=shp_points_d, outdir=outdir)


def main():
    folder_shp = './shapefiles'
    folder_raster = './output/raster_meteorological'
    outdir = './output/catchment_meteorological'

    shps = [x for x in absoluteFilePaths(folder_shp) if x.endswith('.shp')]
    tifs = absoluteFilePaths(folder_raster)
    shp_points_d = {}
    for shp in shps:
        name = os.path.basename(shp).split('_')[-1].split('.')[0]
        points = list(np.round(shp_points(shp), 1))
        shp_points_d[name] = points
    names = list(shp_points_d.keys())

    proc = []

    num_threads = 8
    num_sample = 100000
    for i in range(num_threads):
        s, e = (len(names) // num_threads + 1) * i, (len(names) // num_threads + 1) * (i + 1)
        batch_names = names[s:e]
        p = Process(target=multi_shp, args=(batch_names, num_sample, tifs, shp_points_d, outdir))
        proc.append(p)

    for p in proc:
        p.start()

    for p in proc:
        p.join()


if __name__ == '__main__':
    main()
