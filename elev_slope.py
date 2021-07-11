import re, shapefile, math
import richdem as rd
from osgeo import gdal, osr
import pandas as pd
from tqdm import tqdm
from utils import *

'''


Catchment-scale average elevation and slope calculation based on the ASTER GDEM
Reference: https://asterweb.jpl.nasa.gov/gdem.asp

Requirement:
Downloaded DEM TIFs.

The directory should be structured as follows:
├── elev_slope.py
├── shapefiles
|   ├── basin_0000.shp
|   ├── basin_0001.shp
├── data
|   ├── dems
|   |   ├── ASTGTMV003_N34E111_dem.tif
|   |   ├── ASTGTMV003_N32E110_dem.tif
|   |   ├── ASTGTMV003_N33E109_dem.tif
|   |   ├── ASTGTMV003_N34E108_dem.tif
├── output


'''


def load_N_E_from_dem_name(dem_file: str):
    ''' return lat and lon from aster dem file names '''
    N = re.findall('N(\d+)', dem_file)[0]
    E = re.findall('E(\d+)', dem_file)[0]
    return {'N': int(N), 'E': int(E)}


def shapefile_N_E(shpfile: str):
    ''' return min/max lat/lon, this is for determining the range of needed dem files '''
    sf = shapefile.Reader(shpfile)
    bbox = sf.bbox
    return {'N_min': bbox[1], 'N_max': bbox[3], 'E_min': bbox[0], 'E_max': bbox[2]}


def fetch_shapefile_needed_DEM_range(shpfile: str):
    ''' return the range of needed dem files for the given shapefile '''
    N_E = shapefile_N_E(shpfile)
    Ns = range(math.floor(N_E['N_min']), math.ceil(N_E['N_max']) + 1)
    Es = range(math.floor(N_E['E_min']), math.ceil(N_E['E_max']) + 1)
    return {'Ns': Ns, 'Es': Es}


def elev_mean(shpfile: str, dem_folder: str):
    ''' calculate mean elevation of the catchment '''
    if os.path.isfile(tmp_merged):
        os.remove(tmp_merged)
    if os.path.isfile(tmp_reprojected):
        os.remove(tmp_reprojected)
    # get needed N E range
    needed_Ns = fetch_shapefile_needed_DEM_range(shpfile)['Ns']
    needed_Es = fetch_shapefile_needed_DEM_range(shpfile)['Es']

    print(f"{os.path.basename(shpfile)}: N range: {needed_Ns}, E range: {needed_Es}")

    # get needed tifs
    files = absolute_file_paths(dem_folder)
    files = [file for file in files if file.endswith('.tif')]
    needed_tifs = []
    for file in files:
        N = load_N_E_from_dem_name(file)['N']
        E = load_N_E_from_dem_name(file)['E']
        if (N in needed_Ns) and (E in needed_Es):
            needed_tifs.append(file)
    if len(needed_tifs) < len(needed_Ns) * len(needed_Es):
        import warnings
        warnings.warn(f"DEMs may not cover the watershed completely")

    # merge tifs
    if len(needed_tifs) == 0:
        raise FileNotFoundError(f'did not find needed tifs for determining topograpy attributes | shpfile: {shpfile}')
    merge_tifs(needed_tifs, tmp_merged)
    reproject_tif(tmp_merged, tmp_reprojected)
    # zonal stats
    try:
        res = zonal_stats_singletif(tmp_reprojected, shpfile)
    except ValueError as e:
        print(e)
        print(needed_Es, needed_Ns, needed_tifs)
        return np.nan
    return res


def calculate_slope(DEM):
    ''' calculate the slope of a given dem '''
    dem_path = DEM
    shasta_dem = rd.LoadGDAL(dem_path, no_data=-128)
    slope = rd.TerrainAttribute(shasta_dem, attrib='slope_riserun')
    return np.array(slope.data)


def slope_mean(shpfile: str, dem_folder: str):
    ''' calculate the slope of a given catchment '''
    if os.path.isfile(tmp_merged):
        os.remove(tmp_merged)
    if os.path.isfile(tmp_reprojected):
        os.remove(tmp_reprojected)
    # get needed N E range
    needed_Ns = fetch_shapefile_needed_DEM_range(shpfile)['Ns']
    needed_Es = fetch_shapefile_needed_DEM_range(shpfile)['Es']

    # get needed tifs
    files = absolute_file_paths(dem_folder)
    files = [file for file in files if file.endswith('.tif')]

    needed_tifs = []
    for file in files:
        N = load_N_E_from_dem_name(file)['N']
        E = load_N_E_from_dem_name(file)['E']
        if (N in needed_Ns) and (E in needed_Es):
            needed_tifs.append(file)

    # merge tifs
    merge_tifs(needed_tifs, tmp_merged)
    reproject_tif(tmp_merged, tmp_reprojected)

    # get slope
    slope = calculate_slope(tmp_reprojected)

    # rise (m, dem) / run (degree, coordinates)
    slope = slope / 111  # 1 degree = 111km

    # get raster range
    ds = gdal.Open(tmp_reprojected)
    width = ds.RasterXSize
    height = ds.RasterYSize
    gt = ds.GetGeoTransform()
    minx = gt[0]
    miny = gt[3] + width * gt[4] + height * gt[5]
    maxx = gt[0] + width * gt[1] + height * gt[2]
    maxy = gt[3]
    ds = None

    # write slope tif
    geotif_from_array(slope, lat_start=miny, lat_end=maxy, lon_start=minx, lon_end=maxx, degree=0.1,
                      output_file=tmp_slope)

    # zonal stats
    try:
        res = zonal_stats_singletif(tmp_slope, shpfile)
    except ValueError as e:
        print(e)
        print(needed_Es, needed_Ns, needed_tifs)
        return np.nan
    return res


def main(outpath):
    res = []
    print(len([file for file in absolute_file_paths(shp_folfer) if file.endswith('.shp')]))
    shps = [file for file in absolute_file_paths(shp_folfer) if file.endswith('.shp')]
    for shpfile in tqdm(shps):
        tmp_res = {'shp_id': shp_id(shpfile), 'elev(m)': elev_mean(shpfile, dem_folder),
                   'slope(m/km)': slope_mean(shpfile, dem_folder)}
        res.append(tmp_res)
    res = pd.DataFrame(res).rename(columns={'shp_id': ''})
    res.to_excel(outpath, index=None)


if __name__ == '__main__':
    print('Calculating elev and slope')
    dem_folder = './data/dems'
    shp_folfer = './shapefiles'
    outpath = './output/elev_slope.xlsx'

    tmp_merged = 'merge_cache.tif'  # no need to change
    tmp_reprojected = 'reproject_cache.tif'  # no need to change
    tmp_slope = 'slope_cache.tif'  # no need to change
    main(outpath)

    os.remove(tmp_merged)
    os.remove(tmp_reprojected)
    os.remove(tmp_slope)
