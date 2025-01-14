#   This Python module is part of the PyRate software package.
#
#   Copyright 2021 Geoscience Australia
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
"""
This Python module contains tests that compare GAMMA and ROI_PAC
functionality in PyRate.
"""
import os
import shutil
import pytest
from pathlib import Path

import pyrate.configuration
import pyrate.constants as C
from pyrate.core.shared import DEM
from pyrate.core import ifgconstants as ifc
from pyrate.core.prepifg_helper import _is_number
from pyrate import prepifg, conv2tif, configuration
from tests.common import SML_TEST_DIR, small_data_setup, copytree, TEST_CONF_ROIPAC, TEST_CONF_GAMMA, working_dirs, \
    WORKING_DIR


SMLNEY_GAMMA_TEST = os.path.join(SML_TEST_DIR, "gamma_obs")


def test_files_are_same(tempdir, get_config):
    roipac_params = get_config(TEST_CONF_ROIPAC)
    roipac_tdir = Path(tempdir())
    roipac_params[WORKING_DIR] = working_dirs[Path(TEST_CONF_ROIPAC).name]
    roipac_params = __workflow(roipac_params, roipac_tdir)

    gamma_params = get_config(TEST_CONF_GAMMA)
    gamma_tdir = Path(tempdir())
    gamma_params[WORKING_DIR] = working_dirs[Path(TEST_CONF_GAMMA).name]
    gamma_params = __workflow(gamma_params, gamma_tdir)

    # conv2tif output equal
    __assert_same_files_produced(roipac_params[C.INTERFEROGRAM_DIR], gamma_params[C.INTERFEROGRAM_DIR], "*_unw.tif", 17)

    # prepifg output equal
    __assert_same_files_produced(roipac_params[C.INTERFEROGRAM_DIR], gamma_params[C.INTERFEROGRAM_DIR], f"*_ifg.tif", 17)

    __assert_same_files_produced(roipac_params[C.GEOMETRY_DIR], gamma_params[C.GEOMETRY_DIR], "dem.tif", 1)

    # clean up
    shutil.rmtree(roipac_params[WORKING_DIR])
    shutil.rmtree(gamma_params[WORKING_DIR])


def __workflow(params, tdir):
    copytree(params[WORKING_DIR], tdir)
    # manipulate params
    outdir = tdir.joinpath('out')
    outdir.mkdir(exist_ok=True)
    params[C.OUT_DIR] = outdir.as_posix()

    params[C.DEM_FILE] = tdir.joinpath(Path(params[C.DEM_FILE]).name).as_posix()
    params[C.DEM_HEADER_FILE] = tdir.joinpath(Path(params[C.DEM_HEADER_FILE]).name).as_posix()
    params[C.HDR_FILE_LIST] = tdir.joinpath(Path(params[C.HDR_FILE_LIST]).name).as_posix()
    params[C.IFG_FILE_LIST] = tdir.joinpath(Path(params[C.IFG_FILE_LIST]).name).as_posix()
    params[C.TMPDIR] = tdir.joinpath(Path(params[C.TMPDIR]).name).as_posix()
    output_conf = tdir.joinpath('roipac_temp.conf')
    pyrate.configuration.write_config_file(params=params, output_conf_file=output_conf)
    params = configuration.Configuration(output_conf).__dict__
    conv2tif.main(params)
    prepifg.main(params)
    params[WORKING_DIR] = tdir.as_posix()
    return params


def __assert_same_files_produced(dir1, dir2, ext, num_files):
    dir1_files = list(Path(dir1).glob(ext))
    dir2_files = list(Path(dir2).glob(ext))
    dir1_files.sort()
    dir2_files.sort()
    # 17 unwrapped geotifs
    # 17 cropped multilooked tifs + 1 dem
    assert len(dir1_files) == num_files
    assert len(dir2_files) == num_files
    c = 0

    all_roipac_ifgs = [f for f in small_data_setup(dir1_files) if not isinstance(f, DEM)]
    all_gamma_ifgs = [f for f in small_data_setup(dir2_files) if not isinstance(f, DEM)]

    for c, (i, j) in enumerate(zip(all_roipac_ifgs, all_gamma_ifgs)):
        mdi = i.meta_data
        mdj = j.meta_data
        for k in mdi:  # all key values equal
            if k == "INCIDENCE_DEGREES":
                pass  # incidence angle not implemented for roipac
            elif _is_number(mdi[k]):
                assert pytest.approx(float(mdj[k]), 0.00001) == float(mdi[k])
            elif mdi[k] == "ROIPAC" or "GAMMA":
                pass  # INSAR_PROCESSOR can not be equal
            else:
                assert mdj[k] == mdi[k]

        if i.data_path.__contains__("_ifg.tif"):
            # these are multilooked tifs
            # test that DATA_STEP is MULTILOOKED
            assert mdi[ifc.DATA_TYPE] == ifc.MULTILOOKED
            assert mdj[ifc.DATA_TYPE] == ifc.MULTILOOKED
        else:
            assert mdi[ifc.DATA_TYPE] == ifc.ORIG
            assert mdj[ifc.DATA_TYPE] == ifc.ORIG
    if not all_gamma_ifgs:  # checking for dem
        return
    assert c + 1 == len(all_gamma_ifgs)
