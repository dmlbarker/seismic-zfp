from collections.abc import Mapping
import numpy as np
from .read import SgzReader


class SubvolumeAccessor(SgzReader):

    def __init__(self, file):
        super(SubvolumeAccessor, self).__init__(file)

        self.zslices_int = self.zslices.astype('intc')

        self.axes_message = "Inline {}:{}:{}, Crossline {}:{}:{}, Samples {}:{}:{}".format(
                self.ilines[0], self.ilines[-1] + self.ilines[1] - self.ilines[0], self.ilines[1] - self.ilines[0],
                self.xlines[0], self.xlines[-1] + self.xlines[1] - self.xlines[0], self.xlines[1] - self.xlines[0],
                self.zslices_int[0], self.zslices_int[-1] + self.zslices_int[1] - self.zslices_int[0], self.zslices_int[1] - self.zslices_int[0])

    def __getitem__(self, subscripts):
        il, xl, z = subscripts

        self._check_subscripts(il, self.ilines, "Inline")
        self._check_subscripts(xl, self.xlines, "Crossline")
        self._check_subscripts(z,  self.zslices_int, "Samples")

        il_start, il_step, il_stop = self._get_index_subscripts(il, self.ilines)
        xl_start, xl_step, xl_stop = self._get_index_subscripts(xl, self.xlines)
        z_start, z_step, z_stop = self._get_index_subscripts(z, self.zslices_int)

        # N.B. While this implementation will work with steps larger than 1, it has to read and decompress
        # everything in between. Of course there's no way to avoid that for steps <=4 but memory usage could
        # be reduced with a better implementation
        return self.read_subvolume(il_start, il_stop, xl_start, xl_stop, z_start, z_stop)[::il_step, ::xl_step, ::z_step]

    def _get_index_subscripts(self, coord_subscript, coords):
        start = 0 if coord_subscript.start is None else np.where(coords == coord_subscript.start)[0][0]
        stop = len(coords) if (coord_subscript.stop is None) or (coord_subscript.stop == coords[-1] + coords[1] - coords[0]) else np.where(coords == coord_subscript.stop)[0][0]
        step = 1 if coord_subscript.step is None else coord_subscript.step // (coords[1] - coords[0])
        return start, step, stop

    def _check_subscripts(self, subscript, coords, coord_name):
        if subscript.start is not None and not coords[0] <= subscript.start < coords[-1] + coords[1] - coords[0]:
            raise IndexError("{} start {} out of range. Axes are {}".format(coord_name, subscript.start, self.axes_message))
        if subscript.stop is not None and not coords[0] < subscript.stop <= coords[-1] + coords[1] - coords[0]:
            raise IndexError("{} stop {} out of range. Axes are {}".format(coord_name, subscript.stop, self.axes_message))
        if subscript.step is not None and not subscript.step % (coords[1] - coords[0]) == 0:
            raise IndexError("{} step {} invalid. Axes are {}".format(coord_name, subscript.step, self.axes_message))


class Accessor(SgzReader):

    def __init__(self, file):
        super(Accessor, self).__init__()

    def __iter__(self):
        return iter(self[:])

    def __len__(self):
        return self.len_object

    def __getitem__(self, subscript):
        if isinstance(subscript, slice):
            # Acquiris Quodcumquae Rapis
            start, stop, step = subscript.indices(len(self))
            return [self.values_function(index) for index in range(start, stop, step)]
        else:
            return self.values_function(subscript)

    def __contains__(self, key):
        return key in self.keys_object

    def __hash__(self):
        return hash(self.filename)

    def keys(self):
        return self.keys_object

    def values(self):
        return self[:]

    def items(self):
        return zip(self.keys(), self[:])


class InlineAccessor(Accessor, Mapping):
    def __init__(self, file):
        super(Accessor, self).__init__(file)
        self.len_object = self.n_ilines
        self.keys_object = self.ilines
        self.values_function = self.read_inline_number


class CrosslineAccessor(Accessor, Mapping):
    def __init__(self, file):
        super(Accessor, self).__init__(file)
        self.len_object = self.n_xlines
        self.keys_object = self.xlines
        self.values_function = self.read_crossline_number


class ZsliceAccessor(Accessor, Mapping):
    def __init__(self, file):
        super(Accessor, self).__init__(file)
        self.len_object = self.n_samples
        self.keys_object = self.zslices
        self.values_function = self.read_zslice


class HeaderAccessor(Accessor, Mapping):
    def __init__(self, file):
        super(Accessor, self).__init__(file)
        self.len_object = self.tracecount
        self.keys_object = list(range(self.tracecount))
        self.values_function = self.gen_trace_header


class TraceAccessor(Accessor, Mapping):
    def __init__(self, file):
        super(Accessor, self).__init__(file)
        self.len_object = self.tracecount
        self.keys_object = list(range(self.tracecount))
        self.values_function = self.get_trace
