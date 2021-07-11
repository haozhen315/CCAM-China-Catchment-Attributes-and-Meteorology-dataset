If you find any bugs or unclear in the code, you can contact me through zhen.hao18 at alumni.imperial.ac.uk

This repository supports generating 120+ basin attributes given a basin boundary in shapefile format within Contiguous China. There are two ways to use this project:
1. Calculate certain types of attributes using the single scripts;
2. Calculate all characteristics for the given basins using the calculate_all_attributes.py.


Steps to generate the desired basin attributes:
1. Prepare the required source data, put them in the right place following the instruction in each script; for data from SoilGrids250m, the TIF file might be large, and you will need to downscale large TIF files;
2. Run the code.

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
