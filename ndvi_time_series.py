import os, datetime, subprocess, shutil, re, sys
from utils import *

'''


Calculate catchment-scale NDVI/LAI time-series based on MODIS products

Reference:
https://lpdaac.usgs.gov/products/mcd15a3hv006/
https://lpdaac.usgs.gov/products/mod13q1v006/

The directory should be structured as follows:
├── ndvi_series.py/lai_series.py
├── shapefiles
|   ├── basin_0000.shp
|   ├── basin_0001.shp
├── data
|   ├── MOD13Q1/MCD15A3H
|   |   ├── MOD13Q1.A2002185.h22v04.006.2015149102803.hdf
|   |   ├── MOD13Q1.A2002186.h22v04.006.2015149102803.hdf
|   |   ├── MOD13Q1.A2002187.h22v04.006.2015149102803.hdf
|   |   ├── MOD13Q1.A2002188.h22v04.006.2015149102803.hdf
├── output


'''


def get_qualified_hdf_files_from_folder(folder: str, modis_product: str, zones: list):
    '''

    :param folder: modis hdfs folder
    :param modis_product: modis product id: 'MCD15A3H' for LAI; 'MOD13Q1' for NDVI
    :param zones: modis tiles
                  https://lpdaac.usgs.gov/data/get-started-data/collection-overview/missions/modis-overview/
                  e.g. [h25v06, h25v07]
    :return: qualified hdfs list
    '''
    if zones == 'all':
        res = [file for file in absolute_file_paths(folder) if file.endswith('.hdf')]
    else:
        res = [file for file in absolute_file_paths(folder) if
               file.endswith('.hdf') and (get_info_from_modis_hdf(file)['zones'] in zones)]
    for file in res:
        assert os.path.basename(file).split('.')[0] == modis_product
    return res


def get_info_from_modis_hdf(file_path) -> dict:
    """
    file_path: 'MCD15A3H.A2018017.h25v06.006.2018023210623.hdf' or absolute path

    > get_info_from_modis_hdf('MCD15A3H.A2018017.h25v06.006.2018023210623.hdf')
    """
    res = {}
    date = os.path.basename(file_path).split('.')[1]
    year = int(date[1:-3])
    day_of_year = int(date[-3:])
    res['date'] = datetime.datetime(year, 1, 1) + datetime.timedelta(day_of_year - 1)
    res['product'] = os.path.basename(file_path).split('.')[0]
    res['zones'] = os.path.basename(file_path).split('.')[2]
    return res


def get_info_from_modis_tif(file_path) -> dict:
    """
    file_path: "MCD12Q1.A2018001.h25v04.006.2019200013451_08.tif" or absolute path

    > get_info_from_modis_tif(r"MCD12Q1.A2018001.h25v04.006.2019200013451_08.tif")
    """
    res = {}
    date = os.path.basename(file_path).split('.')[1]
    year = int(date[1:-3])
    day_of_year = int(date[-3:])
    res['date'] = datetime.datetime(year, 1, 1) + datetime.timedelta(day_of_year - 1)
    res['product'] = os.path.basename(file_path).split('.')[0]
    res['zones'] = os.path.basename(file_path).split('.')[2]
    res['feature'] = re.findall('_(\d+)', file_path)[-1]
    return res


def group_hdf_files_by_date(hdf_files: list):
    '''

    :param hdf_files: hdf files
    :return: group hdf files by dare
    '''
    dates = [get_info_from_modis_hdf(file)['date'] for file in hdf_files]
    unique_dates = np.unique(dates)
    res = {}
    for date in unique_dates:
        res[date] = [file for file in hdf_files if date == get_info_from_modis_hdf(file)['date']]
    return res


def hdf_to_tif(hdf_file: str, output_dir: str):
    '''

    :param hdf_file: hdf file
    :param output_dir: convert hdf file to tifs
    :return:
    '''
    cwd = os.getcwd()
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    os.chdir(output_dir)
    name = os.path.basename(hdf_file)[:-4] + '.tif'
    command = f'gdal_translate -sds -of GTiff {os.path.basename(hdf_file)} {name}'
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    os.chdir(cwd)
    return name


def group_tif_files_by_date_feature(files: list):
    '''

    :param files: tif files
    :return: group tifs by date and feature
    '''
    dates = [get_info_from_modis_tif(file)['date'] for file in files]
    unique_dates = np.unique(dates)
    features = [get_info_from_modis_tif(file)['feature'] for file in files]
    unique_features = np.unique(features)
    res = {}
    for date in unique_dates:
        res[date] = {}
        for feature in unique_features:
            res[date][feature] = [file for file in files if date == get_info_from_modis_tif(file)['date'] and
                                  feature == get_info_from_modis_tif(file)['feature']]
    return res, unique_features


def get_84_tifs(folder: str):
    '''

    :param folder: tifs folder
    :return: return only tifs in wgs84
    '''
    files = absolute_file_paths(folder)
    return [file for file in files if 'tif84' in file]


def zonal_stats(tif_file: str, shape_file: str, valid_min, valid_max) -> dict:
    '''

    :param tif_file: tif file path
    :param shape_file: shp file path
    :param valid_min: NDVI: [-2000, 10000]; LAI: [0, 100]
    :param valid_max: NDVI: [-2000, 10000]; LAI: [0, 100]
    :return:
    '''
    res = extract_raster_by_shape_file(tif_file, shape_file).flatten()
    res[res > valid_max] = -9999
    res[res < valid_min] = -9999
    res = res[res != -9999]
    res = res[~np.isnan(res)]
    if len(res) > 0:
        return {'mean': np.mean(res),
                'max': np.max(res), 'min': np.min(res)}
    else:
        return {'mean': 0, 'max': 0, 'min': 0}


def clear_dir(folder: str):
    '''

    :param folder: folder path
    :return: None
    '''
    shutil.rmtree(folder)
    print(f'-> {folder} cleared')


class Modis():
    def __init__(self, hdf_folder, working_folder, tmp_folder, product, zones):
        self.hdf_folder = hdf_folder
        self.working_folder = working_folder
        self.tmp_folder = tmp_folder
        self.product = product
        self.zones = zones
        self.merged_tif_names = []
        print('tmp_folder: ', tmp_folder)
        print('product: ', product)
        print('zones: ', zones)
        print('---------------------')

    def get_merged_tifs(self, merged_tifs_folder: str, feature_name: str, feature_index: str) -> pd.DataFrame:
        print('feature_index: ', feature_index)
        print('feature_name: ', feature_name)
        print('----------------------')
        print('clear the tmp folder, if not exists, creat one')
        files = absolute_file_paths(self.tmp_folder)
        # files = get_qualified_hdf_files_from_folder(self.hdf_folder, self.product, self.zones)
        print('convert hdf to tif...')
        for file in tqdm(files, position=0, leave=True, file=sys.stdout):
            hdf_to_tif(file, tmp_dir)
        print('downscale tif...')
        for file in absolute_file_paths(tmp_dir):
            if file.endswith('.tif'):
                gdal_downsample_tif(file, tmp_dir, 50)
        print('reproject tif to wgs84')
        tifs = [file for file in absolute_file_paths(tmp_dir) if
                (file.endswith('.tif') and '_downscaled' in file)]
        for file in tqdm(tifs, position=0, leave=True, file=sys.stdout):
            name = file + '84.tif'
            reproject_tif(file, name)
        tifs_84 = get_84_tifs(tmp_dir)
        groups, unique_features = group_tif_files_by_date_feature(tifs_84)
        print('merge tif...')
        if not os.path.isdir(merged_tifs_folder):
            os.makedirs(merged_tifs_folder)
        merged_tifs = {}
        for date in tqdm(groups.keys(), position=0, leave=True, file=sys.stdout):
            merged_tifs[date] = {}
            merged_tif_name = f'{self.product}-{date.year}.{date.month}.{date.day}-{feature_name}-merged.tif'
            merged_tif_name = os.path.join(merged_tifs_folder, merged_tif_name)
            merge_tifs(groups[date][feature_index], merged_tif_name)
            merged_tifs[date][feature_name] = merged_tif_name
            self.merged_tif_names.append(merged_tif_name)
        return pd.DataFrame(merged_tifs).T

    def zonal_stats_by_shapefile(self, shapefile: str, valid_min=-2000, valid_max=10000):
        res = {}
        for file in self.merged_tif_names:
            date = file.split('-')[1]
            year = int(date.split('.')[0])
            month = int(date.split('.')[1])
            day = int(date.split('.')[2])
            date = datetime.datetime(year, month, day)
            feature = file.split('-')[2]
            stats = zonal_stats(tif_file=file, shape_file=shapefile, valid_min=valid_min, valid_max=valid_max)['mean']
            res[date] = {feature: stats}
        return stats

    def clear_tmp(self):
        shutil.rmtree(tmp_dir)


def get_hdf_product(file):
    '''

    :param file: e.g. ./MCD15A3H.A2002185.h23v03.006.2015149105852.hdf
    :return: 'MCD15A3H'
    '''
    return os.path.basename(file).split('.')[0]


def get_hdf_date(file):
    '''

    :param file: e.g. ./MCD15A3H.A2002185.h23v03.006.2015149105852.hdf
    :return: datetime.datetime(2002, M, D)
    '''
    tmp = os.path.basename(file).split('.')[1]
    year = int(tmp[1:5])
    days = int(tmp[5:])
    return datetime.datetime(year, 1, 1) + datetime.timedelta(days - 1)


def summary_year(year, data_root, out_dir, root_dir):
    '''

    :param year: specify the year to calculate
    :param data_root: modis lai/ndvi data root dir, e.g. ./MOD13Q1
    :param out_dir: output dir, e.g. ./output/ndvi
    :param root_dir: data processing root dir
    :return: xlsx files
    '''
    start = datetime.datetime(year, 1, 1)
    end = datetime.datetime(year, 12, 31)

    if os.path.exists(tmp_dir):
        clear_dir(tmp_dir)
        os.makedirs(tmp_dir)
    else:
        os.makedirs(tmp_dir)

    files = absolute_file_paths(data_root)
    files = [file for file in files if file.endswith('.hdf')]

    res = {}
    for date in tqdm(np.unique([get_hdf_date(file) for file in files])):
        if not start <= date <= end:
            continue

        print(date, '...')
        for file in files:
            if get_hdf_date(file) == date:
                shutil.copyfile(file, f'{tmp_dir}/{os.path.basename(file)}')

        modis = Modis(hdf_folder=tmp_dir,
                      working_folder=root_dir,
                      tmp_folder=tmp_dir,
                      product='MOD13Q1',
                      zones='all')
        modis.get_merged_tifs(merged_tifs_folder=tmp_dir,
                              feature_name='NDVI',
                              feature_index='1')

        for shape_file in [file for file in absolute_file_paths(shp_dir) if file.endswith('.shp')]:
            id = shp_id(shape_file)
            tmp_res = modis.zonal_stats_by_shapefile(shapefile=shape_file, valid_min=-2000, valid_max=10000)

            if id not in res:
                res[id] = {}
            res[id][date] = tmp_res

        clear_dir(tmp_dir)
        os.makedirs(tmp_dir)

    final_res = {}
    for key in res:
        df = pd.DataFrame(res[key], index=[0]).T
        df = df.rename(columns={0: 'ndvi'})
        df.to_excel(os.path.join(out_dir, str(year), f'{key}.xlsx'))
        final_res[key] = [df['ndvi'].max(), df['ndvi'].min(), df['ndvi'].mean()]
    return final_res


shp_dir = './shapefiles'
tmp_dir = './tmp'
if __name__ == '__main__':
    print('-> ndvi time series')
    res = {}
    for year in range(2002, 2003):
        tmp_res = summary_year(year, data_root='./MODIS/MOD13Q1 ', out_dir='./output/ndvi', root_dir='./')
        for key in tmp_res:
            if not key in res:
                res[key] = []
            res[key].append(tmp_res[key])
    for key in res:
        res[key] = np.mean(np.array(res[key]), axis=0)
    res = pd.DataFrame(res).T
    res.columns = ['max', 'min', 'mean']
    res = res.reset_index().rename(columns={'index': 'basin_id'})
    res.to_excel('./output/ndvi.xlsx', index=None)
