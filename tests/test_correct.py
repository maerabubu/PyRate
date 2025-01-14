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
This Python module contains tests for the correct.py PyRate module.
"""
import shutil
from pathlib import Path
import pytest

import pyrate.constants as C
from pyrate.configuration import ConfigException, Configuration, write_config_file
from pyrate import correct, prepifg, conv2tif
from tests import common


def test_unsupported_process_steps_raises(gamma_conf):
    config = Configuration(gamma_conf)
    gamma_params = config.__dict__
    gamma_params['correct'] = ['orbfit2', 'something_other_step']
    with pytest.raises(ConfigException):
        correct.correct_ifgs(config)


def test_supported_process_steps_dont_raise(gamma_params):
    supported_stpes = ['orbfit', 'refphase', 'mst', 'apscorrect', 'maxvar', 'demerror', 'phase_closure']
    assert all([s in gamma_params['correct'] for s in supported_stpes])
    correct.__validate_correct_steps(params=gamma_params)


@pytest.mark.slow
@pytest.mark.skipif(not common.PYTHON3P9, reason="Only run in one CI env")
def test_process_treats_prepif_outputs_readonly(gamma_conf, tempdir, coh_mask):
    from pyrate.configuration import Configuration
    tdir = Path(tempdir())
    params = common.manipulate_test_conf(gamma_conf, tdir)
    params[C.COH_MASK] = coh_mask
    params[C.PARALLEL] = 0
    output_conf = tdir.joinpath('conf.cfg')
    write_config_file(params=params, output_conf_file=output_conf)
    params = Configuration(output_conf).__dict__
    conv2tif.main(params)
    tifs = list(Path(params[C.INTERFEROGRAM_DIR]).glob('*_unw.tif'))
    assert len(tifs) == 17

    if params[C.COH_FILE_LIST] is not None:
        coh_tifs = list(Path(params[C.COHERENCE_DIR]).glob('*_cc.tif'))
        assert len(coh_tifs) == 17

    params = Configuration(output_conf).__dict__
    prepifg.main(params)
    cropped_coh = list(Path(params[C.COHERENCE_DIR]).glob('*_coh.tif'))
    cropped_ifgs = list(Path(params[C.INTERFEROGRAM_DIR]).glob('*_ifg.tif'))
    dem_ifgs = list(Path(params[C.GEOMETRY_DIR]).glob('*_dem.tif'))

    if params[C.COH_FILE_LIST] is not None:  # 17 + 1 dem + 17 coh files
        assert len(cropped_coh) + len(cropped_ifgs) + len(dem_ifgs) == 35
    else:  # 17 + 1 dem
        assert len(cropped_coh) + len(cropped_ifgs) + len(dem_ifgs) == 18
    # check all tifs from conv2tif are still readonly
    for t in tifs:
        assert t.stat().st_mode == 33060

    # check all prepifg outputs are readonly
    for c in cropped_coh + cropped_ifgs:
        assert c.stat().st_mode == 33060

    config = Configuration(output_conf)
    correct.main(config)

    # check all after correct steps multilooked files are still readonly
    for c in cropped_coh + cropped_ifgs + dem_ifgs:
        assert c.stat().st_mode == 33060
    shutil.rmtree(params[C.OUT_DIR])
