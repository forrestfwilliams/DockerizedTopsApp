import os
import site
import subprocess
from pathlib import Path

from jinja2 import Template
from tqdm import tqdm
from osgeo import gdal

TOPSAPP_STEPS = ['startup',
                 'preprocess',
                 'computeBaselines',
                 'verifyDEM',
                 'topo',
                 'subsetoverlaps',
                 'coarseoffsets',
                 'coarseresamp',
                 'overlapifg', 'prepesd',
                 'esd', 'rangecoreg',
                 'fineoffsets', 'fineresamp', 'ion',
                 'burstifg',
                 'mergebursts',
                 'filter', 'unwrap', 'unwrap2stage',
                 'geocode', 'denseoffsets',
                 'filteroffsets', 'geocodeoffsets']

TEMPLATE_DIR = Path(__file__).parent/'templates'


def swap_vrt_if_needed() -> None:
    ref_vrt_list = [str(x) for x in Path('reference').glob('**/*.vrt')]
    sec_vrt_list = [str(x) for x in Path('secondary').glob('**/*.vrt')]
    if len(ref_vrt_list) + len(sec_vrt_list) != 2:
        return None

    for vrt_list in (ref_vrt_list, sec_vrt_list):
        vrt = gdal.Open(vrt_list[0])
        base = gdal.Open(vrt.GetFileList()[1])
        vrt_shape, base_shape = [(x.RasterXSize, x.RasterYSize) for x in (vrt, base)]

        del vrt
        if vrt_shape == base_shape:
            gdal.Translate(vrt_list[0], base, format='VRT')
        del base

    return None


def topsapp_processing(*,
                       reference_slc_zips: list,
                       secondary_slc_zips: list,
                       orbit_directory: str,
                       extent: list,
                       dem_for_proc: str,
                       dem_for_geoc: str,
                       azimuth_looks: int = 7,
                       range_looks: int = 19,
                       swaths: list = None,
                       dry_run: bool = False):
    swaths = swaths or [1, 2, 3]
    # for [ymin, ymax, xmin, xmax]
    extent_isce = [extent[k] for k in [1, 3, 0, 2]]

    # Update PATH with ISCE2 applications
    isce_application_path = Path(f'{site.getsitepackages()[0]}'
                                 '/isce/applications/')
    os.environ['PATH'] += (':' + str(isce_application_path))

    with open(TEMPLATE_DIR/'topsapp_template.xml', 'r') as file:
        template = Template(file.read())

    topsApp_xml = template.render(orbit_directory=orbit_directory,
                                  output_reference_directory='reference',
                                  output_secondary_directory='secondary',
                                  ref_zip_file=reference_slc_zips,
                                  sec_zip_file=secondary_slc_zips,
                                  region_of_interest=extent_isce,
                                  demFilename=dem_for_proc,
                                  geocodeDemFilename=dem_for_geoc,
                                  do_esd=False,
                                  filter_strength=.5,
                                  do_unwrap=True,
                                  use_virtual_files=True,
                                  esd_coherence_threshold=-1,
                                  azimuth_looks=azimuth_looks,
                                  range_looks=range_looks,
                                  swaths=swaths
                                  )
    with open('topsApp.xml', "w") as file:
        file.write(topsApp_xml)

    tops_app_cmd = f'{isce_application_path}/topsApp.py'
    for step in tqdm(TOPSAPP_STEPS, desc='TopsApp Steps'):
        if step == 'computeBaselines':
            swap_vrt_if_needed()

        step_cmd = f'{tops_app_cmd} --dostep={step}'
        result = subprocess.run(step_cmd,
                                shell=True)
        if result.returncode != 0:
            raise ValueError(f'TopsApp failed at step: {step}')
        if dry_run and (step == 'topo'):
            break

    return result.returncode
