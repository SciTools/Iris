# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Common code for benchmarks."""
import resource

from .generate_data import BENCHMARK_DATA, run_function_elsewhere

ARTIFICIAL_DIM_SIZE = int(10e3)  # For all artificial cubes, coords etc.


def disable_repeat_between_setup(benchmark_object):
    """
    Decorator for benchmarks where object persistence would be inappropriate.

    E.g:
        * Benchmarking data realisation
        * Benchmarking Cube coord addition

    Can be applied to benchmark classes/methods/functions.

    https://asv.readthedocs.io/en/stable/benchmarks.html#timing-benchmarks

    """
    # Prevent repeat runs between setup() runs - object(s) will persist after 1st.
    benchmark_object.number = 1
    # Compensate for reduced certainty by increasing number of repeats.
    #  (setup() is run between each repeat).
    #  Minimum 5 repeats, run up to 30 repeats / 20 secs whichever comes first.
    benchmark_object.repeat = (5, 30, 20.0)
    # ASV uses warmup to estimate benchmark time before planning the real run.
    #  Prevent this, since object(s) will persist after first warmup run,
    #  which would give ASV misleading info (warmups ignore ``number``).
    benchmark_object.warmup_time = 0.0

    return benchmark_object


class TrackAddedMemoryAllocation:
    """
    Context manager which measures by how much process resident memory grew,
    during execution of its enclosed code block.

    Obviously limited as to what it actually measures : Relies on the current
    process not having significant unused (de-allocated) memory when the
    tested codeblock runs, and only reliable when the code allocates a
    significant amount of new memory.

    Example:
        with TrackAddedMemoryAllocation() as mb:
            initial_call()
            other_call()
        result = mb.addedmem_mb()

    """

    @staticmethod
    def process_resident_memory_mb():
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

    def __enter__(self):
        self.mb_before = self.process_resident_memory_mb()
        return self

    def __exit__(self, *_):
        self.mb_after = self.process_resident_memory_mb()

    def addedmem_mb(self):
        """Return measured memory growth, in Mb."""
        return self.mb_after - self.mb_before
