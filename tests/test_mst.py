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
This module contains tests for the mst.py PyRate module.
"""
import os
import shutil
from itertools import product
from numpy import empty, array, nan, isnan, sum as nsum
import numpy as np

import pyrate.constants as C
from pyrate.core import algorithm, mst
from pyrate.core.shared import IfgPart, Tile, Ifg, save_numpy_phase
from pyrate.configuration import Configuration
from pyrate import conv2tif, prepifg, correct
from tests import common
from tests.common import UnitTestAdaptation, TEST_CONF_GAMMA, MockIfg, small5_mock_ifgs, small_data_setup


class TestMST(UnitTestAdaptation):
    """Basic verification of minimum spanning tree (MST) functionality."""

    def setup_method(self):
        self.ifgs = small_data_setup()

    def test_mst_matrix_as_array(self):
        # Verifies MST matrix func returns array with dict/trees in each cell
        for i in self.ifgs[3:]:
            i.phase_data[0, 1] = 0  # partial stack of NODATA to one cell

        for i in self.ifgs:
            i.convert_to_nans() # zeros to NaN/NODATA

        epochs = algorithm.get_epochs(self.ifgs)[0]
        res = mst._mst_matrix_as_array(self.ifgs)
        ys, xs = res.shape

        for y, x in product(range(ys), range(xs)):
            r = res[y, x]
            num_nodes = len(r)
            self.assertTrue(num_nodes < len(epochs.dates))

            stack = array([i.phase_data[y, x] for i in self.ifgs])  # 17 ifg stack
            self.assertTrue(0 == nsum(stack == 0))  # all 0s should be converted
            nc = nsum(isnan(stack))
            exp_count = len(epochs.dates) - 1

            if nc == 0:
                self.assertEqual(num_nodes, exp_count)
            elif nc > 5:
                # rough test: too many nans must reduce the total tree size
                self.assertTrue(num_nodes <= (17-nc))

    def test_mst_matrix_as_ifgs(self):
        # ensure only ifgs are returned, not individual MST graphs
        ifgs = small5_mock_ifgs()
        nifgs = len(ifgs)
        ys, xs = ifgs[0].shape
        result = mst._mst_matrix_ifgs_only(ifgs)

        for coord in product(range(ys), range(xs)):
            stack = (i.phase_data[coord] for i in self.ifgs)
            nc = nsum([isnan(n) for n in stack])
            check = len(result[coord]) <= (nifgs - nc)
            self.assertTrue(check)

            # HACK: type testing here is a bit grubby
            self.assertTrue(all([isinstance(i, MockIfg) for i in ifgs]))

    def test_partial_nan_pixel_stack(self):
        # Ensure a limited # of coherent cells results in a smaller MST tree
        num_coherent = 3

        def assert_equal():
            res = mst._mst_matrix_as_array(mock_ifgs)
            self.assertEqual(len(res[0,0]), num_coherent)

        mock_ifgs = [MockIfg(i, 1, 1) for i in self.ifgs]
        for m in mock_ifgs[num_coherent:]:
            m.phase_data[:] = nan
        assert_equal()

        # fill in more nans leaving only one ifg
        for m in mock_ifgs[1:num_coherent]:
            m.phase_data[:] = nan
        num_coherent = 1
        assert_equal()

    def test_all_nan_pixel_stack(self):
        # ensure full stack of NaNs in an MST pixel classifies to NaN
        mock_ifgs = [MockIfg(i, 1, 1) for i in self.ifgs]
        for m in mock_ifgs:
            m.phase_data[:] = nan

        res = mst._mst_matrix_as_array(mock_ifgs)
        exp = empty((1, 1))  # , dtype=object)
        exp[:] = nan

        shape = (mock_ifgs[0].nrows, mock_ifgs[0].ncols)
        self.assertTrue(res.shape == shape)
        self.assertTrue(res.shape == exp.shape)
        self.assertTrue(isnan(res[0][0]) and isnan(exp[0][0]))


class TestDefaultMST(UnitTestAdaptation):

    def test_default_mst(self):
        # default MST from full set of Ifgs shouldn't drop any nodes
        ifgs = small5_mock_ifgs()
        dates = [(i.first, i.second) for i in ifgs]

        res = mst.mst_from_ifgs(ifgs)[0]
        num_edges = len(res)
        self.assertEqual(num_edges, len(ifgs))

        # test edges, note node order can be reversed
        for edge in res:
            self.assertTrue(edge in dates or (edge[1], edge[0]) in dates)

        # check all nodes exist in this default tree
        mst_dates = set(res)
        mst_dates = list(sum(mst_dates, ()))
        for i in ifgs:
            for node in (i.first, i.second):
                self.assertIn(node, mst_dates)


class TestNetworkxMSTTreeCheck(UnitTestAdaptation):

    @classmethod
    def setup_class(cls):
        cls.ifgs = small_data_setup()

    def test_assert_is_not_tree(self):
        non_overlapping = [1, 2, 5, 6, 12, 13, 14, 15, 16, 17]
        ifgs_non_overlapping = [ifg for i, ifg in enumerate(self.ifgs) if i + 1 in non_overlapping]
        edges, is_tree, ntrees, _ = mst.mst_from_ifgs(ifgs_non_overlapping)
        self.assertFalse(is_tree)
        self.assertEqual(4, ntrees)

    def test_small_data_tree(self):
        self.assertTrue(mst.mst_from_ifgs(self.ifgs)[1])

    def test_assert_is_tree(self):
        overlapping = [1, 2, 3, 4, 6, 7, 10, 11, 16, 17]

        ifgs_overlapping = [ifg for i, ifg in enumerate(self.ifgs) if (i + 1 in overlapping)]
        edges, is_tree, ntrees, _ = mst.mst_from_ifgs(ifgs_overlapping)
        self.assertFalse(is_tree)
        self.assertEqual(4, ntrees)

    def test_assert_two_trees_overlapping(self):
        overlapping = [3, 4, 5, 6, 7, 8, 9, 10, 11, 16, 17]

        ifgs_overlapping = [ifg for i, ifg in enumerate(self.ifgs) if (i + 1 in overlapping)]
        edges, is_tree, ntrees, _ = mst.mst_from_ifgs(ifgs_overlapping)
        self.assertFalse(is_tree)
        self.assertEqual(2, ntrees)

    def test_assert_two_trees_non_overlapping(self):
        non_overlapping = [2, 5, 6, 12, 13, 15]
        ifgs_non_overlapping = [ifg for i, ifg in enumerate(self.ifgs) if i + 1 in non_overlapping]
        edges, is_tree, ntrees, _ = mst.mst_from_ifgs(ifgs_non_overlapping)
        self.assertFalse(is_tree)
        self.assertEqual(2, ntrees)


class TestIfgPart(UnitTestAdaptation):

    def setup_method(self):
        self.ifgs = small_data_setup()
        self.params = Configuration(common.TEST_CONF_ROIPAC).__dict__

    def test_ifg_part_shape_and_slice(self):
        r_start = 0
        r_end = 10
        for i in self.ifgs:
            tile = Tile(0, top_left=(r_start, 0), bottom_right=(r_end, i.ncols))
            ifg_part = IfgPart(i.data_path, tile, params=self.params)
            self.assertEqual(ifg_part.phase_data.shape, (r_end-r_start, i.phase_data.shape[1]))
            np.testing.assert_array_equal(ifg_part.phase_data, i.phase_data[r_start:r_end, :])

    def test_mst_multiprocessing_serial(self):
        self.params[C.PARALLEL] = False
        original_mst = mst.mst_boolean_array(self.ifgs)
        parallel_mst = mst.mst_parallel(self.ifgs, params=self.params)
        np.testing.assert_array_equal(original_mst, parallel_mst)

    def test_mst_multiprocessing(self):
        self.params[C.PARALLEL] = True
        original_mst = mst.mst_boolean_array(self.ifgs)
        parallel_mst = mst.mst_parallel(self.ifgs, params=self.params)
        np.testing.assert_array_equal(original_mst, parallel_mst)


class TestMSTFilesReusedFromDisc:

    @classmethod
    def setup_class(cls):
        cls.conf = TEST_CONF_GAMMA
        cls.params = Configuration(cls.conf).__dict__
        conv2tif.main(cls.params)
        cls.params = Configuration(cls.conf).__dict__
        prepifg.main(cls.params)
        cls.params = Configuration(cls.conf).__dict__
        multi_paths = cls.params[C.INTERFEROGRAM_FILES]
        cls.ifg_paths = [p.tmp_sampled_path for p in multi_paths]

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(cls.params[C.OUT_DIR])

    def test_mst_used_from_disc_on_rerun(self):
        correct._copy_mlooked(self.params)
        correct._update_params_with_tiles(self.params)
        times_written = self.__run_once()
        times_written_1 = self.__run_once()

        np.testing.assert_array_equal(times_written_1, times_written)

    def __run_once(self):
        tiles = self.params[C.TILES]
        mst_files = [Configuration.mst_path(self.params, t.index) for t in tiles]
        correct._copy_mlooked(self.params)
        correct._create_ifg_dict(self.params)
        save_numpy_phase(self.ifg_paths, self.params)
        mst.mst_calc_wrapper(self.params)
        assert all(m.exists() for m in mst_files)
        return [os.stat(o).st_mtime for o in mst_files]
