#!/usr/lib/tethys/bin/python
import netCDF4 as nc
import numpy as np
import time
import os
from zipfile import ZipFile

GRASS_HEADER_TEMPLATE = """north: {north}
south: {south}
east: {east}
west: {west}
rows: {rows}
cols: {cols}
"""

ARC_HEADER_TEMPLATE = """ncols {cols}
nrows {rows}
xllcorner {south}
yllcorner {west}
cellsize {cell_size}
NODATA_value {no_data}
"""

LAT_UNITS = ['degrees_north', 'degree_north', 'degree_N', 'degrees_N', 'degreeN', 'degreesN']
LON_UNITS = ['degrees_east', 'degree_east', 'degree_E', 'degrees_E', 'degreeE', 'degreesE']
TIME_VAR_NAME = 'time'
LAT_VAR_NAME = 'lat'
LON_VAR_NAME = 'lon'

def get_lat_lon_variables(variables):
    lat_var = None
    lon_var = None

    for var_name in variables:
        var = variables[var_name]
        units = get_variable_units(var)
        if units in LON_UNITS:
            lon_var =  var
            global LON_VAR_NAME
            LON_VAR_NAME = var_name
        elif units in LAT_UNITS:
            lat_var = var
            global LAT_VAR_NAME
            LAT_VAR_NAME = var_name

    return lat_var, lon_var

def get_variable_units(variable):
    if 'units' in variable.ncattrs():
        return variable.units

def get_lats_and_lons(data):
    lat_var, lon_var = get_lat_lon_variables(data.variables)
    lats = lat_var[:]
    lons = lon_var[:]
    return lats, lons

def write_header(data, bounding_box_indices, no_data, output_format):
    lats, lons = get_lats_and_lons(data)
    half_cell_height = abs(lats[1] - lats[0])/2.0
    half_cell_width = abs(lons[1] - lons[0])/2.0
    assert(half_cell_width == half_cell_width)
    def correct_coordinate(coord):
        if coord < 0:
            return coord# + 360
        else:
            return coord


    north = lats[bounding_box_indices['north']] + half_cell_height
    south = lats[bounding_box_indices['south']] - half_cell_height
    east = lons[bounding_box_indices['east']] + half_cell_width
    west = lons[bounding_box_indices['west']] - half_cell_width

    east = correct_coordinate(east)
    west = correct_coordinate(west)

    rows = 1 + abs(bounding_box_indices['east'] - bounding_box_indices['west'])
    cols = 1 + abs(bounding_box_indices['north'] - bounding_box_indices['south'])
    cell_size = half_cell_width * 2

    header_values = {'north': north,
                     'south': south,
                     'east': east,
                     'west': west,
                     'rows': rows,
                     'cols': cols,
                     'cell_size': cell_size,
                     'no_data': no_data}

    header_template = ARC_HEADER_TEMPLATE if output_format == 'ARC' else GRASS_HEADER_TEMPLATE

    header = header_template.format(**header_values)
    return header


def get_bounding_box_indices(data, bbox=None):
    lats, lons = get_lats_and_lons(data)

    if not bbox:
        return {'north': len(lats) - 1,
                'south': 0,
                'east': len(lons) - 1,
                'west': 0}

    north, south, east, west = bbox

    if east < 0:
        east += 360
    if west < 0:
        west += 360

    north_index = _find_nearest_index(lats, north)
    south_index = _find_nearest_index(lats, south)
    east_index = _find_nearest_index(lons, east)
    west_index = _find_nearest_index(lons, west)

    return {'north': north_index,
            'south': south_index,
            'east': east_index,
            'west': west_index}

def index_variable(variable, time_index, lat_indicies, lon_indicies):
    index_array = []
    for dimension in variable.dimensions:

        if dimension == TIME_VAR_NAME:
            # index_array.append('{0}:{1}'.format(time_index, time_index + 1))
            index_array.append('{0}'.format(time_index))
        elif dimension == LAT_VAR_NAME:
            index_array.append('{0}:{1}'.format(lat_indicies[0], lat_indicies[1] + 1))
        elif dimension == LON_VAR_NAME:
            index_array.append('{0}:{1}'.format(lon_indicies[0], lon_indicies[1] + 1))
        else:
            index_array.append('0')

    index_str = ', '.join(index_array)
    index_stmnt = 'variable[{0}]'.format(index_str)
    array = eval(index_stmnt)
    return array

def get_values(data, variable_name, time_index, bounding_box_indices, no_data_value):
    north_index = bounding_box_indices['north']
    south_index = bounding_box_indices['south']
    east_index = bounding_box_indices['east']
    west_index = bounding_box_indices['west']

    variable = data.variables[variable_name]
    array = index_variable(variable, time_index, (south_index, north_index), (west_index, east_index))
    mask = np.ma.getmask(array)
    if mask.any():
        return array.filled(no_data_value)
    return array

def array_to_string(array):
    string = '\n'.join([' '.join([str(v) for v in row]) for row in array])
    return string

def write_ascii_file(file_name, header, values):
    with open(file_name, 'w') as ascii:
        ascii.write(header)
        ascii.write(values)

def zip_files(zip_file_name, files_to_zip):
    with ZipFile(zip_file_name, 'w') as zip_file:
        for file_name in files_to_zip:
            zip_file.write(file_name)
            os.remove(file_name)

def _find_nearest_index(array,value):
    # TODO possible bug with finding west index
    idx = (np.abs(array-value)).argmin()
    return idx

def create_ascii(input_file_name,
                 variable,
                 timesteps=None,
                 bbox=None,
                 no_data_value=-9999,
                 output_zipfile_name=None,
                 output_format='GRASS'):

    data = nc.Dataset(input_file_name, 'r')

    bounding_box_indices = get_bounding_box_indices(data, bbox)
    header = write_header(data, bounding_box_indices, no_data_value, output_format)
    file_extension = 'asc' if output_format == 'ARC' else 'ggd'
    timesteps = timesteps or range(0,len(data.variables['time']))
    output_files = []
    for time_step in timesteps:
        values = get_values(data, variable, time_step, bounding_box_indices, no_data_value)
        values_str = array_to_string(values)
        time_str = time.strftime('%Y%m%d%H%M%S', time.gmtime(data.variables['time'][time_step]))
        output_file_name = '%s-%s.%s' % (variable, time_str, file_extension)
        write_ascii_file(output_file_name, header, values_str)
        output_files.append(output_file_name)

    output_zipfile_name = output_zipfile_name or '%s-%s.zip' % (input_file_name, variable)
    zip_files(output_zipfile_name, output_files)

if __name__ == '__main__':
    # input_file_name = 'SSW_Download-1446756228.52.nc'
    # variable = 'SOILM_110_DBLY'
    input_file_name = '../user_workspaces/sdc50/SSW_Download-1446756228.52.nc'
    variable = 'APCPsfc_110_SFC_acc1h'
    # variable = 'SOILM_GDS0_DBLY'
    timesteps = None#(0,)
    bbox = None
    no_data_value = -9999

    import sys
    input_file_name = sys.argv[1]
    variable = sys.argv[2]
    file_type = sys.argv[3]
    create_ascii(input_file_name, variable, timesteps, bbox, no_data_value, file_type)


