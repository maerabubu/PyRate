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
This Python module contains generic utilities and mock objects for use in the
PyRate test suite.
"""

import glob
import os
import shutil
import stat
import itertools
import tempfile
from decimal import Decimal
import pytest
from typing import Iterable, Union
from os.path import join
from subprocess import check_output, run
from pathlib import Path

import numpy as np
from numpy import isnan, sum as nsum
from osgeo import gdal

import pyrate.constants as C
from pyrate.constants import PYRATEPATH
from pyrate.core import algorithm, ifgconstants as ifc, timeseries, mst, stack
from pyrate.core.shared import (Ifg, nan_and_mm_convert, get_geotiff_header_info,
                                write_output_geotiff, dem_or_ifg)
from pyrate.core import ifgconstants as ifg
from pyrate.core import roipac
from pyrate.configuration import Configuration, parse_namelist

PYTHON_VERSION = check_output(["python", "--version"]).decode(encoding="utf-8").strip().split(" ")[1][:3]

PYTHON3P7 = True if PYTHON_VERSION == '3.7' else False
PYTHON3P8 = True if PYTHON_VERSION == '3.8' else False
PYTHON3P9 = True if PYTHON_VERSION == '3.9' else False

GDAL_VERSION = check_output(["gdal-config", "--version"]).decode(encoding="utf-8").split('\n')[0]
GITHUB_ACTIONS = True if ('GITHUB_ACTIONS' in os.environ) else False

# python3.7 and gdal3.0.2
PY37GDAL302 = PYTHON3P7 and (GDAL_VERSION == '3.0.2')
# python3.7 and gdal3.0.4
PY37GDAL304 = PYTHON3P7 and (GDAL_VERSION == '3.0.4')


TEMPDIR = tempfile.gettempdir()
TESTDIR = join(PYRATEPATH, 'tests')
BASE_TEST = join(PYRATEPATH, "tests", "test_data")
SML_TEST_DIR = join(BASE_TEST, "small_test")
ROIPAC_SML_TEST_DIR = join(SML_TEST_DIR, 'roipac_obs')  # roipac processed unws
SML_TEST_OUT = join(SML_TEST_DIR, 'out')
SML_TEST_TIF = join(SML_TEST_DIR, 'tif')
GAMMA_SML_TEST_DIR = join(SML_TEST_DIR, 'gamma_obs')  # gamma processed unws
SML_TEST_CONF = join(SML_TEST_DIR, 'conf')
SML_TEST_LINRATE = join(SML_TEST_DIR, 'linrate')
SML_TEST_GAMMA_HEADER_LIST = join(GAMMA_SML_TEST_DIR, 'headers')
SML_TEST_ROIPAC_HEADER_LIST = join(ROIPAC_SML_TEST_DIR, 'headers')

SML_TEST_DEM_DIR = join(SML_TEST_DIR, 'dem')
SML_TEST_LEGACY_PREPIFG_DIR = join(SML_TEST_DIR, 'prepifg_output')
SML_TEST_LEGACY_ORBITAL_DIR = join(SML_TEST_DIR, 'orbital_error_correction')
SML_TEST_DEM_ROIPAC = join(ROIPAC_SML_TEST_DIR, 'roipac_test_trimmed.dem')
SML_TEST_DEM_GAMMA = join(GAMMA_SML_TEST_DIR, '20060619_utm.dem')
SML_TEST_INCIDENCE = join(GAMMA_SML_TEST_DIR, '20060619_utm.inc')
SML_TEST_ELEVATION = join(GAMMA_SML_TEST_DIR, '20060619_utm.lv_theta')
SML_TEST_DEM_HDR_GAMMA = join(GAMMA_SML_TEST_DIR, '20060619_utm_dem.par')
SML_TEST_DEM_HDR = join(ROIPAC_SML_TEST_DIR, 'roipac_test_trimmed.dem.rsc')
SML_TEST_DEM_TIF = join(SML_TEST_DEM_DIR, 'roipac_test_trimmed.tif')

SML_TEST_COH_DIR = join(SML_TEST_DIR, 'coherence')
SML_TEST_COH_LIST = join(SML_TEST_COH_DIR, 'coherence_17')

SML_TEST_BASE_LIST = join(GAMMA_SML_TEST_DIR, 'baseline_17')

SML_TEST_LT_FILE = join(GAMMA_SML_TEST_DIR, 'cropped_lookup_table.lt')

TEST_CONF_ROIPAC = join(SML_TEST_CONF, 'pyrate_roipac_test.conf')
TEST_CONF_GAMMA = join(SML_TEST_CONF, 'pyrate_gamma_test.conf')

system_test_dir = PYRATEPATH.joinpath("tests", "test_data", "system")
ROIPAC_SYSTEM_FILES = system_test_dir.joinpath("roipac")
ROIPAC_SYSTEM_CONF = ROIPAC_SYSTEM_FILES.joinpath("input_parameters.conf")

GAMMA_SYSTEM_FILES = system_test_dir.joinpath("gamma")
GAMMA_SYSTEM_CONF = GAMMA_SYSTEM_FILES.joinpath("input_parameters.conf")

GEOTIF_SYSTEM_FILES = system_test_dir.joinpath("geotiff")
GEOTIF_SYSTEM_CONF = GEOTIF_SYSTEM_FILES.joinpath("input_parameters.conf")

PREP_TEST_DIR = join(BASE_TEST, 'prepifg')
PREP_TEST_OBS = join(PREP_TEST_DIR, 'obs')
PREP_TEST_TIF = join(PREP_TEST_DIR, 'tif')

HEADERS_TEST_DIR = join(BASE_TEST, 'headers')
INCID_TEST_DIR = join(BASE_TEST, 'incidence')

GAMMA_TEST_DIR = join(BASE_TEST, "gamma")

MEXICO_CROPA_DIR = join(BASE_TEST, "cropA", "geotiffs")
MEXICO_CROPA_DIR_GEOMETRY = join(BASE_TEST, "cropA", "geometry")
MEXICO_CROPA_DIR_HEADERS = join(BASE_TEST, "cropA", "headers")
MEXICO_CROPA_DIR_DEM_ERROR = join(BASE_TEST, "cropA", "dem_error_result")
MEXICO_CROPA_CONF = PYRATEPATH.joinpath("tests", "test_data", "cropA", "pyrate_mexico_cropa.conf")

#: STR; Name of directory containing input interferograms for certian tests
WORKING_DIR = 'working_dir'

# small dummy ifg list to limit overall # of ifgs
IFMS5 = """geo_060828-061211_unw.tif
geo_061106-061211_unw.tif
geo_061106-070115_unw.tif
geo_061106-070326_unw.tif
geo_070326-070917_unw.tif
"""

UNWS5 = """geo_060828-061211.unw
geo_061106-061211.unw
geo_061106-070115.unw
geo_061106-070326.unw
geo_070326-070917.unw
"""

IFMS16 = [
    "geo_060619-061002_unw.tif",
    "geo_060828-061211_unw.tif",
    "geo_061002-070219_unw.tif",
    "geo_061002-070430_unw.tif",
    "geo_061106-061211_unw.tif",
    "geo_061106-070115_unw.tif",
    "geo_061106-070326_unw.tif",
    "geo_061211-070709_unw.tif",
    "geo_061211-070813_unw.tif",
    "geo_070115-070326_unw.tif",
    "geo_070115-070917_unw.tif",
    "geo_070219-070430_unw.tif",
    "geo_070219-070604_unw.tif",
    "geo_070326-070917_unw.tif",
    "geo_070430-070604_unw.tif",
    "geo_070604-070709_unw.tif",
]


def remove_tifs(path):
    tifs = glob.glob(os.path.join(path, '*.tif'))
    for tif in tifs:
        os.remove(tif)


def small_data_setup(datafiles=None, is_dir=False):
    """Returns Ifg objs for the files in the small test dir
    input phase data is in radians; these ifgs are in radians - not converted to mm"""
    if is_dir:
        datafiles = glob.glob(join(datafiles, "*.tif"))
    else:
        if datafiles:
            for i, d in enumerate(datafiles):
                datafiles[i] = os.path.join(SML_TEST_TIF, d)
        else:
            datafiles = glob.glob(join(SML_TEST_TIF, "*.tif"))
    datafiles.sort()
    ifgs = [dem_or_ifg(i) for i in datafiles]
    
    for i in ifgs: 
        i.open()
        i.nodata_value = 0

    return ifgs


def assert_tifs_equal(tif1, tif2):
    mds = gdal.Open(tif1)
    sds = gdal.Open(tif2)

    md_mds = mds.GetMetadata()
    md_sds = sds.GetMetadata()
    # meta data equal
    for k, v in md_sds.items():
        if k in [ifg.PYRATE_ALPHA, ifg.PYRATE_MAXVAR]:
            print(k, v, md_mds[k])
            assert round(eval(md_sds[k]), 1) == round(eval(md_mds[k]), 1)
        else:
            assert md_sds[k] == md_mds[k]
    # assert md_mds == md_sds
    d1 = mds.ReadAsArray()
    d2 = sds.ReadAsArray()
    # phase equal
    np.testing.assert_array_almost_equal(d1,  d2, decimal=3)

    mds = None  # close datasets
    sds = None


def copy_small_ifg_file_list():
    temp_dir = tempfile.mkdtemp()
    move_files(SML_TEST_TIF, temp_dir, file_type='*.tif', copy=True)
    datafiles = glob.glob(join(temp_dir, "*.tif"))
    for d in datafiles:
        Path(d).chmod(0o664)  # assign write permission as conv2tif output is readonly
    return temp_dir, datafiles


def copy_and_setup_small_data():
    temp_dir, datafiles = copy_small_ifg_file_list()
    datafiles.sort()
    ifgs = [dem_or_ifg(i) for i in datafiles]

    for i in ifgs:
        i.open()
        i.nodata_value = 0
    return temp_dir, ifgs


def small_ifg_file_list(datafiles=None):
    """Returns the file list of all the .tif files after prepifg conversion
    input phase data is in radians; these ifgs are in radians - not converted to mm"""
    if datafiles:
        for i, d in enumerate(datafiles):
            datafiles[i] = os.path.join(SML_TEST_TIF, d)
    else:
        datafiles = glob.glob(join(SML_TEST_TIF, "*.tif"))
    datafiles.sort()
    return datafiles


def small_data_roipac_unws():
    """Returns unw file list before prepifg operation
    input phase data is in radians; these ifgs are in radians - not converted to mm"""
    return glob.glob(join(ROIPAC_SML_TEST_DIR, "*.unw"))


def small_data_setup_gamma_unws():
    """Returns unw file list before prepifg operation
    input phase data is in radians; these ifgs are in radians - not converted to mm"""
    return glob.glob(join(GAMMA_SML_TEST_DIR, "*.unw"))


def small5_ifgs():
    """Convenience func to return a subset of 5 linked Ifgs from the testdata"""
    new_data_paths = small5_ifg_paths()

    return [Ifg(p) for p in new_data_paths]


def small5_ifg_paths():
    BASE_DIR = tempfile.mkdtemp()
    data_paths = [os.path.join(SML_TEST_TIF, p) for p in IFMS5.split()]
    new_data_paths = [os.path.join(BASE_DIR, os.path.basename(d))
                      for d in data_paths]
    for d in data_paths:
        shutil.copy(d, os.path.join(BASE_DIR, os.path.basename(d)))
    return new_data_paths


def small5_mock_ifgs(xs=3, ys=4):
    '''Returns smaller mocked version of small Ifgs for testing'''
    ifgs = small5_ifgs()
    for i in ifgs:
        i.open()
        i.nodata_value = 0

    return [MockIfg(i, xs, ys) for i in ifgs]


class MockIfg(object):
    """Mock Ifg for detailed testing"""

    def __init__(self, ifg, xsize=None, ysize=None):
        """
        Creates mock Ifg based on a given interferogram. Size args specify the
        dimensions of the phase band (so the mock ifg can be resized differently
        to the source interferogram for smaller test datasets).
        """
        self.dataset = ifg.dataset
        self.first = ifg.first
        self.second = ifg.second
        self.data_path = ifg.data_path
        self.nrows = ysize
        self.ncols = xsize
        self.x_size = ifg.x_size
        self.y_size = ifg.y_size
        self.x_step = ifg.x_step
        self.y_step = ifg.y_step
        self.num_cells = self.ncols * self.nrows
        self.phase_data = ifg.phase_data[:ysize, :xsize]
        self.nan_fraction = ifg.nan_fraction # use existing overall nan fraction
        self.is_open = False

    def __repr__(self, *args, **kwargs):
        return 'MockIfg: %s -> %s' % (self.first, self.second)

    def open(self):
        # TODO: could move some of the init code here to mimic Ifgs
        pass  # can't actually open anything!

    @property
    def nan_count(self):
        return nsum(isnan(self.phase_data))

    @property
    def shape(self):
        return self.nrows, self.ncols

    def write_modified_phase(self):  #dummy
        pass

    def close(self):  # dummy
        pass


def reconstruct_stack_rate(shape, tiles, output_dir, out_type):
    rate = np.zeros(shape=shape, dtype=np.float32)
    for t in tiles:
        rate_file = os.path.join(output_dir, out_type +
                                 '_{}.npy'.format(t.index))
        rate_tile = np.load(file=rate_file)
        rate[t.top_left_y:t.bottom_right_y,
             t.top_left_x:t.bottom_right_x] = rate_tile
    return rate


def reconstruct_mst(shape, tiles, output_dir):
    mst_file_0 = os.path.join(output_dir, C.MST_DIR, 'mst_mat_{}.npy'.format(0))
    shape0 = np.load(mst_file_0).shape[0]

    mst = np.empty(shape=((shape0,) + shape), dtype=np.float32)
    for i, t in enumerate(tiles):
        mst_file_n = os.path.join(output_dir, C.MST_DIR, 'mst_mat_{}.npy'.format(i))
        mst[:, t.top_left_y:t.bottom_right_y,
                t.top_left_x: t.bottom_right_x] = np.load(mst_file_n)
    return mst


def move_files(source_dir, dest_dir, file_type='*.tif', copy=False):
    for filename in glob.glob(os.path.join(source_dir, file_type)):
        if copy:
            shutil.copy(filename, dest_dir)
        else:
            shutil.move(filename, dest_dir)


def assert_ifg_phase_equal(ifg_path1, ifg_path2):
    ds1 = gdal.Open(ifg_path1)
    ds2 = gdal.Open(ifg_path2)
    np.testing.assert_array_almost_equal(ds1.ReadAsArray(), ds2.ReadAsArray())
    ds1 = None
    ds2 = None


def prepare_ifgs_without_phase(ifg_paths, params):
    ifgs = [Ifg(p) for p in ifg_paths]
    for i in ifgs:
        i.open(readonly=False)
        nan_conversion = params[C.NAN_CONVERSION]
        if nan_conversion:  # nan conversion happens here in networkx mst
            # if not ifg.nan_converted:
            i.nodata_value = params[C.NO_DATA_VALUE]
            i.convert_to_nans()
    return ifgs


def mst_calculation(ifg_paths_or_instance, params):
    if isinstance(ifg_paths_or_instance, list):
        ifgs = pre_prepare_ifgs(ifg_paths_or_instance, params)
        mst_grid = mst.mst_parallel(ifgs, params)
        # write mst output to a file
        mst_mat_binary_file = join(params[C.OUT_DIR], 'mst_mat')
        np.save(file=mst_mat_binary_file, arr=mst_grid)

        for i in ifgs:
            i.close()
        return mst_grid
    return None


def get_nml(ifg_list_instance, nodata_value, nan_conversion=False):
    """
    :param xxx(eg str, tuple, int, float...) ifg_list_instance: xxxx
    :param float nodata_value: No data value in image
    :param bool nan_conversion: Convert NaNs
    
    :return: ifg_list_instance: replaces in place
    :rtype: list
    :return: _epoch_list: list of epochs
    :rtype: list
    """
    _epoch_list, n = algorithm.get_epochs(ifg_list_instance.ifgs)
    ifg_list_instance.reshape_n(n)
    if nan_conversion:
        ifg_list_instance.update_nan_frac(nodata_value)
        # turn on for nan conversion
        ifg_list_instance.convert_nans(nan_conversion=nan_conversion)
    ifg_list_instance.make_data_stack()
    return ifg_list_instance, _epoch_list


def compute_time_series(ifgs, mst_grid, params, vcmt):
    # Calculate time series
    tsincr, tscum, tsvel = calculate_time_series(
        ifgs, params, vcmt=vcmt, mst=mst_grid)

    # tsvel_file = join(params[cf.OUT_DIR], 'tsvel.npy')
    tsincr_file = join(params[C.OUT_DIR], 'tsincr.npy')
    tscum_file = join(params[C.OUT_DIR], 'tscum.npy')
    np.save(file=tsincr_file, arr=tsincr)
    np.save(file=tscum_file, arr=tscum)
    # np.save(file=tsvel_file, arr=tsvel)

    # TODO: write tests for these functions
    write_timeseries_geotiff(ifgs, params, tsincr, pr_type='tsincr')
    write_timeseries_geotiff(ifgs, params, tscum, pr_type='tscuml')
    # write_timeseries_geotiff(ifgs, params, tsvel, pr_type='tsvel')
    return tsincr, tscum, tsvel


def calculate_time_series(ifgs, params, vcmt, mst):
    res = timeseries.time_series(ifgs, params, vcmt, mst)
    for r in res:
        if len(r.shape) != 3:
            raise timeseries.TimeSeriesError

    tsincr, tscum, tsvel = res
    return tsincr, tscum, tsvel


def write_timeseries_geotiff(ifgs, params, tsincr, pr_type):
    # setup metadata for writing into result files
    gt, md, wkt = get_geotiff_header_info(ifgs[0].data_path)
    epochlist = algorithm.get_epochs(ifgs)[0]

    for i in range(tsincr.shape[2]):
        md[ifc.EPOCH_DATE] = epochlist.dates[i + 1]
        md['SEQUENCE_POSITION'] = i+1  # sequence position

        data = tsincr[:, :, i]
        dest = join(params[C.OUT_DIR], pr_type + "_" +
                    str(epochlist.dates[i + 1]) + ".tif")
        md[ifc.DATA_TYPE] = pr_type
        write_output_geotiff(md, gt, wkt, data, dest, np.nan)


def calculate_stack_rate(ifgs, params, vcmt, mst_mat=None):
    # log.info('Calculating stacked rate')
    res = stack.stack_rate_array(ifgs, params, vcmt, mst_mat)
    for r in res:
        if r is None:
            raise ValueError('TODO: bad value')

    r, e, samples = res
    rate, error = stack.mask_rate(r, e, params['maxsig'])
    write_stackrate_tifs(ifgs, params, res)
    # log.info('Stacked rate calculated')
    return rate, error, samples


def write_stackrate_tifs(ifgs, params, res):
    rate, error, samples = res
    gt, md, wkt = get_geotiff_header_info(ifgs[0].data_path)
    epochlist = algorithm.get_epochs(ifgs)[0]
    dest = join(params[C.OUT_DIR], "stack_rate.tif")
    md[ifc.EPOCH_DATE] = epochlist.dates
    md[ifc.DATA_TYPE] = ifc.STACKRATE
    write_output_geotiff(md, gt, wkt, rate, dest, np.nan)
    dest = join(params[C.OUT_DIR], "stack_error.tif")
    md[ifc.DATA_TYPE] = ifc.STACKERROR
    write_output_geotiff(md, gt, wkt, error, dest, np.nan)
    dest = join(params[C.OUT_DIR], "stack_samples.tif")
    md[ifc.DATA_TYPE] = ifc.STACKSAMP
    write_output_geotiff(md, gt, wkt, samples, dest, np.nan)
    write_stackrate_numpy_files(error, rate, samples, params)


def write_stackrate_numpy_files(error, rate, samples, params):
    rate_file = join(params[C.OUT_DIR], 'rate.npy')
    error_file = join(params[C.OUT_DIR], 'error.npy')
    samples_file = join(params[C.OUT_DIR], 'samples.npy')
    np.save(file=rate_file, arr=rate)
    np.save(file=error_file, arr=error)
    np.save(file=samples_file, arr=samples)


def copytree(src: Union[str, bytes, os.PathLike], dst: Union[str, bytes, os.PathLike], symlinks=False, ignore=None):
    # pylint: disable=line-too-long
    """
    Copy entire contents of src directory into dst directory.
    See: http://stackoverflow.com/questions/1868714/how-do-i-copy-an-entire-directory-of-files-into-an-existing-directory-using-pyth?lq=1

    :param str src: source directory path
    :param str dst: destination directory path (created if does not exist)
    :param bool symlinks: Whether to copy symlink or not
    :param bool ignore:
    """
    # pylint: disable=invalid-name
    if not os.path.exists(dst):  # pragma: no cover
        os.makedirs(dst)
    shutil.copystat(src, dst)
    lst = os.listdir(src)
    if ignore:
        excl = ignore(src, lst)
        lst = [x for x in lst if x not in excl]
    for item in lst:
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if symlinks and os.path.islink(s):  # pragma: no cover
            if os.path.lexists(d):
                os.remove(d)
            os.symlink(os.readlink(s), d)
            try:
                st = os.lstat(s)
                mode = stat.S_IMODE(st.st_mode)
                os.lchmod(d, mode)
            except AttributeError:
                pass  # lchmod not available
        elif os.path.isdir(s):  # pragma: no cover
            copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def repair_params_for_correct_tests(out_dir, params):
    base_ifg_paths = [d.unwrapped_path for d in params[C.INTERFEROGRAM_FILES]]
    headers = [roipac.roipac_header(i, params) for i in base_ifg_paths]
    params[C.INTERFEROGRAM_FILES] = params[C.INTERFEROGRAM_FILES][:-2]
    dest_paths = [Path(out_dir).joinpath(Path(d.sampled_path).name).as_posix()
                  for d in params[C.INTERFEROGRAM_FILES]]
    for p, d in zip(params[C.INTERFEROGRAM_FILES], dest_paths):  # hack
        p.sampled_path = d
    return dest_paths, headers


def pre_prepare_ifgs(ifg_paths, params):
    """
    nan and mm convert ifgs
    """
    ifgs = [Ifg(p) for p in ifg_paths]
    for i in ifgs:
        i.open(readonly=False)
        nan_and_mm_convert(i, params)
    return ifgs


def assert_two_dirs_equal(dir1, dir2, ext, num_files=None):
    if not isinstance(ext, list):
        ext = [ext]
    dir1_files = list(itertools.chain(* [list(Path(dir1).glob(ex)) for ex in ext]))
    dir2_files = list(itertools.chain(* [list(Path(dir2).glob(ex)) for ex in ext]))
    dir1_files.sort()
    dir2_files.sort()
    # 17 unwrapped geotifs
    # 17 cropped multilooked tifs + 1 dem
    if num_files is not None:
        assert len(dir1_files) == num_files
        assert len(dir2_files) == num_files
    else:
        assert len(dir1_files) == len(dir2_files)
    if dir1_files[0].suffix == '.tif':
        for m_f, s_f in zip(dir1_files, dir2_files):
            assert m_f.name == s_f.name
            assert_tifs_equal(m_f.as_posix(), s_f.as_posix())

    elif dir1_files[0].suffix == '.npy':
        for m_f, s_f in zip(dir1_files, dir2_files):
            assert m_f.name == s_f.name
            np.testing.assert_array_almost_equal(np.load(m_f), np.load(s_f), decimal=3)
    elif dir1_files[0].suffix in {'.kml', '.png'}:
        return
    else:
        raise


def assert_same_files_produced(dir1, dir2, dir3, ext, num_files=None):
    assert_two_dirs_equal(dir1, dir2, ext, num_files)
    assert_two_dirs_equal(dir1, dir3, ext, num_files)


working_dirs = {
    GAMMA_SYSTEM_CONF: GAMMA_SYSTEM_FILES,
    ROIPAC_SYSTEM_CONF: ROIPAC_SYSTEM_FILES,
    GEOTIF_SYSTEM_CONF: GEOTIF_SYSTEM_FILES,
    Path(TEST_CONF_ROIPAC).name: ROIPAC_SML_TEST_DIR,
    Path(TEST_CONF_GAMMA).name: GAMMA_SML_TEST_DIR
}


def manipulate_test_conf(conf_file, work_dir: Path):
    params = Configuration(conf_file).__dict__
    if conf_file == MEXICO_CROPA_CONF:
        copytree(MEXICO_CROPA_DIR, work_dir)
        copytree(MEXICO_CROPA_DIR_HEADERS, work_dir)
        copytree(MEXICO_CROPA_DIR_GEOMETRY, work_dir)
        copytree(MEXICO_CROPA_DIR_DEM_ERROR, work_dir)
        shutil.copy2(params[C.IFG_FILE_LIST], work_dir)
        shutil.copy2(params[C.HDR_FILE_LIST], work_dir)
        shutil.copy2(params[C.COH_FILE_LIST], work_dir)
        shutil.copy2(params[C.BASE_FILE_LIST], work_dir)
        for m_path in params[C.INTERFEROGRAM_FILES]:
            m_path.converted_path = work_dir.joinpath(Path(m_path.converted_path).name).as_posix()
    else:  # legacy unit test data
        params[WORKING_DIR] = working_dirs[Path(conf_file).name]
        copytree(params[WORKING_DIR], work_dir)

    params[WORKING_DIR] = work_dir.as_posix()
    # manipulate params
    outdir = work_dir.joinpath('out')
    outdir.mkdir(exist_ok=True)
    params[C.OUT_DIR] = outdir.as_posix()
    params[C.TEMP_MLOOKED_DIR] = outdir.joinpath(C.TEMP_MLOOKED_DIR).as_posix()
    params[C.DEM_FILE] = work_dir.joinpath(Path(params[C.DEM_FILE]).name).as_posix()
    params[C.DEM_HEADER_FILE] = work_dir.joinpath(Path(params[C.DEM_HEADER_FILE]).name).as_posix()
    params[C.HDR_FILE_LIST] = work_dir.joinpath(Path(params[C.HDR_FILE_LIST]).name).as_posix()
    params[C.IFG_FILE_LIST] = work_dir.joinpath(Path(params[C.IFG_FILE_LIST]).name).as_posix()
    params[C.TMPDIR] = outdir.joinpath(C.TMPDIR).as_posix()
    params[C.COHERENCE_DIR] = outdir.joinpath(C.COHERENCE_DIR).as_posix()
    params[C.GEOMETRY_DIR] = outdir.joinpath(C.GEOMETRY_DIR).as_posix()
    params[C.APS_ERROR_DIR] = outdir.joinpath(C.APS_ERROR_DIR).as_posix()
    params[C.MST_DIR] = outdir.joinpath(C.MST_DIR).as_posix()
    params[C.ORB_ERROR_DIR] = outdir.joinpath(C.ORB_ERROR_DIR).as_posix()
    params[C.PHASE_CLOSURE_DIR] = outdir.joinpath(C.PHASE_CLOSURE_DIR).as_posix()
    params[C.DEM_ERROR_DIR] = outdir.joinpath(C.DEM_ERROR_DIR).as_posix()
    params[C.INTERFEROGRAM_DIR] = outdir.joinpath(C.INTERFEROGRAM_DIR).as_posix()
    params[C.VELOCITY_DIR] = outdir.joinpath(C.VELOCITY_DIR).as_posix()
    params[C.TIMESERIES_DIR] = outdir.joinpath(C.TIMESERIES_DIR).as_posix()

    return params


class UnitTestAdaptation:
    @staticmethod
    def assertEqual(arg1, arg2):
        assert arg1 == arg2

    @staticmethod
    def assertTrue(arg, msg=''):
        assert arg, msg

    @staticmethod
    def assertFalse(arg, msg=''):
        assert ~ arg, msg

    @staticmethod
    def assertIsNotNone(arg, msg=''):
        assert arg is not None, msg

    @staticmethod
    def assertIsNone(arg, msg=''):
        assert arg is None, msg

    @staticmethod
    def assertDictEqual(d1: dict, d2: dict):
        assert d1 == d2

    @staticmethod
    def assertRaises(excpt: Exception, func, *args, **kwargs):
        with pytest.raises(excpt):
            func(*args, **kwargs)

    @staticmethod
    def assertIn(item, s: Iterable):
        assert item in s

    @staticmethod
    def assertAlmostEqual(arg1, arg2, places=7):
        places *= -1
        num = Decimal((0, (1, ), places))
        assert arg1 == pytest.approx(arg2, abs=num)


def min_params(out_dir):
    params = {}
    params[C.OUT_DIR] = out_dir
    params[C.IFG_LKSX] = 1
    params[C.IFG_LKSY] = 1
    params[C.IFG_CROP_OPT] = 4
    params[C.TEMP_MLOOKED_DIR] = Path(tempfile.mkdtemp())
    params[C.ORBFIT_OFFSET] = 1
    params[C.ORBITAL_FIT_METHOD] = 1
    params[C.ORBITAL_FIT_DEGREE] = 2
    params[C.ORBITAL_FIT_LOOKS_X] = 1
    params[C.ORBITAL_FIT_LOOKS_Y] = 1
    return params


def sub_process_run(cmd, *args, **kwargs):
    return run(cmd, *args, shell=True, check=True, **kwargs)


def original_ifg_paths(ifglist_path, working_dir):
    """
    Returns sequence of paths to files in given ifglist file.

    Args:
        ifglist_path: Absolute path to interferogram file list.
        working_dir: Absolute path to observations directory.

    Returns:
        list: List of full paths to interferogram files.
    """
    ifglist = parse_namelist(ifglist_path)
    return [os.path.join(working_dir, p) for p in ifglist]
