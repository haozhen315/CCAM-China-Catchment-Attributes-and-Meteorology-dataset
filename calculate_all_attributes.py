import os
import pandas as pd
import subprocess


def merge_dfs(dfs):
    from functools import reduce
    df_merged = reduce(lambda left, right: pd.merge(left, right, on=['Unnamed: 0'], how='outer'), dfs)
    return df_merged


if __name__ == '__main__':

    program_list = ['basin_shape_factor.py',
                    'elev_slope.py',
                    'glhymps.py',
                    'glim.py',
                    'igbp.py',
                    'lai_series.py',
                    'meteorological_series.py',
                    'root_depth.py',
                    'soil.py']

    for program in program_list:
        subprocess.call(['python', program])
        print("Finished:" + program)

    os.chdir('./output')
    files = os.listdir('.')

    dfs = []
    for file in files:
        if file.endswith('.xlsx'):
            dfs.append(pd.read_excel(file))
    res = merge_dfs(dfs)
    res.rename(columns={'Unnamed: 0': 'basin_id'}).to_excel('../all_attributes.xlsx', index=None)
