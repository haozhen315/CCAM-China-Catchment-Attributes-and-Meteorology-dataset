from itertools import groupby
import pandas as pd
import numpy as np
from tqdm import tqdm
from utils import absolute_file_paths
import datetime
import os

'''
calculate catchment-scale climate indicator
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
    data pd.DataFrame containing PRE ['20-20时累计降水量'] and TEM ['平均气温'] columns | longer is better
    Returns
    -------
    float
        p_seasonality
    '''

    from sklearn.linear_model import LinearRegression
    from datetime import timedelta
    from tqdm import tqdm

    data = data.loc[datetime.datetime(2009, 1, 1): datetime.datetime(2014, 12, 31)]

    best_score = 0
    for st in range(365):
        X = []
        y = []
        for i in range(len(data)):
            t = data.index[i].day_of_year
            X.append(np.sin(2 * np.pi * (t - st) / 365))
            # y.append(data.iloc[i]['TEM'])
            y.append(data.iloc[i]['平均气温'])
        X = np.array(X).reshape(-1, 1)
        y = np.array(y)
        reg = LinearRegression(fit_intercept=True, n_jobs=-1).fit(X, y)
        if reg.score(X, y) > best_score:
            best_reg = reg
            best_score = reg.score(X, y)
            best_X = X
            best_st = st
    delta_t = best_reg.coef_[0]
    st = best_st
    best_reg_t = best_reg

    best_score = 0
    for sp in range(365):
        X = []
        y = []
        for i in range(len(data)):
            t = data.index[i].day_of_year
            X.append(np.sin(2 * np.pi * (t - sp) / 365))
            # y.append(data.iloc[i]['PRE'])
            y.append(data.iloc[i]['20-20时累计降水量'])
        X = np.array(X).reshape(-1, 1)
        y = np.array(y)
        reg = LinearRegression(fit_intercept=True, n_jobs=-1).fit(X, y)
        if reg.score(X, y) > best_score:
            best_reg = reg
            best_score = reg.score(X, y)
            best_X = X
            best_sp = sp
    pbar = best_reg.intercept_
    delta_p = best_reg.coef_[0] / pbar
    sp = best_sp
    best_reg_p = best_reg

    p_season = delta_p * np.sign(delta_t) * np.cos(2 * np.pi * (sp - st) / 365)
    return p_season, delta_t, st, delta_p, sp, best_reg_t, best_reg_p


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
                     'p_seasonality': p_seasonality(df)[0]}
    res = pd.DataFrame(res).T.reset_index().rename(columns={'index': 'basin_id'})
    res.to_excel(f'{output_dir}/climate.xlsx', index=None)
