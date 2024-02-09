# CCAM: China Catchment Attributes and Meteorology dataset

Accompanying code for our paper:

```
Hao, Z., Jin, J., Xia, R., Tian, S., Yang, W., Liu, Q., Zhu, M., Ma, T., Jing, C., and Zhang, Y.: CCAM: China Catchment Attributes and Meteorology dataset, Earth Syst. Sci. Data, 13, 5591–5616, https://doi.org/10.5194/essd-13-5591-2021, 2021.
```

The manuscript can be found [here](https://doi.org/10.5194/essd-13-5591-2021) (publicly available).

This repository supports generating 120+ basin attributes for each basin given a single or several basin boundaries. Except for the netCDF and Meteorological time series data, which only covers China, other data sources are global, which means that the code can also be used to calculate these attributes of watersheds in other regions.

## Description of the data set
CCAM: All catchment data (catchment static attributes, meteorological time series) are calculated based on the information within the corresponding catchment boundary, even if there is an upper catchment.
HydroMLYR: All catchmens are divided up to the source of the river such that there is no upper catchment.

## Find the data you need
The data provided by the [dataset](https://zenodo.org/record/5092162#.YPVcpuhLhPY) includes all river basins in China. Use the following code to find the nearest river basin id according to the given coordinates:
```python
>>> import pandas as pd
>>> import numpy as np
>>> x, y = 29.7060803, 120.1387931
>>> loc_data = pd.read_csv('./2_location_and_topography.txt')
>>> data['dis'] = np.sqrt((data['lat'] - x)**2 + (data['lon'] - y)**2)
>>> data.sort_values('dis')[:3]
```

In addition to the above method, one can download [GDBD] (https://www.cger.nies.go.jp/db/gdbd/gdbd_index_e.html) Asia data. Open the mdb file in a GIS software, then the GDBD_ID of basins of interest can be found easily.

## Update
(20210906) SURF_CLI_CHN_MUL_DAY has just been closed for sharing. If you have SURF_CLI_CHN_MUL_DAY data downloaded or SURF_CLI_CHN_MUL_DAY may be made public again in the future, the code meteo_time_series_surf.py for calculating the watershed climate time series can still be used. If not, the meteorological time series from 1990 to 2020 for any given basin can still be calculated based on our [released data](https://zenodo.org/record/5137288) using meteo_time_series_ccam.py. The principle is to calculate the overlapping areas of the given watershed and the watersheds we have prepared, and then calculate the meteorological time series of the given watershed by weighting. 

## Contact
If you find any bug or unclear in the code, you can contact me through zhen.hao18 at alumni.imperial.ac.uk

## Dependency
fiona==1.8.4<br/>
gdal==2.3.1<br/>
geopandas==0.6.1<br/>
netcdf4==1.4.2<br/>
pyproj==3.1.0<br/>
rasterio==1.0.21<br/>
rasterstats==0.14.0<br/>
richdem==0.3.4<br/>
scikit-learn==0.24.2<br/>
pyshp==2.1.3<br/>
scipy==1.6.2<br/>
xarray==0.17.0<br/>
tqdm==4.60.0<br/>
shapely==1.6.4.post2<br/>
pandas==1.2.3

## Guidelines for generating data for custom watersheds
There are two ways to use this project:
1. Calculate certain types of attributes using the single scripts; sample outputs are provided in ./output/
2. Calculate all characteristics for the given basins using the calculate_all_attributes.py.


Steps to generate the desired basin attributes:
1. Prepare the required source data, put them in the right place following the instruction in each script; for data from SoilGrids250m, the TIF file might be large, and you may need to downscale large TIF files if you use GDAL=2.2.2;
2. Run the code.

The [9_code_data.zip](https://zenodo.org/record/5137288/files/9_code_data.zip?download=1) included in the Zenodo repository contains processed_glim.py, processed_igbp.tif, processed_permeability.tif and processed_porosity.tif

When all the data is ready, the ./data folder will look like this:
```bash
├── dems
|   ├── ASTGTMV003_N34E111_dem.tif
|   ├── ASTGTMV003_N32E110_dem.tif
|   ├── ...
├── MCD15A3H
|   ├── MCD15A3H.A2002185.h22v04.006.2015149102803.hdf
|   ├── MCD15A3H.A2002188.h22v04.006.2015149102803.hdf
|   ├── ...
├── MOD13Q1
|   ├── MOD13Q1.A2002185.h22v04.006.2015149102803.hdf
|   ├── MOD13Q1.A2002188.h22v04.006.2015149102803.hdf
|   ├── ...
├── river_network
|   ├── as_streams_wgs.shp
|   ├── ...
├── soil_source_data
|   ├── binary
|   |   ├── log_k_s_l1
|   |   ├── log_k_s_l2
|   |   ├── ...
|   ├── netcdf 
|   |   ├── CL.nc
|   |   ├── GRAV.nc
|   |   ├── PDEP.nc
|   |   ├── SA.nc
|   |   ├── SI.nc
|   |   ├── SOM.nc
|   |   ├── POR.nc
|   |   ├── ...
|   ├── tif 
|   |   ├── *.tif
├── SURF_CLI_CHN_MUL_DAY
|   ├── Data
|   |   ├── EVP
|   |   |   ├── SURF_CLI_CHN_MUL_DAY-EVP-13240-195101.TXT
|   |   ├── GST
|   |   |   ├── ...
|   |   ├── WIN
|   |   |   ├── ...
├── glim_cate_number_mapping.csv
├── glim_name_short_long.txt
├── processed_glim.py
├── processed_igbp.tif
├── processed_permeability.tif
├── processed_porosity.tif
├── root_depth_calculated.txt
```

Following is the summary of each script that is used to calculate specific basin attributes; for an introduction to each feature, see [attributes_description.xlsx](https://github.com/haozhen315/BACC-Basin-Attributes-dataset-for-Contiguous-China/raw/main/data/attributes_description.xlsx):
- shape_factors.py: length, form factor, shape factor, compactness coefficient, circulatory ratio, elongation ratio	 
- climate_indicators.py: p_seasonality, high_prec_freq, high_prec_dur, high_prec_timing, low_prec_freq, low_prec_dur, low_prec_timing, frac_snow_daily	   
- elevation_slope.py: elev, slope
- permeability_porosity.py: geol_porosity, geol_permeability
- lithology.py: ig, pa, sc, su, sm, vi, mt, ss, pi, va, wb, pb, vb, nd, py, ev	   
- land_cover.py: land cover fractions
- lai_time_series.py: catchment scale LAI statistic time series
- ndvi_time_series.py: catchment scale NDVI statistic time series
- rooting_depth.py: root_depth_50, root_depth_99  
- soil.py: all soil attributes


## Meteorological time series of a custom watershed
In addition, this project supports generating catchment scale meteorological time series based on the [SURF_CLI_CHN_MUL_DAY](https://data.cma.cn/data/cdcdetail/dataCode/SURF_CLI_CHN_MUL_DAY_V3.0.html) data, following the steps specified in interpolation.py and meteorological_series.py.


## Citation
Hao, Z., Jin, J., Xia, R., Tian, S., Yang, W., Liu, Q., Zhu, M., Ma, T., Jing, C., and Zhang, Y.: CCAM: China Catchment Attributes and Meteorology dataset, Earth Syst. Sci. Data, 13, 5591–5616, https://doi.org/10.5194/essd-13-5591-2021, 2021.
