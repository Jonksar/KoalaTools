import numpy as np
from random import choice
from string import lowercase, digits

class WindowStatistics(object):
    # A class to store data about ContinuousData
    def __init__(self, parent):
        self.parent = parent
        self.calibrate(data=parent.data)

    def calibrate(self, data):
        self.mean = np.mean(data, axis=1)
        self.std = np.std(data, axis=1)
        self.std_sqrd = self.std ** 2

    def __str__(self):
        return "Instance of WindowStatistics; \nmean: " + str(self.mean) + "\nstd: " + str(self.std)


class SubWindowStatistics(WindowStatistics):
    def __init__(self, parent, start, end):
        super(SubWindowStatistics, self).__init__(parent=parent)
        self.start = start
        self.end = end

    def sub_calibrate(self, data):
        self.mean = np.mean(data[:, self.start: self.end], axis=1)
        self.std = np.std(data[:, self.start: self.end], axis=1)
        self.std_sqrd = self.std ** 2

    def __str__(self):
        return "Instance of SubWindowStatistics; start: " + str(self.start) + " end: " + str(self.end) + "\nmean: " + str(self.mean) + "\nstd: " + str(self.std)

class ContinuousData:
    def __init__(self, init_data=None, track_metadata=True, verbose=False):
        # Main components
        self.data = init_data if len(init_data.shape) != 1 else init_data.reshape((-1, 1))
        self.track_metadata = track_metadata

        # Convenience
        self.n_dim = self.data.shape[0]
        self.verbose=verbose

        # Limits the amount of data we can have
        self.max_data = init_data.shape[1]

        if track_metadata:
            self._mwindow = WindowStatistics(parent=self)  # main data window

            # Recalibrate std and such every self.calibration_iter
            self.calibration_iter = 3 * self.max_data
            self.iter = 0

        self.attention_windows = {}

    def add_data(self, data):
        self.iter += 1
        assert np.size(data) == self.n_dim, "you can only add data of shape n_dim"
        # Make sure data is of right shape
        if len(data.shape) == 1:
            data = data.reshape((-1, 1))

        # Add data
        self.data = np.hstack((self.data, data))

        if self.track_metadata:
            # Keep track of data statistics
            if self.iter % self.calibration_iter == 0:

                if self.verbose: print "\n ##### RECALIBRATING CONTINUOUS DATA ##### \n"
                self._calc_metadata()

                # Initialize the windows again (shortcut for updating the mean, std etc)
                if len(self.attention_windows) != 0:
                    for window in self.attention_windows.values():
                        window.sub_calibrate(self.data)
            else:
                self._calc_mean()
                self._calc_std()

                if len(self.attention_windows) != 0:
                    for window in self.attention_windows.values():
                        self._calc_mean_attention_window(window, start=window.start, end=window.end)
                        self._calc_std_attention_window(window, start=window.start, end=window.end)

        # Make sure we don't have too much data
        self._trim_data()

    def add_attention_window(self, start=0, end=None, length=None):
        assert end is not None or length is not None, "Please specify ending index or length of attention window"

        if length is not None:
            end = start + length

        name = self._unique_window_name()
        self.attention_windows[name] = SubWindowStatistics(parent=self, start=start, end=end)

        return name

    def _trim_data(self):
        self.data = self.data[:self.n_dim, -self.max_data:]

    def _calc_mean(self):
        self._mwindow.mean = self._mwindow.mean - self.data[:, 0] / self.data.shape[1] + self.data[:, -1] / self.data.shape[1]

    def _calc_std(self):
        self._mwindow.std_sqrd = self._mwindow.std_sqrd\
                        - (self.data[:, 0] - self._mwindow.mean)**2 / self.data.shape[1]\
                        + (self.data[:, -1] - self._mwindow.mean)**2 / self.data.shape[1]

        self._mwindow.std_sqrd = np.maximum(self._mwindow.std_sqrd, 0)
        self._mwindow.std = np.sqrt(self._mwindow.std_sqrd)

    def _calc_metadata(self):
        self._mwindow.mean = np.mean(self.data, axis=1)
        self._mwindow.std = np.std(self.data, axis=1)
        self._mwindow.std_sqrd = self._mwindow.std**2


    def _calc_mean_attention_window(self, window, start, end):
        len_data = end - start
        window.mean = window.mean - self.data[:, start] / len_data + self.data[:, end] / len_data


    def _calc_std_attention_window(self, window, start, end):
        data_len = end - start
        window.std_sqrd = window.std_sqrd \
                        - (self.data[:, start] - window.mean) ** 2 / data_len \
                        + (self.data[:, end] - window.mean) ** 2 / data_len

        window.std_sqrd = np.maximum(window.std_sqrd, 0)
        window.std = np.sqrt(window.std_sqrd)

    def _unique_window_name(self, n=10):
        res = ''.join([choice(lowercase + digits) for _ in range(n)])
        while res in self.attention_windows.keys():
            res = ''.join([choice(lowercase + digits) for _ in range(n)])

        return res
