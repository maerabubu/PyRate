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
This Python module contains utilities to validate user input parameters
parsed in a PyRate configuration file.
"""
import re
from configparser import ConfigParser
from pathlib import Path, PurePath
from typing import Union

import pyrate.constants as C
from pyrate.constants import NO_OF_PARALLEL_PROCESSES, sixteen_digits_pattern, twelve_digits_pattern, ORB_ERROR_DIR, \
    DEM_ERROR_DIR, TEMP_MLOOKED_DIR
from pyrate.core import ifgconstants as ifg
from pyrate.default_parameters import PYRATE_DEFAULT_CONFIGURATION
from pyrate.core.algorithm import factorise_integer
from pyrate.core.shared import extract_epochs_from_filename, InputTypes, get_tiles


def set_parameter_value(data_type, input_value, default_value, required, input_name):
    if len(input_value) < 1:
        input_value = None
        if required:  # pragma: no cover
            raise ValueError("A required parameter is missing value in input configuration file: " + str(input_name))

    if input_value is not None:
        if str(data_type) in "path":
            return Path(input_value)
        return data_type(input_value)
    return default_value


def validate_parameter_value(input_name, input_value, min_value=None, max_value=None, possible_values=None):
    if isinstance(input_value, PurePath):
        if not Path.exists(input_value):  # pragma: no cover
            raise ValueError("Given path: " + str(input_value) + " does not exist.")
    if input_value is not None:
        if min_value is not None:
            if input_value < min_value:  # pragma: no cover
                raise ValueError(
                    "Invalid value for " + str(input_name) + " supplied: " + str(
                        input_value) + ". Provide a value greater than or equal to " + str(min_value) + ".")
    if input_value is not None:
        if max_value is not None:
            if input_value > max_value:  # pragma: no cover
                raise ValueError(
                    "Invalid value for " + str(input_name) + " supplied: " + str(
                        input_value) + ". Provide a value less than or equal to " + str(max_value) + ".")

    if possible_values is not None:
        if input_value not in possible_values:  # pragma: no cover
            raise ValueError(
                "Invalid value for " + str(input_name) + " supplied: " + str(
                    input_value) + ". Provide one of these values: " + str(possible_values) + ".")
    return True


def validate_file_list_values(file_list, no_of_epochs):
    if file_list is None:  # pragma: no cover
        raise ValueError("No value supplied for input file list: " + str(file_list))

    files = parse_namelist(file_list)

    for f in files:
        if not Path(f).exists():  # pragma: no cover
            raise ConfigException(f"{f} does not exist")
        else:
            matches = extract_epochs_from_filename(filename_with_epochs=f)
            if len(matches) < no_of_epochs:  # pragma: no cover
                raise ConfigException(f"the number of epochs in {f} names are less the required number: {no_of_epochs}")


class MultiplePaths:
    def __init__(self, file_name: str, params: dict, input_type: InputTypes = InputTypes.IFG):

        self.input_type = input_type
        out_dir = params[C.OUT_DIR]
        tempdir = params[C.TEMP_MLOOKED_DIR]
        if isinstance(tempdir, str):
            tempdir = Path(tempdir)
        b = Path(file_name)
        if input_type in [InputTypes.IFG, InputTypes.COH]:
            d = re.search(sixteen_digits_pattern, b.stem)
            if d is None:  # could be 6 digit epoch dates
                d = re.search(twelve_digits_pattern, b.stem)
            if d is None:
                raise ValueError(f"{input_type.value} filename does not contain two 8- or 6-digit date strings")
            filestr = d.group() + '_'
        else:
            filestr = ''

        dir_exists = input_type.value in InputTypes.dir_map.value.keys()
        anchoring_dir = Path(out_dir).joinpath(InputTypes.dir_map.value[input_type.value]) \
            if dir_exists else Path(out_dir)

        if b.suffix == ".tif":
            self.unwrapped_path = None
            converted_path = b  # original file
            self.sampled_path = anchoring_dir.joinpath(filestr + input_type.value + '.tif')
        else:
            self.unwrapped_path = b.as_posix()
            converted_path = anchoring_dir.joinpath(b.stem.split('.')[0] + '_' + b.suffix[1:]).with_suffix('.tif')
            self.sampled_path = converted_path.with_name(filestr + input_type.value + '.tif')

        # tmp_sampled_paths are used after prepifg, during correct steps
        self.tmp_sampled_path = tempdir.joinpath(self.sampled_path.name).as_posix()
        self.converted_path = converted_path.as_posix()
        self.sampled_path = self.sampled_path.as_posix()

    @staticmethod
    def orb_error_path(ifg_path: Union[str, Path], params) -> Path:
        if isinstance(ifg_path, str):
            ifg_path = Path(ifg_path)
        return Path(params[C.OUT_DIR], C.ORB_ERROR_DIR,
                    ifg_path.stem + '_' +
                    '_'.join([str(params[C.ORBITAL_FIT_METHOD]),
                              str(params[C.ORBITAL_FIT_DEGREE]),
                              str(params[C.ORBITAL_FIT_LOOKS_X]),
                              str(params[C.ORBITAL_FIT_LOOKS_Y])]) +
                    '_orbfit.npy')

    @staticmethod
    def dem_error_path(ifg_path: Union[str, Path], params) -> Path:
        if isinstance(ifg_path, str):
            ifg_path = Path(ifg_path)
        return Path(params[C.OUT_DIR], C.DEM_ERROR_DIR,
                    ifg_path.stem + '_' + str(params[C.DE_PTHR]) + '_dem_error.npy')

    @staticmethod
    def aps_error_path(ifg_path: Union[str, Path], params) -> Path:
        if isinstance(ifg_path, str):
            ifg_path = Path(ifg_path)
        return Path(params[C.OUT_DIR], C.APS_ERROR_DIR,
                    ifg_path.stem + '_' +
                    '_'.join([str(x) for x in [
                        params[C.SLPF_CUTOFF],
                        params[C.SLPF_NANFILL],
                        params[C.SLPF_NANFILL_METHOD],
                        params[C.TLPF_CUTOFF],
                        params[C.TLPF_PTHR]
                    ]
                              ]) + '_aps_error.npy')

    def __str__(self):  # pragma: no cover
        st = ""
        if self.unwrapped_path is not None:
            st += """\nunwrapped_path = """ + self.unwrapped_path
        else:
            st += """\nunwrapped_path = None"""
        st += """
            converted_path = """ + self.converted_path + """ 
            sampled_path = """ + self.sampled_path + """    
            tmp_sampled_path = """ + self.tmp_sampled_path + """
            """
        return st


class Configuration:

    def __init__(self, config_file_path):

        parser = ConfigParser()
        parser.optionxform = str
        # mimic header to fulfil the requirement for configparser
        with open(config_file_path) as stream:
            parser.read_string("[root]\n" + stream.read())

        for key, value in parser["root"].items():
            self.__dict__[key] = value

        # make output path, if not provided will error
        Path(self.outdir).mkdir(exist_ok=True, parents=True)

        # custom correct sequence if 'correct' section is provided in config
        if 'correct' in parser and 'steps' in parser['correct']:
            self.__dict__['correct'] = list(filter(None, parser['correct'].get('steps').splitlines()))
        else:
            self.__dict__['correct'] = [
                'orbfit',
                'refphase',
                'demerror',
                'phase_closure',
                'mst',
                'apscorrect',
                'maxvar',
            ]

        # Validate required parameters exist.

        required = {k for k, v in PYRATE_DEFAULT_CONFIGURATION.items() if v['Required']}

        if not required.issubset(self.__dict__):  # pragma: no cover
            raise ValueError("Required configuration parameters: " + str(
                required.difference(self.__dict__)) + " are missing from input config file.")

        # handle control parameters
        for parameter_name in PYRATE_DEFAULT_CONFIGURATION:
            param_value = self.__dict__[parameter_name] if parameter_name in required or \
                                                           parameter_name in self.__dict__ else ''

            self.__dict__[parameter_name] = set_parameter_value(
                PYRATE_DEFAULT_CONFIGURATION[parameter_name]["DataType"],
                param_value,
                PYRATE_DEFAULT_CONFIGURATION[parameter_name]["DefaultValue"],
                PYRATE_DEFAULT_CONFIGURATION[parameter_name]["Required"],
                parameter_name)
            validate_parameter_value(parameter_name, self.__dict__[parameter_name],
                                     PYRATE_DEFAULT_CONFIGURATION[parameter_name]["MinValue"],
                                     PYRATE_DEFAULT_CONFIGURATION[parameter_name]["MaxValue"],
                                     PYRATE_DEFAULT_CONFIGURATION[parameter_name]["PossibleValues"])

        # bespoke parameter validation
        if self.refchipsize % 2 != 1:  # pragma: no cover
            if self.refchipsize - 1 > 1:
                # Configuration parameters refchipsize must be odd
                # values too large (>101) will slow down the process without significant gains in results.
                self.refchipsize = self.refchipsize - 1

        # calculate rows and cols if not supplied
        if hasattr(self, 'rows') and hasattr(self, 'cols'):
            self.rows, self.cols = int(self.rows), int(self.cols)
        else:
            if NO_OF_PARALLEL_PROCESSES > 1:  # i.e. mpirun
                self.rows, self.cols = [int(num) for num in factorise_integer(NO_OF_PARALLEL_PROCESSES)]
            else:
                if self.parallel:  # i.e. joblib parallelism
                    self.rows, self.cols = [int(num) for num in factorise_integer(self.processes)]
                else:  # i.e. serial
                    self.rows, self.cols = 1, 1

        # create a temporary directory if not supplied
        if not hasattr(self, 'tmpdir'):
            self.tmpdir = Path(self.outdir).joinpath("tmpdir")
        else:
            self.tmpdir = Path(self.tmpdir)

        self.tmpdir.mkdir(parents=True, exist_ok=True)

        # create orbfit error dir
        self.orb_error_dir = Path(self.outdir).joinpath(ORB_ERROR_DIR)
        self.orb_error_dir.mkdir(parents=True, exist_ok=True)

        self.interferogram_dir = Path(self.outdir).joinpath(C.INTERFEROGRAM_DIR)
        self.interferogram_dir.mkdir(parents=True, exist_ok=True)

        # create DEM error dir
        self.dem_error_dir = Path(self.outdir).joinpath(DEM_ERROR_DIR)
        self.dem_error_dir.mkdir(parents=True, exist_ok=True)

        # create aps error dir
        self.aps_error_dir = Path(self.outdir).joinpath(C.APS_ERROR_DIR)
        self.aps_error_dir.mkdir(parents=True, exist_ok=True)

        # create mst dir
        self.mst_dir = Path(self.outdir).joinpath(C.MST_DIR)
        self.mst_dir.mkdir(parents=True, exist_ok=True)

        self.phase_closure_dir = Path(self.outdir).joinpath(C.PHASE_CLOSURE_DIR)
        self.phase_closure_dir.mkdir(parents=True, exist_ok=True)

        self.coherence_dir = Path(self.outdir).joinpath(C.COHERENCE_DIR)
        self.coherence_dir.mkdir(parents=True, exist_ok=True)

        self.geometry_dir = Path(self.outdir).joinpath(C.GEOMETRY_DIR)
        self.geometry_dir.mkdir(parents=True, exist_ok=True)

        self.timeseries_dir = Path(self.outdir).joinpath(C.TIMESERIES_DIR)
        self.timeseries_dir.mkdir(parents=True, exist_ok=True)

        self.velocity_dir = Path(self.outdir).joinpath(C.VELOCITY_DIR)
        self.velocity_dir.mkdir(parents=True, exist_ok=True)

        # create temp multilooked files dir
        self.temp_mlooked_dir = Path(self.outdir).joinpath(TEMP_MLOOKED_DIR)
        self.temp_mlooked_dir.mkdir(parents=True, exist_ok=True)

        self.ref_pixel_file = self.ref_pixel_path(self.__dict__)

        # var no longer used
        self.APS_ELEVATION_EXT = None
        self.APS_INCIDENCE_EXT = None
        self.apscorrect = 0
        self.apsmethod = 0
        self.elevationmap = None
        self.incidencemap = None

        # define parallel processes that will run
        self.NUMEXPR_MAX_THREADS = str(NO_OF_PARALLEL_PROCESSES)

        # Validate file names supplied in list exist and contain correct epochs in file names
        if self.cohfilelist is not None:
            # if self.processor != 0:  # not roipac
            validate_file_list_values(self.cohfilelist, 1)
            self.coherence_file_paths = self.__get_files_from_attr('cohfilelist', input_type=InputTypes.COH)

        if self.basefilelist is not None:
            # if self.processor != 0:  # not roipac
            validate_file_list_values(self.basefilelist, 1)
            self.baseline_file_paths = self.__get_files_from_attr('basefilelist', input_type=InputTypes.BASE)

        self.header_file_paths = self.__get_files_from_attr('hdrfilelist', input_type=InputTypes.HEADER)

        self.interferogram_files = self.__get_files_from_attr('ifgfilelist')

        self.dem_file = MultiplePaths(self.demfile, self.__dict__, input_type=InputTypes.DEM)

        # backward compatibility for string paths
        for key in self.__dict__:
            if isinstance(self.__dict__[key], PurePath):
                self.__dict__[key] = str(self.__dict__[key])

    @staticmethod
    def ref_pixel_path(params):
        return Path(params[C.OUT_DIR]).joinpath(
            '_'.join(
                [str(x) for x in [
                    'ref_pixel', params[C.REFX], params[C.REFY], params[
                        C.REFNX], params[C.REFNY],
                    params[C.REF_CHIP_SIZE], params[C.REF_MIN_FRAC], '.npy'
                ]
                 ]
            )
        )

    @staticmethod
    def mst_path(params, index) -> Path:
        return Path(params[C.OUT_DIR], C.MST_DIR).joinpath(f'mst_mat_{index}.npy')

    @staticmethod
    def preread_ifgs(params: dict) -> Path:
        return Path(params[C.TMPDIR], 'preread_ifgs.pk')

    @staticmethod
    def vcmt_path(params):
        return Path(params[C.OUT_DIR], C.VCMT).with_suffix('.npy')

    @staticmethod
    def phase_closure_filtered_ifgs_list(params):
        return Path(params[C.TEMP_MLOOKED_DIR]).joinpath('phase_closure_filtered_ifgs_list')

    def refresh_ifg_list(self, params):  # update params dict
        filtered_ifgs_list = self.phase_closure_filtered_ifgs_list(params)
        files = parse_namelist(filtered_ifgs_list.as_posix())
        params[C.INTERFEROGRAM_FILES] = [MultiplePaths(p, self.__dict__, input_type=InputTypes.IFG) for p in files]
        return params

    @staticmethod
    def ref_phs_file(params):
        ref_pixel_path = Configuration.ref_pixel_path(params)
        # add ref pixel path as when ref pixel changes - ref phs path should also change
        return Path(params[C.OUT_DIR]).joinpath(
            ref_pixel_path.stem + '_' +
            '_'.join(['ref_phs', str(params[C.REF_EST_METHOD]), '.npy'])
        )

    @staticmethod
    def get_tiles(params):
        ifg_path = params[C.INTERFEROGRAM_FILES][0].sampled_path
        rows, cols = params['rows'], params['cols']
        return get_tiles(ifg_path, rows, cols)

    def __get_files_from_attr(self, attr, input_type=InputTypes.IFG):
        val = self.__getattribute__(attr)
        files = parse_namelist(val)
        return [MultiplePaths(p, self.__dict__, input_type=input_type) for p in files]

    def closure(self):
        closure_d = Path(self.phase_closure_dir)

        class Closure:
            def __init__(self):
                self.closure = closure_d.joinpath('closure.npy')
                self.ifgs_breach_count = closure_d.joinpath('ifgs_breach_count.npy')
                self.num_occurences_each_ifg = closure_d.joinpath('num_occurrences_each_ifg.npy')
                self.loops = closure_d.joinpath('loops.npy')

        return Closure()

    @staticmethod
    def coherence_stats(params):
        coh_d = Path(params[C.COHERENCE_DIR])
        return {k: coh_d.joinpath(k.lower() + '.tif').as_posix() for k in [ifg.COH_MEDIAN, ifg.COH_MEAN, ifg.COH_STD]}

    @staticmethod
    def geometry_files(params):
        geom_dir = Path(params[C.GEOMETRY_DIR])
        return {k: geom_dir.joinpath(k.lower() + '.tif').as_posix() for k in C.GEOMETRY_OUTPUT_TYPES}


def write_config_parser_file(conf: ConfigParser, output_conf_file: Union[str, Path]):
    """replacement function for write_config_file which uses dict instead of a ConfigParser instance"""
    with open(output_conf_file, 'w') as configfile:
        conf.write(configfile)


def write_config_file(params, output_conf_file):
    """
    Takes a param object and writes the config file. Reverse of get_conf_params.

    :param dict params: parameter dictionary
    :param str output_conf_file: output file name

    :return: config file
    :rtype: list
    """
    with open(output_conf_file, 'w') as f:
        for k, v in params.items():
            if v is not None:
                if k == 'correct':
                    f.write(''.join(['[', k, ']' ':\t', '', '\n']))
                    f.write(''.join(['steps = ', '\n']))
                    for vv in v:
                        f.write(''.join(['\t' + str(vv), '\n']))
                elif isinstance(v, list):
                    continue
                else:
                    if isinstance(v, MultiplePaths):
                        if v.unwrapped_path is None:
                            vv = v.converted_path
                        else:
                            vv = v.unwrapped_path
                    else:
                        vv = v
                    f.write(''.join([k, ':\t', str(vv), '\n']))
            else:
                f.write(''.join([k, ':\t', '', '\n']))


def parse_namelist(nml):
    """
    Parses name list file into array of paths

    :param str nml: interferogram file list

    :return: list of interferogram file names
    :rtype: list
    """
    with open(nml) as f_in:
        lines = [line.rstrip() for line in f_in]
    return filter(None, lines)


class ConfigException(Exception):
    """
    Default exception class for configuration errors.
    """

