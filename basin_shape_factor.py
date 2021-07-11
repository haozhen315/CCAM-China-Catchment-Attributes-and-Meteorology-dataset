import shapefile
from tqdm import tqdm
from shapely.geometry import Polygon, LineString
from shapely.geometry import Point
from functools import partial
import shapely.ops as ops
import pyproj
from utils import *
from shapely.ops import transform

'''
Reference: 
Subramanya, K. (2013). Engineering Hydrology, 4e, Tata McGraw-Hill Education.
Masutomi, Y., Y. Inui, K. Takahashi and Y. Matsuoka (2009). "Development of highly accurate global polygonal drainage basin data." 
Hydrological Processes: An International Journal 23(4): 572-584.

├── basin_shape_factor.py
├── shapefiles
|   ├── basin_0000.shp
|   ├── basin_0001.shp
├── data
|   ├── river_network
|   |   ├── as_streams_wgs.shp
├── output

Drainage basin boundary data and the river network data are obtained from the Global Drainage Basin Database (GDBD) 
dataset: https://www.cger.nies.go.jp/db/gdbd/gdbd_index_e.html. Here, determining the basin outlet needs river network 
and basin boundaries as input. Since the river network provided by GDBD did not cover all basins (mainly watersheds 
where the river stream is not clear), basin outlet and hence river length cannot be derived for some of the basins.
'''


def latlon2km(p1, p2):
    '''
    Convert distance in degree to km
    '''
    import pyproj
    pyproj.Proj("+init=epsg:4326")
    from shapely.geometry import LineString
    from functools import partial
    import pyproj
    from shapely.ops import transform

    line = LineString([p1, p2])
    wgs84 = pyproj.Proj(init='epsg:4326')
    utm = pyproj.Proj(init='epsg:32649')

    project = partial(
        pyproj.transform,
        wgs84,
        utm)

    utm_polyline = transform(project, line)
    length_km = utm_polyline.length / 1000
    return length_km


def find_outlet(catchment_shp, stream_shps):
    '''
    Find catchment outlet point given river stream shps and catchment shapefile
    '''
    basin = shapefile.Reader(catchment_shp).shapeRecord(0).shape
    stream_shapes = shapefile.Reader(stream_shps).shapes()

    basin_polygon = Polygon(basin.points)
    if not basin_polygon.is_valid:
        print('invalid polygon')
        return
    for stream in stream_shapes:
        line = LineString(stream.points)
        intersection = basin_polygon.exterior.intersection(line)
        if intersection.is_empty:
            continue
        else:
            try:
                return intersection.coords.xy[0][0], intersection.coords.xy[1][0]
            except:
                continue


def get_record(basins, i):
    '''
    Read shapefile information

    basins: shapefile.Reader(shapefile)
    '''
    fields = basins.fields[1:]
    field_names = [field[0] for field in fields]
    atr = dict(zip(field_names, basins.shapeRecord(i).record))
    return atr


def catchment_perimeter(catchment_shp):
    '''
    Calculate the Perimeter of the catchment given shapefile
    '''
    polyline = Polygon(shapefile.Reader(catchment_shp).shapeRecord(0).shape.points)
    wgs84 = pyproj.Proj(init='epsg:4326')
    utm = pyproj.Proj(init='epsg:32649')

    project = partial(
        pyproj.transform,
        wgs84,
        utm)

    utm_polyline = transform(project, polyline)
    length_km = utm_polyline.length / 1000
    return length_km


def longest_distance(catchment_shp, stream_shps):
    '''
    For a given point, find the remotest point on the polygon boundary and return the distance
    '''
    basin = shapefile.Reader(catchment_shp).shapeRecord(0).shape
    streams = shapefile.Reader(stream_shps).shapes()
    outlet = find_outlet(catchment_shp, stream_shps)
    if outlet:
        max_dis = 0
        for p in basin.points:
            if Point(p).distance(Point(outlet)) > max_dis:
                max_dis = Point(p).distance(Point(outlet))
                max_point = p
        return latlon2km(max_point, outlet)


def form_factor(A, L):
    '''
    Catchment Form factor
    [Section Catchment Characteristics] Subramanya, K. (2013). Engineering hydrology, 4e. Tata McGraw-Hill Education.
    '''
    return A / L ** 2


def shape_factor(A, L):
    '''
    Catchment Shape factor
    [Section Catchment Characteristics] Subramanya, K. (2013). Engineering hydrology, 4e. Tata McGraw-Hill Education.
    '''
    return L ** 2 / A


def compactness_coefficient(P, A):
    '''
    Catchment Compactness coefficient
    [Section Catchment Characteristics] Subramanya, K. (2013). Engineering hydrology, 4e. Tata McGraw-Hill Education.
    '''
    return 0.2821 * P / np.sqrt(A)


def circulatory_ratio(P, A):
    '''
    Catchment Circulatory ratio
    [Section Catchment Characteristics] Subramanya, K. (2013). Engineering hydrology, 4e. Tata McGraw-Hill Education.
    '''
    return 12.57 * A / P ** 2


def elongation_ratio(A, L):
    '''
    Catchment Elongation ratio
    [Section Catchment Characteristics] Subramanya, K. (2013). Engineering hydrology, 4e. Tata McGraw-Hill Education.
    '''
    return 1.128 * np.sqrt(A) / L


def basin_area(basin_shp):
    '''
    Calculate catchment area given shapefile
    '''
    basin = shapefile.Reader(basin_shp).shapeRecord(0).shape
    geom = Polygon(basin.points)
    geom_area = ops.transform(
        partial(
            pyproj.transform,
            pyproj.Proj(init='EPSG:4326'),
            pyproj.Proj(
                proj='aea',
                lat_1=geom.bounds[1],
                lat_2=geom.bounds[3]
            )
        ),
        geom)
    return geom_area.area / 1000 ** 2  # km^2


def basin_topo_stats(basin_shps, stream_shps):
    '''
    Catchment shape factors statistics given a list of basin shapefiles and river stream shapefiles
    '''
    res = {}
    for basin_shp in tqdm(basin_shps):
        basin = shapefile.Reader(basin_shp)
        gdbd_id = int(get_record(basin, 0)['GDBD_ID'])
        print(gdbd_id)
        L = longest_distance(basin_shp, stream_shps)
        A = basin_area(basin_shp)
        P = catchment_perimeter(basin_shp)
        if L:
            res[gdbd_id] = {'Length': L, 'Area': A, 'Form factor': form_factor(A, L),
                            'Shape factor': shape_factor(A, L),
                            'Compactness coefficient': compactness_coefficient(P, A),
                            'Circulatory ratio': circulatory_ratio(P, A),
                            'Elongation ratio': elongation_ratio(A, L)}
        # If the given polygon is invalid, the length attribute (L) cannot be determined, and other variables depend on that.
        else:
            res[gdbd_id] = {'Length': None, 'Area': A, 'Form factor': None,
                            'Shape factor': None,
                            'Compactness coefficient': None,
                            'Circulatory ratio': None,
                            'Elongation ratio': None}
    return res


if __name__ == '__main__':
    print('Calculating basin shape factors')
    shp_folfer = './shapefiles'
    stream_shps = './data/river_network/as_streams_wgs.shp'
    out_dir = './output'

    basin_shps = [file for file in absolute_file_paths(shp_folfer) if '.shp' in file]
    topo_stats = basin_topo_stats(basin_shps=basin_shps, stream_shps=stream_shps)
    res = pd.DataFrame(topo_stats).T
    res.columns = [x.lower().replace(' ', '_') for x in res.columns]
    res.to_excel(f'{out_dir}/shape_factor.xlsx')
