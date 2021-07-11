from multiprocessing import Process
import calendar
from tqdm import tqdm
import os
import shutil
from scipy import spatial
import numpy as np
import pandas as pd
import scipy
import gdal
import osr
from utils import *
import datetime

'''
Interpolate site weather data to raster time series.

├── data
|   ├── SURF_CLI_CHN_MUL_DAY
|   |   ├── Data
|   |   |   ├── EVP
|   |   |   |   ├── SURF_CLI_CHN_MUL_DAY-EVP-13240-195101.TXT
|   |   |   ├── GST
|   |   |   |   ├── ...
|   |   |   ├── WIN
|   |   |   |   ├── ...

Steps:
1. Download the situ observations meteorological data (access permission needed): https://data.cma.cn/data/cdcdetail/dataCode/SURF_CLI_CHN_MUL_DAY_V3.0.html
2. Run this code. The interpolation range and resolution can be modified in L418-L422. 
Interpolation can take hours to run.
'''


def clear_folder(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


def absoluteFilePaths(directory):
    import os
    def absoluteFilePaths(directory):
        for dirpath, _, filenames in os.walk(directory):
            for f in filenames:
                yield os.path.abspath(os.path.join(dirpath, f))

    return list(absoluteFilePaths(directory))


def datetime2str(date, sep='-'):
    '''

    :param date: datetime.datetime
    :param sep: separator
    :return:
    '''
    year = date.year
    month = date.month
    day = date.day
    return f'{year}{sep}{month}{sep}{day}'


def get_date_range_from_txt(txtfile: str):
    '''

    Parameters
    ----------
    txtfile e.g. D:\DataSet\SURF_CLI_CHN_MUL_DAY\Data\EVP\SURF_CLI_CHN_MUL_DAY-EVP-13240-199601.TXT

    Returns
    -------
    list
        e.g. ['2000-2-24', '2000-2-5', '2000-2-14', '2000-2-10', '2000-2-21'...]
    '''
    date = txtfile.split('-')[-1][:6]
    year = int(date[:4])
    month = int(date[4:])
    num_days = calendar.monthrange(year, month)[1]
    days = [datetime.datetime(year, month, day) for day in range(1, num_days + 1)]
    return [remove_date_zeros(x) for x in days]


def remove_date_zeros(date):
    date = str(date)
    year = int(date.split('-')[0])
    month = int(date.split('-')[1])
    day = int(date.split('-')[2][:2])
    return str(year) + '-' + str(month) + '-' + str(day)


def geotif_from_array(array: np.array, lat_start: float, lat_end: float, lon_start: float, lon_end: float,
                      degree: float, output_file: str):
    """
    Write a numpy.array to a GeoTIFF file with location information, using the WGS84 (EPSG: 4326) coordinate system by default

    array: data to be written to GeoTIFF
    lat_start: minimum latitude
    lat_end: maximum latitude
    lon_start: minimum longitude
    lon_end: maximum longitude
    degree: output raster unit size (unit: degree)
    output_file: output GeoTIFF file path
    """
    mag_grid = np.float64(array)
    num_v = mag_grid.shape[0]
    num_h = mag_grid.shape[1]
    lats = np.linspace(lat_start, lat_end, num_v)
    lons = np.linspace(lon_start, lon_end, num_h)
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


def idw_interpolation(x: np.array, y: np.array, z: np.array, lat_start: float, lat_end: float, lon_start: float,
                      lon_end: float, degree: float, k: int = 12, p: int = 12, reshape_order: str = 'F'):
    """
    x: site longitude
    y: site latitude
    z: site value
    k: Number of neighbors in inverse distance weighting method, default is 12
    p: Control the weight of the station with a long distance in the interpolation, negative correlation
    lat/lon_start/end: ​​maximum [minimum] latitude [longitude]
    degree: output raster unit size (unit: degree)
    reshape_order: order of reshaping, no need to change
    """
    station_points = np.stack([x, y], axis=1)
    tree = scipy.spatial.cKDTree(station_points, leafsize=100)
    xi = np.arange(lat_start, lat_end, degree)
    nx = len(xi)
    yi = np.arange(lon_start, lon_end, degree)
    ny = len(yi)
    xi, yi = np.meshgrid(xi, yi)
    all_points = np.stack([xi.flatten(), yi.flatten()], axis=1)
    dist, index = tree.query(all_points, k=k)
    weights = 1 / dist ** p
    norm_weights = weights / np.sum(weights, axis=1)[:, np.newaxis]
    res = np.sum(z[index] * norm_weights, axis=1)
    res = np.reshape(res, (nx, ny), order=reshape_order)
    return res


def qualified_files(date_range: pd.date_range, variable: str, cfg):
    '''

    :param date_range: date range
    :param variable: variable name
    :param cfg: configuration dict
    :return: List of eligible files
    '''
    var_all = {'大型蒸发量': 'evp', '日最高地表气温': 'gst', '日最低地表气温': 'gst',
               '平均地表气温': 'gst', '20-20时累计降水量': 'pre', '平均本站气压': 'prs', '日最高本站气压': 'prs',
               '日最低本站气压': 'prs', '平均相对湿度': 'rhu', '日照时数': 'ssd',
               '平均气温': 'tem', '日最高气温': 'tem', '日最低气温': 'tem', '平均风速': 'win', '最大风速': 'win'}
    variable = var_all[variable].upper()

    date_range = set([datetime2str(x, sep='-') for x in date_range])
    files = absolute_file_paths(cfg['data_root'])
    var_files = []
    found = False
    for file in files:
        if variable in file:
            txt_date_range = set(get_date_range_from_txt(file))
            if not date_range.isdisjoint(txt_date_range):
                found = True
                var_files.append(file)
    if not found:
        raise ValueError("Did not find file needed.")

    def custum_key(file):
        return int(file[-10:-4])

    return sorted(var_files, key=custum_key)


def evp_convert(data):
    '''

    :param data: pd.DataFrame, with datetime as index
    :return: Processed EVP data
    '''
    ks = {1: 0.605, 2: 0.646, 3: 0.645, 4: 0.596, 5: 0.585, 6: 0.592, 7: 0.590, 8: 0.624, 9: 0.620, 10: 0.638,
          11: 0.653, 12: 0.653}
    data.loc[data['小型蒸发量'] > 1000, '小型蒸发量'] = np.nan
    data.loc[data['大型蒸发量'] > 1000, '大型蒸发量'] = np.nan
    for index in data.index:
        if np.isnan(data['大型蒸发量'].loc[index]):
            month = data['月'].loc[index]
            data.loc[index, '大型蒸发量'] = data.loc[index, '小型蒸发量'] * ks[month]
    return data


def load_txt_forcing(txt, var):
    '''

    :param txt: site observation data of SURF_CLI_CHN_MUL_DAY dataset, for example: "SURF_CLI_CHN_MUL_DAY-EVP-13240-195101.TXT"
    :param var: variable name, such as '大型蒸发量'
    :return: dict
    '''
    header_evp = [x.strip() for x in '''区站号
                    纬度
                    经度
                    观测场拔海高度
                    年
                    月
                    日
                    小型蒸发量
                    大型蒸发量
                    小型蒸发量质量控制码
                    大型蒸发量质量控制码'''.split('\n')]

    header_prs = [x.strip() for x in '''区站号
    纬度
    经度
    观测场拔海高度
    年
    月
    日
    平均本站气压
    日最高本站气压
    日最低本站气压
    平均本站气压质量控制码
    日最高本站气压质量控制码
    日最低本站气压质量控制码'''.split('\n')]

    header_tem = [x.strip() for x in '''区站号
    纬度
    经度
    观测场拔海高度
    年
    月
    日
    平均气温
    日最高气温
    日最低气温
    平均气温质量控制码
    日最高气温质量控制码
    日最低气温质量控制码'''.split('\n')]

    header_rhu = [x.strip() for x in '''区站号
    纬度
    经度
    观测场拔海高度
    年
    月
    日
    平均相对湿度
    最小相对湿度(仅自记)
    平均相对湿度质量控制码
    最小相对湿度质量控制码'''.split('\n')]

    header_pre = [x.strip() for x in '''区站号
    纬度
    经度
    观测场拔海高度
    年
    月
    日
    20-8时降水量
    8-20时降水量
    20-20时累计降水量
    20-8时降水量质量控制码
    8-20时累计降水量质量控制码
    20-20时降水量质量控制码'''.split('\n')]

    header_win = [x.strip() for x in '''区站号
    纬度
    经度
    观测场拔海高度
    年
    月
    日
    平均风速
    最大风速
    最大风速的风向
    极大风速
    极大风速的风向
    平均风速质量控制码
    最大风速质量控制码
    最大风速的风向质量控制码
    极大风速质量控制码
    极大风速的风向质量控制码'''.split('\n')]

    header_ssd = [x.strip() for x in '''区站号
    纬度
    经度
    观测场拔海高度
    年
    月
    日
    日照时数
    日照时数质量控制码'''.split('\n')]

    header_gst = [x.strip() for x in '''区站号
    纬度
    经度
    观测场拔海高度
    年
    月
    日
    平均地表气温
    日最高地表气温
    日最低地表气温
    平均地表气温质量控制码
    日最高地表气温质量控制码
    日最低地表气温质量控制码'''.split('\n')]

    var_all = {'大型蒸发量': [1000, header_evp], '日最高地表气温': [10000, header_gst], '日最低地表气温': [10000, header_gst],
               '平均地表气温': [10000, header_gst], '20-20时累计降水量': [10000, header_pre], '平均本站气压': [20000, header_prs],
               '日最高本站气压': [20000, header_prs], '日最低本站气压': [20000, header_prs], '平均相对湿度': [300, header_rhu],
               '日照时数': [300, header_ssd], '平均气温': [10000, header_tem], '日最高气温': [10000, header_tem],
               '日最低气温': [10000, header_tem], '平均风速': [1000, header_win], '最大风速': [1000, header_win]}

    data = pd.read_table(txt, sep='\s+', header=None)

    data.columns = var_all[var][1]
    if var == '大型蒸发量':
        data = evp_convert(data)
    else:
        data.loc[np.abs(data[var]) > var_all[var][0], var] = np.nan

    data['经度'] = data['经度'] / 100
    data['纬度'] = data['纬度'] / 100

    year = np.unique(data['年'].values)[0]
    unique_month = np.unique(data['月'].values)
    unique_day = np.unique(data['日'].values)
    res = {}
    for month in unique_month:
        for day in unique_day:
            tmp_data = data[np.logical_and(data['月'] == month, data['日'] == day)]
            zs = tmp_data[var].values
            res[f'{year}-{month}-{day}'] = {'lats': tmp_data['纬度'].values, 'lons': tmp_data['经度'].values, 'zs': zs}

    return res


def variable_tif(date_start, date_end, variable, cfg):
    '''

    :param date_start: start date
    :param date_end: end date
    :param variable: variable name
    :param cfg: configuration dict
    :return: None
    '''
    date_range = pd.date_range(date_start, date_end)
    var_files = qualified_files(date_range, variable, cfg)
    for file in tqdm(var_files):
        station_data = load_txt_forcing(file, variable)
        for key in station_data.keys():
            x, y, z = station_data[key].values()
            x, y, z = x[~np.isnan(z)], y[~np.isnan(z)], z[~np.isnan(z)]  # Only use data with observing sites
            if len(x) < cfg['num_neighbours']:
                raise UserWarning(
                    f'Too few observations, need as least {cfg["num_neighbours"]} stations with observation for interpolation')
            tmp_res = idw_interpolation(x, y, z, lat_start=cfg['lat_start'], lat_end=cfg['lat_end'],
                                        lon_start=cfg['lon_start'], lon_end=cfg['lon_end'], degree=cfg['degree'],
                                        k=cfg['num_neighbours'])
            if not os.path.isdir(f'{cfg["outdir"]}/{variable}'):
                os.mkdir(f'{cfg["outdir"]}/{variable}')
            geotif_from_array(array=tmp_res, lat_start=cfg['lat_start'], lat_end=cfg['lat_end'],
                              lon_start=cfg['lon_start'], lon_end=cfg['lon_end'], degree=cfg['degree'],
                              output_file=f'{cfg["outdir"]}/{variable}/{key + "-" + variable}.tif')


def mutil(cfg):
    '''
    Multithreading
    
    :param cfg: configuration dict
    :return: None
    '''
    proc = []

    for variable in ['大型蒸发量', '日最高地表气温', '日最低地表气温', '平均地表气温',
                     '20-20时累计降水量', '平均本站气压', '日最高本站气压',
                     '日最低本站气压', '平均相对湿度', '日照时数',
                     '平均气温', '日最高气温', '日最低气温', '平均风速', '最大风速']:
        p = Process(target=variable_tif, args=(cfg['date_start'], cfg['date_end'], variable, cfg))
        proc.append(p)

    for p in proc:
        p.start()

    for p in proc:
        p.join()


if __name__ == '__main__':
    cfg = dict(outdir='./output/raster_meteorological',
               num_neighbours=12,
               data_root='./data/SURF_CLI_CHN_MUL_DAY/DATA',
               date_start=datetime.datetime(1999, 1, 1),
               date_end=datetime.datetime(1999, 12, 31),
               lat_start=15,
               lat_end=55,
               lon_start=70,
               lon_end=140,
               degree=0.1)
    mutil(cfg)
