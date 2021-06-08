# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Unit tests for the engine.activate() call within the
`iris.fileformats.netcdf._load_cube` function.

Tests for rules activation relating to 'time' and 'time_period' coords.

"""
import iris.tests as tests

from iris.coords import AuxCoord, DimCoord


from iris.tests.unit.fileformats.netcdf.load_cube.load_cube__activate import (
    Mixin__nc_load_actions,
)


class Opts(dict):
    # A dict-like thing which provides '.' access in place of indexing.
    def __init__(self, **kwargs):
        # Init like a dict
        super().__init__(**kwargs)
        # Alias contents "self['key']",  as properties "self.key"
        # See: https://stackoverflow.com/a/14620633/2615050
        self.__dict__ = self


# Per-coord options settings for testcase definitions.
_COORD_OPTIONS_TEMPLATE = {
    "which": "",  # set to "something"
    "stdname": "_auto_which",  # default = time / time_period
    "varname": "_as_which",  # default = time / period
    "dimname": "_as_which",
    "in_phenomvar_dims": True,
    "in_phenomvar_coords": False,  # set for an aux-coord
    "values_all_zero": False,  # set to block CFDimensionVariable identity
    "units": "_auto_which",  # specific to time/period
}


class Mixin__timecoords__common(Mixin__nc_load_actions):
    def _make_testcase_cdl(
        self,
        phenom_dims="_auto",  # =get from time+period opts
        phenom_coords="_auto",  # =get from time+period opts
        time_opts=None,
        period_opts=None,
        timedim_name="time",
        perioddim_name="period",
    ):
        opt_t = None
        opt_p = None
        if time_opts is not None:
            # Replace 'True' with an options dict for 'time' options
            opt_t = Opts(**_COORD_OPTIONS_TEMPLATE)
            opt_t.update(which="time", **time_opts)
        if period_opts is not None:
            # Replace 'True' with an options dict for 'period' options
            opt_p = Opts(**_COORD_OPTIONS_TEMPLATE)
            opt_p.update(which="period", **period_opts)

        # Define the 'standard' dimensions which we will create
        # NB we don't necessarily *use* either of these
        dims_and_lens = {timedim_name: 2, perioddim_name: 3}
        dims_string = "\n".join(
            [
                f"        {name} = {length} ;"
                for name, length in dims_and_lens.items()
            ]
        )

        phenom_auto_dims = []
        phenom_auto_coords = []
        coord_variables_string = ""
        data_string = ""
        for opt in (opt_t, opt_p):
            # Handle computed defaults and common info for both coord options.
            if opt:
                if opt.which not in ("time", "period"):
                    raise ValueError(f"unrecognised opt.which={opt.which}")

                # Do computed defaults.
                if opt.stdname == "_auto_which":
                    if opt.which == "time":
                        opt.stdname = "time"
                    else:
                        assert opt.which == "period"
                        opt.stdname = "forecast_period"
                if opt.varname == "_as_which":
                    opt.varname = opt.which
                if opt.dimname == "_as_which":
                    opt.dimname = opt.which
                if opt.units == "_auto_which":
                    if opt.which == "time":
                        opt.units = "hours since 2000-01-01"
                    else:
                        assert opt.which == "period"
                        opt.units = "hours"

                # Build 'auto' lists of phenom dims and (aux) coordinates.
                if opt.in_phenomvar_dims:
                    phenom_auto_dims.append(opt.dimname)
                if opt.in_phenomvar_coords:
                    phenom_auto_coords.append(opt.varname)

                # Add a definition of the coord variable.
                coord_variables_string += f"""
        double {opt.varname}({opt.dimname}) ;
            {opt.varname}:standard_name = "{opt.stdname}" ;
            {opt.varname}:units = "{opt.units}" ;
"""
                # NOTE: we don't bother with an 'axis' property.
                # We can probe the behaviour we need without that, because we
                # are *not* testing the cf.py categorisation code, or the
                # helper "build_xxx" routines.

                # Define coord-var data values (so it can be a dimension).
                varname = opt.varname
                if opt.values_all_zero:
                    # Use 'values_all_zero' to prevent a dim-var from
                    # identifying as a CFDimensionCoordinate (as it is
                    # non-monotonic).
                    dim_vals = [0.0] * dims_and_lens[opt.dimname]
                else:
                    # "otherwise", assign an ascending sequence.
                    dim_vals = range(dims_and_lens[opt.dimname])
                dimvals_string = ", ".join(f"{val:0.1f}" for val in dim_vals)
                data_string += f"\n        {varname} = {dimvals_string} ;"

        if phenom_dims == "_auto":
            phenom_dims = phenom_auto_dims
        if not phenom_dims:
            phenom_dims_string = ""
        else:
            phenom_dims_string = ", ".join(phenom_dims)

        if phenom_coords == "_auto":
            phenom_coords = phenom_auto_coords
        if not phenom_coords:
            phenom_coords_string = ""
        else:
            phenom_coords_string = " ".join(phenom_coords)
            phenom_coords_string = (
                "            "
                f'phenom:coordinates = "{phenom_coords_string}" ; '
            )

        # Create a testcase with time dims + coords.
        cdl_string = f"""
netcdf test {{
    dimensions:
{dims_string}
    variables:
        double phenom({phenom_dims_string}) ;
            phenom:standard_name = "air_temperature" ;
            phenom:units = "K" ;
{phenom_coords_string}

{coord_variables_string}
    data:
{data_string}
}}
"""
        return cdl_string

    def check_result(self, cube, time_is="dim", period_is="missing"):
        """
        Check presence of expected dim/aux-coords in the result cube.

        Both of 'time_is' and 'period_is' can take values 'dim', 'aux' or
        'missing'.

        """
        options = ("dim", "aux", "missing")
        msg = f'Invalid "{{name}}" = {{opt}} : Not one of {options!r}.'
        if time_is not in options:
            raise ValueError(msg.format(name="time_is", opt=time_is))
        if period_is not in options:
            raise ValueError(msg.format(name="period_is", opt=period_is))

        # Get the facts we want to check
        time_name = "time"
        period_name = "forecast_period"
        time_dimcos = cube.coords(time_name, dim_coords=True)
        time_auxcos = cube.coords(time_name, dim_coords=False)
        period_dimcos = cube.coords(period_name, dim_coords=True)
        period_auxcos = cube.coords(period_name, dim_coords=False)

        if time_is == "dim":
            self.assertEqual(len(time_dimcos), 1)
            self.assertEqual(len(time_auxcos), 0)
        elif time_is == "aux":
            self.assertEqual(len(time_dimcos), 0)
            self.assertEqual(len(time_auxcos), 1)
        else:
            self.assertEqual(len(time_dimcos), 0)
            self.assertEqual(len(time_auxcos), 0)

        if period_is == "dim":
            self.assertEqual(len(period_dimcos), 1)
            self.assertEqual(len(period_auxcos), 0)
        elif period_is == "aux":
            self.assertEqual(len(period_dimcos), 0)
            self.assertEqual(len(period_auxcos), 1)
        else:
            self.assertEqual(len(period_dimcos), 0)
            self.assertEqual(len(period_auxcos), 0)

        # Also check expected built Coord types.
        if time_is == "dim":
            self.assertIsInstance(time_dimcos[0], DimCoord)
        elif time_is == "aux":
            self.assertIsInstance(time_auxcos[0], AuxCoord)

        if period_is == "dim":
            self.assertIsInstance(period_dimcos[0], DimCoord)
        elif period_is == "aux":
            self.assertIsInstance(period_auxcos[0], AuxCoord)


class Mixin__singlecoord__tests(Mixin__timecoords__common):
    # Coordinate tests to be run for both 'time' and 'period' coordinate vars.
    # Set (in inheritors) to select time/period testing.
    which = None

    def run_testcase(self, coord_dim_name=None, **opts):
        """
        Specialise 'run_testcase' for single-coord 'time' or 'period' testing.
        """
        which = self.which
        assert which in ("time", "period")

        # Separate the 'Opt' keywords from "others" : others are passed
        # directly to the parent routine, whereas 'Opt' ones are passed to
        # 'time_opts' / 'period_opts' keys accordingly.
        general_opts = {}
        for key, value in list(opts.items()):
            if key not in _COORD_OPTIONS_TEMPLATE.keys():
                del opts[key]
                general_opts[key] = value

        if coord_dim_name is not None:
            # Translate this into one of timedim_name/perioddim_name
            general_opts[f"{which}dim_name"] = coord_dim_name

        period_opts = None
        time_opts = None
        if which == "time":
            time_opts = opts
        else:
            period_opts = opts

        result = super().run_testcase(
            time_opts=time_opts, period_opts=period_opts, **general_opts
        )

        return result

    def check_result(self, cube, coord_is="dim"):
        """
        Specialise 'check_result' for single-coord 'time' or 'period' testing.
        """
        # Pass generic 'coord_is' option to parent as time/period options.
        which = self.which
        assert which in ("time", "period")

        if which == "time":
            time_is = coord_is
            period_is = "missing"
        else:
            period_is = coord_is
            time_is = "missing"

        super().check_result(cube, time_is=time_is, period_is=period_is)

    #
    # Generic single-coordinate testcases.
    # ( these are repeated for both 'time' and 'time_period' )
    #

    def test_dimension(self):
        # Coord is a normal dimension --> dimcoord
        #
        # Rules Triggered:
        #     001 : fc_default
        #     002 : fc_provides_coordinate_time
        #     003 : fc_build_coordinate_time
        result = self.run_testcase()
        self.check_result(result, "dim")

    def test_dimension_in_phenom_coords(self):
        # Dimension coord also present in phenom:coords.
        # Strictly wrong but a common error in datafiles : must tolerate.
        # Rules Triggered:
        #     001 : fc_default
        #     002 : fc_provides_coordinate_time
        #     003 : fc_build_coordinate_time
        result = self.run_testcase(in_phenomvar_coords=True)
        self.check_result(result, "dim")

    def test_dim_nonmonotonic(self):
        # Coord has all-zero values, which prevents it being a dimcoord.
        # The rule has a special way of treating it as an aux coord
        # -- even though it doesn't appear in the phenom coords.
        # ( Done by  the build_coord routine, so not really a rules issue).
        # Rules Triggered:
        #     001 : fc_default
        #     002 : fc_provides_coordinate_time
        #     003 : fc_build_coordinate_time
        msg = "Failed to create.* dimension coordinate"
        result = self.run_testcase(values_all_zero=True, warning=msg)
        self.check_result(result, "aux")

    def test_dim_fails_typeident(self):
        # The coord variable is identified as a CFDimensionCoordinate by cf.py,
        # but having the wrong units causes it to fail the 'is_time' or
        # 'is_period' test, so the 'provides_coord' rule fails to trigger.
        # So it is built as a 'miscellaneous' dim-coord.
        # N.B. this makes *no* practical difference, because a 'misc' dim
        # coord is still a dim coord (albeit with bad units).
        # ( N.B.#2 Not quite the same for lat/lon coords, where coord-specific
        #   'build' rules always use a fixed standard-name ).
        # Rules Triggered:
        # 	#001 : fc_default
        # 	#002 : fc_default_coordinate
        result = self.run_testcase(units="1")
        self.check_result(result, "dim")

    def test_aux(self):
        # time/period is installed as an auxiliary coord.
        # For this, rename both DIMENSIONS, so that the generated coords are
        # not actually CF coordinates.
        # For a valid case, we must *also* have a ref in phenom:coordinates
        # Rules Triggered:
        #     001 : fc_default
        #     002 : fc_build_auxiliary_coordinate_time
        result = self.run_testcase(
            coord_dim_name="dim_renamed",
            dimname="dim_renamed",
            in_phenomvar_coords=True,
        )
        self.check_result(result, "aux")

    def test_aux_not_in_phenom_coords(self):
        # time/period is installed as an auxiliary coord,
        # but we DIDN'T list it in phenom:coords  -- otherwise as previous.
        # Should have no result at all.
        # Rules Triggered:
        #     001 : fc_default
        result = self.run_testcase(
            coord_dim_name="dim_renamed",
            dimname="dim_renamed",
            in_phenomvar_coords=False,
        )  # "should" be True for an aux-coord
        self.check_result(result, "missing")

    def test_aux_fails_typeident(self):
        # The coord variable is identified as a CFAuxiliaryCoordinate by cf.py,
        # but having the wrong units causes it to fail the 'is_time' or
        # 'is_period' test, so the 'provides_coord' rule fails to trigger.
        # Rules Triggered:
        #     001 : fc_default
        #     002 : fc_build_auxiliary_coordinate
        # Again, though it builds as a 'miscellaneous' rather than a recognised
        # specific coord type, it makes no practical difference.
        result = self.run_testcase(
            coord_dim_name="dim_renamed",
            dimname="dim_renamed",
            in_phenomvar_coords=True,
            units="1",
        )
        self.check_result(result, "aux")

    def test_aux_no_coordsref(self):
        # The coord variable is identified as a CFAuxiliaryCoordinate by cf.py,
        # but having the wrong units causes it to fail the 'is_time' or
        # 'is_period' test.
        # Rules Triggered:
        #     001 : fc_default
        #     002 : fc_build_auxiliary_coordinate
        # Again, though it builds as a 'miscellaneous' rather than a reocgnised
        # specific coord type, it makes no practical difference.
        result = self.run_testcase(
            coord_dim_name="dim_renamed",
            dimname="dim_renamed",
            in_phenomvar_coords=True,
            units="1",
        )
        self.check_result(result, "aux")


class Test__time__withpyke(Mixin__singlecoord__tests, tests.IrisTest):
    # Run 'time' coord tests
    which = "time"
    use_pyke = True
    debug = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()


class Test__period__withpyke(Mixin__singlecoord__tests, tests.IrisTest):
    # Run 'time_period' coord tests
    which = "period"
    use_pyke = True
    debug = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()


class Mixin__dualcoord__tests(Mixin__timecoords__common):
    # Coordinate tests for a combination of 'time' and 'time_period'.
    # Not strictly necessary, as handling is independent, but a handy check
    # on typical usage.
    def test_time_and_period(self):
        # Test case with both 'time' and 'period', with separate dims.
        # Rules Triggered:
        #     001 : fc_default
        #     002 : fc_provides_coordinate_time
        #     003 : fc_provides_coordinate_time_period
        #     004 : fc_build_coordinate_time
        #     005 : fc_build_coordinate_time_period
        result = self.run_testcase(time_opts={}, period_opts={})
        self.check_result(result, time_is="dim", period_is="dim")

    def test_time_dim_period_aux(self):
        # Test case with both 'time' and 'period' sharing a dim.
        # Rules Triggered:
        #     001 : fc_default
        # Rules Triggered:
        #     001 : fc_default
        #     002 : fc_provides_coordinate_time
        #     003 : fc_build_auxiliary_coordinate_time_period
        #     004 : fc_build_coordinate_time
        result = self.run_testcase(
            time_opts={},
            period_opts=dict(
                dimname="time",
                in_phenomvar_dims=False,
                in_phenomvar_coords=True,
            ),
        )
        self.check_result(result, time_is="dim", period_is="aux")


class Test__dualcoord_tests__withpyke(Mixin__dualcoord__tests, tests.IrisTest):
    use_pyke = True
    debug = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()


if __name__ == "__main__":
    tests.main()
