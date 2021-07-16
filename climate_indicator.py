from itertools import groupby
import pandas as pd
import numpy as np
from tqdm import tqdm
from utils import absolute_file_paths
import datetime
import os

'''
Reference:
Woods R A. Analytical model of seasonal climate impacts on snow hydrology: Continuous snowpacks[J]. Advances in Water Resources, 2009, 32(10): 1465-1481.
Addor, N., A. J. Newman, N. Mizukami and M. P. Clark (2017). "The CAMELS data set: catchment attributes and meteorology for large- sample studies." 
Hydrology and Earth System Sciences (HESS) 21(10): 5293-5313.

Calculate catchment-scale climate indicator. After the watershed meteorological time series has been successfully generated. 

├── climate_indicator.py
├── output
|   ├── catchment_meteorological
|   |   ├── 0001.xlsx # 0001 is the basin id, corresponding to the shapefile basin_0001.shp
'''


def p_seasonality(data):
    '''
    seasonality and timing of precipitation (estimated using sine curves to represent the annual temperature and
    precipitation cycles; positive (negative) values indicate that precipitation peaks in summer (winter); values close
    to 0 indicate uniform precipitation throughout the year)

    Reference:
    Woods R A. Analytical model of seasonal climate impacts on snow hydrology: Continuous snowpacks[J].
    Advances in Water Resources, 2009, 32(10): 1465-1481.

    Method detail is described at the end of section 2.3 in the original paper.

    The parameters were estimated by exhaustive search on st, combined with least squares regression for tbar and delta_t;
    the same method was used to estimate pbar; delta_p and sp.

    Parameters
    ----------
    data pd.DataFrame containing PRE ['20-20时累计降水量'] and TEM ['平均气温'] columns

    Returns
    -------
    float
        mean p_seasonality over year 2009-2018
    '''

    from sklearn.linear_model import LinearRegression
    from datetime import timedelta
    from tqdm import tqdm

    p_seasons = []
    for year in tqdm(range(2009, 2019)):  # estimation is based on 10-year records
        df = data.loc[datetime.datetime(year, 5, 1):datetime.datetime(year + 1, 5, 1) - timedelta(1)]

        scores = []
        for st in range(365):
            X = []
            y = []
            for t in range(365):
                X.append(np.sin(2 * np.pi * (t - st) / 365))
                y.append(df.iloc[t]['平均气温'] / 10)
            X = np.array(X).reshape(-1, 1)
            y = np.array(y)
            reg = LinearRegression(fit_intercept=True).fit(X, y)
            scores.append({'st': st, 'tbar': reg.intercept_, 'delta_t': reg.coef_[0], 'score': reg.score(X, y)})
        scores = pd.DataFrame(scores).sort_values('score')
        st, tbar, delta_t, _ = scores.iloc[-1]

        scores = []
        for sp in range(365):
            X = []
            y = []
            for t in range(365):
                X.append(np.sin(2 * np.pi * (t - sp) / 365))
                y.append(df.iloc[t]['20-20时累计降水量'])
            X = np.array(X).reshape(-1, 1)
            y = np.array(y)
            reg = LinearRegression(fit_intercept=True).fit(X, y)
            scores.append({'sp': sp, 'pbar': reg.intercept_, 'delta_p': reg.coef_[0], 'score': reg.score(X, y)})
        scores = pd.DataFrame(scores).sort_values('score')
        sp, pbar, delta_p, _ = scores.iloc[-1]
        delta_p = delta_p / pbar

        p_season = delta_p * np.sign(delta_t) * np.cos(2 * np.pi * (sp - st) / 365)
        p_seasons.append(p_season)
        print(p_season)
    return np.mean(p_seasons), p_seasons


def split_a_list_at_zeros(L):
    return [list(g) for k, g in groupby(L, key=lambda x: x != 0) if k]


def p_mean(data: str):
    return float(data.mean())


def high_prec_freq(data: str):
    num_high_pre_days = len(data[data > data.mean() * 5].dropna())
    return num_high_pre_days / len(data) * 365


def high_prec_dur(data: str):
    data = np.array(data)
    tmp_data = data.copy()
    tmp_data[tmp_data < data.mean() * 5] = 0
    tmp = [len(x) for x in split_a_list_at_zeros(tmp_data)]
    if len(tmp) > 0:
        return np.mean(tmp)
    else:
        return None


def high_prec_timing(data: str):
    months = [x.month for x in data[data > data.mean() * 5].dropna().index]
    seasons = [month2season(x) for x in months]
    seasons, counts = np.unique(seasons, return_counts=True)
    if len(counts) > 0:
        return [x for _, x in sorted(zip(counts, seasons))][-1]
    else:
        return None


def month2season(month):
    """DJF=Dec-Feb, MAM=Mar-May,. JJA=Jun-Aug, SON=Sep-Nov"""
    if month in [3, 4, 5]:
        return 'mam'
    elif month in [6, 7, 8]:
        return 'jja'
    elif month in [9, 10, 11]:
        return 'son'
    elif month in [12, 1, 2]:
        return 'djf'


def low_prec_freq(data: str):
    num_low_pre_days = len(data[data < 1].dropna())
    return num_low_pre_days / len(data) * 365


def low_prec_dur(data: str):
    data = np.array(data)
    tmp_data = data.copy()
    tmp_data[data < 1] = 1
    tmp_data[data > 1] = 0
    tmp = [len(x) for x in split_a_list_at_zeros(tmp_data)]
    if len(tmp) > 0:
        return np.mean(tmp)
    else:
        return None


def low_prec_timing(data: str):
    months = [x.month for x in data[data < 1].dropna().index]
    seasons = [month2season(x) for x in months]
    seasons, counts = np.unique(seasons, return_counts=True)
    return [x for _, x in sorted(zip(counts, seasons))][-1]


def frac_snow_daily(df):
    return len(df.loc[df['平均气温'] < 0].loc[df['20-20时累计降水量'] > 0]) / len(df)


if __name__ == '__main__':

    forcing_dir = './output/catchment_meteorological'
    output_dir = './output'

    files = absolute_file_paths(forcing_dir)

    res = {}
    for file in tqdm(files):
        name = os.path.basename(file).split('.')[0]
        df = pd.read_excel(file).rename(columns={'Unnamed: 0': 'date'}).set_index('date')
        df = df.loc[
             datetime.datetime(1999, 1, 1):datetime.datetime(2019, 12, 31)]  # Make sure to calculate all year round
        pre = df[['20-20时累计降水量']]
        tem = df[['平均气温']]

        res[name] = {'p_mean': p_mean(pre), 'high_prec_freq': high_prec_freq(pre),
                     'high_prec_dur': high_prec_dur(pre), 'high_prec_timing': high_prec_timing(pre),
                     'low_prec_freq': low_prec_freq(pre), 'low_prec_dur': low_prec_dur(pre),
                     'low_prec_timing': low_prec_timing(pre), 'frac_snow_daily': frac_snow_daily(df),
                     'p_seasonality': p_seasonality(df)}
    pd.DataFrame(res).T.to_excel(f'{output_dir}/climate.xlsx')
