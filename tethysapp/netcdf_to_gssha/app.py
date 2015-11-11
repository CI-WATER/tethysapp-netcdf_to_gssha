from tethys_sdk.base import TethysAppBase, url_map_maker
from tethys_sdk.handoff import HandoffHandler
from tethys_sdk.jobs import CondorJobTemplate


class NetcdfToGsshaInput(TethysAppBase):
    """
    Tethys app class for NetCDF to GSSHA Input.
    """

    name = 'Convert NetCDF to GSSHA Input'
    index = 'netcdf_to_gssha:home'
    icon = 'netcdf_to_gssha/images/icon.gif'
    package = 'netcdf_to_gssha'
    root_url = 'netcdf-to-gssha'
    color = '#34495e'
        
    def url_maps(self):
        """
        Add controllers
        """
        UrlMap = url_map_maker(self.root_url)

        url_maps = (UrlMap(name='home',
                           url='netcdf-to-gssha',
                           controller='netcdf_to_gssha.controllers.home'),
                    UrlMap(name='jobs',
                           url='netcdf-to-gssha/jobs',
                           controller='netcdf_to_gssha.controllers.jobs'),
                    UrlMap(name='results',
                           url='netcdf-to-gssha/{job_id}/results',
                           controller='netcdf_to_gssha.controllers.results'),
                    UrlMap(name='download',
                           url='netcdf-to-gssha/{job_id}/download',
                           controller='netcdf_to_gssha.controllers.download')
        )

        return url_maps

    def handoff_handlers(self):
        """
        Add handoff handlers
        """
        handoff_handlers = (HandoffHandler(name='convert-netcdf',
                                           handler='netcdf_to_gssha.handoff.convert_netcdf',
                                           internal=True
                            ),
                            HandoffHandler(name='old-convert-netcdf',
                                           handler='handoff:convert_netcdf')
                            )
        return handoff_handlers

    def job_templates(self):
        """
        Define job templates
        """

        job_templates = (CondorJobTemplate(name='convert_to_ascii',
                                       parameters={'executable': '$(APP_WORKSPACE)/netcdf_to_ascii.py',
                                                   'condorpy_template_name': 'vanilla_transfer_files',
                                                   # 'attributes': {'transfer_output_files': ('$(job_name).nc',),},
                                                   # 'scheduler': None,
                                                   # 'remote_input_files': ('$(APP_WORKSPACE)/netcdf_to_ascii.py',),
                                                  }
                                      ),
                    )

        return job_templates