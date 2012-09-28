import matplotlib.pyplot as plt

import iris
import iris.quickplot as qplt
import iris.plot as iplt

fname = iris.sample_data_path('air_temp.pp')
temperature_cube = iris.load_strict(fname)

# Draw the contour with 25 levels
qplt.contourf(temperature_cube, 25)

# Add coastlines to the map created by contourf
plt.gca().coastlines()

plt.show()
