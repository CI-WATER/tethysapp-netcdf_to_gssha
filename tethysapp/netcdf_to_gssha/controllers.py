from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.encoding import smart_str
# from django.core.servers.basehttp import FileWrapper

from tethys_sdk.gizmos import SelectInput, JobsTable, ToggleSwitch

from app import NetcdfToGsshaInput as app

from glob import glob
import os
import netCDF4 as nc
import time

job_manager = app.get_job_manager()

@login_required()
def home(request):
    """
    Controller for the app home page.
    """
    selected = None
    if 'file_select' in request.GET:
        selected = request.GET['file_select']
        if int(selected) < 0:
            selected = None

    user_workspace = app.get_user_workspace(request.user)
    nc_files = glob(os.path.join(user_workspace.path, '*.nc'))

    nc_file_list = [(os.path.basename(path), str(index)) for index, path in enumerate(nc_files)]
    nc_file_list.insert(0, ('(Select)', '-1'))
    file_select_options = SelectInput(display_text='Select NetCDF File',
                            name='file_select',
                            multiple=False,
                            options=nc_file_list,
                            original=True,
                            attributes='onchange=this.form.submit()')


    variable_select_options = None
    toggle_switch_options = None
    selected_file = None
    file_name = None

    if selected:
        file_select_options = None
        selected_file = nc_files[int(selected)]
        file_name = os.path.basename(selected_file)
        nc_file = nc.Dataset(selected_file, 'r')
        variables = nc_file.variables
        variable_list = [(variable, str(index)) for index, variable in enumerate(variables)]
        variable_select_options = SelectInput(display_text='Select Variable',
                            name='variable_select',
                            multiple=False,
                            options=variable_list,
                            original=True,
                            attributes='onchange=this.form.submit()')

        toggle_switch_options = ToggleSwitch(display_text='File Type',
                                               name='file_type',
                                               on_label='GRASS',
                                               off_label='ARC',
                                               on_style='success',
                                               off_style='primary',
                                               initial=True)


    if 'variable_select' in request.GET:
        variable_index = int(request.GET['variable_select'])
        selected_file = request.GET['selected_file']
        file_name = os.path.basename(selected_file)
        file_type = 'GRASS' if 'file_type' in request.GET else 'ARC'
        nc_file = nc.Dataset(selected_file, 'r')
        variables = nc_file.variables
        variable = [var for var in variables][variable_index]
        job_name = 'Convert-%s-%s-%s' % (file_name, variable, time.time())
        job_description = 'Convert %s in %s to %s ascii rasters.' % (variable, file_name, file_type.lower())
        job = job_manager.create_job(job_name, request.user, 'convert_to_ascii', description=job_description)
        job.set_attribute('arguments', (file_name, variable, file_type))
        job.set_attribute('transfer_input_files', ('../%s' % file_name,))
        job.set_attribute('remote_input_files', ('$(APP_WORKSPACE)/netcdf_to_ascii.py', selected_file))
        job.save()
        job.execute()
        return redirect('jobs/')

    context = {'file_select_options': file_select_options,
               'variable_select_options': variable_select_options,
               'toggle_switch_options': toggle_switch_options,
               'file_name': file_name,
               'selected_file': selected_file}

    return render(request, 'netcdf_to_gssha/home.html', context)


@login_required
def jobs(request):
    """
    Jobs controller
    """
    jobs = job_manager.list_jobs(request.user)

    jobs_table_options = JobsTable(jobs=jobs,
                                   column_fields=('id', 'description', 'run_time'),
                                   hover=True,
                                   striped=True,
                                   bordered=False,
                                   condensed=False,
                                   results_url='netcdf_to_gssha:results',
                                   )

    context = {'jobs_table_options': jobs_table_options}

    return render(request, 'netcdf_to_gssha/jobs.html', context)


@login_required
def results(request, job_id):
    """
    Results controller
    """

    context = {'job_id': job_id,}

    return render(request, 'netcdf_to_gssha/results.html', context)


@login_required
def download(request, job_id):
    job, file_name, file_path = _get_job(job_id)

    try:
        # wrapper = FileWrapper(file(file_path))
        response = HttpResponse(content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(file_name)
        response['Content-Length'] = os.path.getsize(file_path)
        response['X-Sendfile'] = file_path
        return response
    except:
        job._status = 'ERR'
        job.save()
        return redirect('netcdf_to_gssha:jobs')

def _get_job(job_id):
    job = job_manager.get_job(job_id)


    arguments = job.condorpy_job.arguments.split()
    file_name = '%s-%s.zip' % (arguments[0], arguments[1])
    file_path = os.path.join(job.initial_dir, file_name)

    return job, file_name, file_path