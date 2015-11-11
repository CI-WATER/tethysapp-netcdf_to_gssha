# Define your handoff handlers here

from app import NetcdfToGsshaInput as app

import os

def convert_netcdf(request, path_to_netcdf_file):
    """
    Take NetCDF file on server and symlink into local workspace
    """
    workspace = app.get_user_workspace(request)
    src = path_to_netcdf_file
    dst = os.path.join(workspace.path, os.path.basename(src))
    try:
        os.symlink(src, dst)
    except OSError:
        pass

    return 'netcdf_to_gssha:home'