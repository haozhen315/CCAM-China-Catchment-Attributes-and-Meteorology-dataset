If you find any bugs or unclear in the code, you can contact me through zhen.hao18 at alumni.imperial.ac.uk

This repository supports generating 120+ basin attributes given a basin boundary in shapefile format within Contiguous China. There are two ways to use this project:
1. Calculate certain types of attributes using the single scripts;
2. Calculate all characteristics for the given basins using the calculate_all_attributes.py.


## Steps to generate the desired basin attributes:
Prepare the required source data, put them in the right place following the instruction in each script; for data from SoilGrids250m, the TIF file might be large, and you will need to downscale large TIF files;
Run the code.

Following is the summary of each script that is used to calculate specific basin attributes; for an introduction to each feature, see attributes_description.xlsx:
1. basin_shape_factor.py: length, form factor, shape factor, compactness coefficient, circulatory ratio, elongation ratio	 
2. climate_indicator.py: p_seasonality, high_prec_freq, high_prec_dur, high_prec_timing, low_prec_freq, low_prec_dur, low_prec_timing, frac_snow_daily	   
3. elev_slope.py: elev, slope
4. glhymps.py: geol_porosity, geol_permeability
5. glim.py: ig, pa, sc, su, sm, vi, mt, ss, pi, va, wb, pb, vb, nd, py, ev	   
6. igbp.py: land cover fractions
7. lai_series.py: catchment scale LAI statistic time series
8. ndvi_series.py: catchment scale NDVI statistic time series
9. root_depth.py: root_depth_50, root_depth_99  
10. soil.py: all soil attributes

In addition, this project supports generating catchment scale meteorological time series based on the SURF_CLI_CHN_MUL_DAY data (https://data.cma.cn/data/cdcdetail/dataCode/SURF_CLI_CHN_MUL_DAY_V3.0.html), following the steps specified in interpolation.py and meteorological_series.py.

### Meteorological time series:

1. Download the situ observations meteorological data (access permission needed): https://data.cma.cn/data/cdcdetail/dataCode/SURF_CLI_CHN_MUL_DAY_V3.0.html. The data directory should be structured as follows:
```bash
├── Data  
|   ├── EVP  
|   |   ├── SURF_CLI_CHN_MUL_DAY-EVP-13240-195101.TXT  
|   ├── GST  
|   |   ├── ...  
|   ├── WIN  
|   |   ├── ...  
```
2. Interpolate site observation climate data to rasters (GeoTIFF). In raster.py, change line 432-441, specify the output directory (will contain the interpolated rasters) and the root directory of the situ observation meteorological data, and possibly other configurations (e.g. resolution and spatial range of interpolation). The default interpolation range covers the whole of China. Note: interpolation can take hours to run.
3. Calculate the catchment means based on the interpolated rasters. In raster2catchment.py, change line 160-162, specify the path to the interpolated rasters (step 2), catchment shapefiles and the output directory. For the name of the catchment shapefiles, the catchment identifier should be separated by an underscore. And note that the shapefile should have a numeric identifier, e.g. "./shapefiles/0000.shp" or "./shapefiles/basin_0000.shp". For each basin, a "forcing.xlsx" file will be generated in the output directory.  e.g. "./forcing_time_series/basin_name/forcing.xlsx"

### Climate indicator:
In climate.py, change line 110 and 111, specify the path to the forcing time series (last step) and the output dir (will contain the climate statistic file). Run climate.py. 
