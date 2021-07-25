# CCAM: China Catchment Attributes and Meteorology dataset

Accompanying code for our paper:

```
Hao, Z., Jin, J., Xia, R., Tian, S., Yang, W., Liu, Q., Zhu, M., Ma, T., and Jing, C.: Catchment 
attributes and meteorology for large sample study in contiguous China, Earth Syst. Sci. Data 
Discuss. [preprint], https://doi.org/10.5194/essd-2021-71, in review, 2021.
```

The manuscript can be found [here](https://essd.copernicus.org/preprints/essd-2021-71/essd-2021-71.pdf) (publicly available).

This repository supports generating 120+ basin attributes for each basin given a single or several basin boundaries. Except for the netCDF and Meteorological time series data, which only covers China, other data sources are global, which means that the code can also be used to calculate these attributes of watersheds in other regions.

## Contact Information
If you find any bug or unclear in the code, you can contact me through zhen.hao18 at alumni.imperial.ac.uk

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

## Guidelines for generating data for custom watersheds
There are two ways to use this project:
1. Calculate certain types of attributes using the single scripts; sample outputs are provided in ./output/
2. Calculate all characteristics for the given basins using the calculate_all_attributes.py.


Steps to generate the desired basin attributes:
1. Prepare the required source data, put them in the right place following the instruction in each script; for data from SoilGrids250m, the TIF file might be large, and you may need to downscale large TIF files if you use GDAL=2.2.2;
2. Run the code.

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
|   ├── binary # http://globalchange.bnu.edu.cn/research/soil5.jsp
|   |   ├── log_k_s_l1
|   |   ├── log_k_s_l2
|   |   ├── ...
|   ├── netcdf # http://globalchange.bnu.edu.cn/research/soil2
|   |   ├── CL.nc
|   |   ├── GRAV.nc
|   |   ├── PDEP.nc
|   |   ├── SA.nc
|   |   ├── SI.nc
|   |   ├── SOM.nc
|   |   ├── POR.nc
|   |   ├── ...
|   ├── tif # https://files.isric.org/soilgrids/former/2017-03-10/data/
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

Following is the summary of each script that is used to calculate specific basin attributes; for an introduction to each feature, see [attributes_description.xlsx](https://github.com/haozhen315/BACC-Basin-Attributes-dataset-for-Contiguous-China/raw/main/attributes_description.xlsx):
- basin_shape_factor.py: length, form factor, shape factor, compactness coefficient, circulatory ratio, elongation ratio	 
- climate_indicator.py: p_seasonality, high_prec_freq, high_prec_dur, high_prec_timing, low_prec_freq, low_prec_dur, low_prec_timing, frac_snow_daily	   
- elev_slope.py: elev, slope
- glhymps.py: geol_porosity, geol_permeability
- glim.py: ig, pa, sc, su, sm, vi, mt, ss, pi, va, wb, pb, vb, nd, py, ev	   
- igbp.py: land cover fractions
- lai_series.py: catchment scale LAI statistic time series
- ndvi_series.py: catchment scale NDVI statistic time series
- root_depth.py: root_depth_50, root_depth_99  
- soil.py: all soil attributes


## A program to calculate the meteorological time series of a custom watershed
In addition, this project supports generating catchment scale meteorological time series based on the [SURF_CLI_CHN_MUL_DAY](https://data.cma.cn/data/cdcdetail/dataCode/SURF_CLI_CHN_MUL_DAY_V3.0.html) data, following the steps specified in interpolation.py and meteorological_series.py.

## Dependencies
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
