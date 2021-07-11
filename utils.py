import os
import re
import datetime
import numpy as np
import pandas as pd
import pickle
import gdal, osr

from tqdm import tqdm
import time
import fiona
import netCDF4
from netCDF4 import Dataset
import geopandas as gpd
import rasterio
import rasterio.mask
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, Resampling
import subprocess

def geotif_from_array(array: np.array, lat_start: float, lat_end: float, lon_start: float, lon_end: float,
                      degree: float, output_file: str):
    nx, ny = array.shape
    mag_grid = np.reshape(array, (nx, ny), order='F')  # !!!
    mag_grid = np.float64(mag_grid)
    lats = np.linspace(start=lat_start, stop=lat_end, num=mag_grid.shape[0])
    lons = np.linspace(start=lon_start, stop=lon_end, num=mag_grid.shape[1])
    assert len(lats) == mag_grid.shape[0]
    assert len(lons) == mag_grid.shape[1]
    xres = lons[1] - lons[0]
    yres = lats[1] - lats[0]
    ysize = len(lats)
    xsize = len(lons)
    driver = gdal.GetDriverByName('GTiff')
    ds = driver.Create(output_file, xsize, ysize, 1, gdal.GDT_Float32)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetProjection(srs.ExportToWkt())
    gt = [lon_start, xres, 0, lat_start, 0, yres]
    ds.SetGeoTransform(gt)
    outband = ds.GetRasterBand(1)
    outband.SetStatistics(np.min(mag_grid), np.max(mag_grid), np.average(mag_grid), np.std(mag_grid))
    outband.WriteArray(mag_grid)
    ds = None


def shp_id(shpfile: str):
    return re.findall(r'[\d]+', shpfile)[-1]


def absolute_file_paths(directory):
    def nest(nest_directory):
        for path, _, filenames in os.walk(nest_directory):
            for f in filenames:
                yield os.path.abspath(os.path.join(path, f))

    return list(nest(directory))


def reproject_tif(src_tif: str, out_tif: str, out_crc='EPSG:4326'):
    with rasterio.open(src_tif) as src:
        transform, width, height = calculate_default_transform(
            src.crs, out_crc, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': out_crc,
            'transform': transform,
            'width': width,
            'height': height
        })

        with rasterio.open(out_tif, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=out_crc,
                    resampling=Resampling.nearest)


def merge_tifs(tif_files: list, outfile: str):
    src_files_to_mosaic = []
    for fp in tif_files:
        src = rasterio.open(fp)
        src_files_to_mosaic.append(src)
    mosaic, out_trans = merge(src_files_to_mosaic)
    out_meta = src.meta.copy()
    out_meta.update({"driver": "GTiff",
                     "height": mosaic.shape[1],
                     "width": mosaic.shape[2],
                     "transform": out_trans,
                     "crs": "EPSG:4326"})
    with rasterio.open(outfile, "w", **out_meta) as dest:
        dest.write(mosaic)


def extract_raster_by_shape_file(raster: str, shape_file: str, output_file=None):
    with fiona.open(shape_file, "r") as shapefile:
        shapes = [feature["geometry"] for feature in shapefile]
    with rasterio.open(raster) as src:
        out_image, out_transform = rasterio.mask.mask(src, shapes, nodata=-9999, crop=True)
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


def gdal_downsample_tif(tif_file: str, working_dir: str, percent: int):
    '''

    :param tif_file: tif file path
    :param working_dir: data processing root dir
    :param percent: downsample percent
    :return: downsampled tif
    '''
    cwd = os.getcwd()
    os.chdir(working_dir)
    ori_name = os.path.basename(tif_file)
    new_name = os.path.basename(ori_name)[:-4] + '_downscaled.tif'
    os.rename(tif_file, new_name)
    command = f'gdal_translate -outsize {percent}% GTiff {new_name} {ori_name}'
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    os.remove(ori_name)
    os.chdir(cwd)


def zonal_stats_singletif(tif_file: str, shape_file: str, valid_min=None, valid_max=None):
    res = extract_raster_by_shape_file(tif_file, shape_file).flatten()
    res = res[res != -9999]
    res = res[~np.isnan(res)]
    if valid_min is not None:
        res = res[res > valid_min]
    if valid_max is not None:
        res = res[res < valid_max]
    if len(res) > 0:
        return np.mean(res)
    else:
        return np.nan
