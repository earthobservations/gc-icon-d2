import numpy as np
from multiprocessing import Pool
from functools import partial
from utils import *
import sys
from computations import compute_geopot_height

debug = False
if not debug:
    import matplotlib
    matplotlib.use('Agg')

import matplotlib.pyplot as plt

# The one employed for the figure name when exported 
variable_name = 't'
levels = (950, 850, 700, 500)

print_message('Starting script to plot '+variable_name)

# Get the projection as system argument from the call so that we can 
# span multiple instances of this script outside
if not sys.argv[1:]:
    print_message(
        'Projection not defined, falling back to default (de)')
    projection = 'de'
else:
    projection = sys.argv[1]


def main():
    """In the main function we basically read the files and prepare the variables to be plotted.
    This is not included in utils.py as it can change from case to case."""
    dset = read_dataset(variables=['t', 'fi'], level=[l * 100 for l in levels],
                        projection=projection)
    dset = compute_geopot_height(dset)
    cmap = get_colormap('temp')

    for level in levels:    
        dset_level = dset.sel(plev=level*100., method='nearest')
        dset_level.t.metpy.convert_units('degC')
        levels_gph = np.arange(np.nanmin(dset_level.geop).astype("int"),
                                np.nanmax(dset_level.geop).astype("int"), 25.)
        levels_temp = np.arange(np.nanmin(dset_level.t).astype("int"), 
                                np.nanmax(dset_level.t).astype("int"), 1.)

        _ = plt.figure(figsize=(figsize_x, figsize_y))

        ax = plt.gca()
        # Get coordinates from dataset
        m, x, y = get_projection(dset_level, projection, labels=True)
        dset_level = dset_level.drop(['lon', 'lat', 'z']).load()

        # All the arguments that need to be passed to the plotting function
        args=dict(x=x, y=y, ax=ax, cmap=cmap, level=level,
                  levels_temp=levels_temp, levels_gph=levels_gph,
                  time=dset_level.time, projection=projection)

        print_message('Pre-processing finished, launching plotting scripts')
        if debug:
            plot_files(dset_level.isel(time=slice(0, 2)), **args)
        else:
            # Parallelize the plotting by dividing into chunks and processes 
            dss = chunks_dataset(dset_level, chunks_size)
            plot_files_param = partial(plot_files, **args)
            p = Pool(processes)
            p.map(plot_files_param, dss)


def plot_files(dss, **args):
    # Using args we don't have to change the prototype function if we want to add other parameters!
    first = True
    for time_sel in dss.time:
        data = dss.sel(time=time_sel)
        time, run, cum_hour = get_time_run_cum(data)
        # Build the name of the output image
        filename = subfolder_images[projection] + '/' + variable_name + '_%s_%s.png' % (str(args['level']), cum_hour)

        cs = args['ax'].contourf(args['x'], args['y'], data['t'], extend='both', cmap=args['cmap'],
                                    levels=args['levels_temp'])

        c = args['ax'].contour(args['x'], args['y'], data['geop'], levels=args['levels_gph'],
                             colors='white', linewidths=1.)

        labels = args['ax'].clabel(c, c.levels, inline=True, fmt='%4.0f' , fontsize=6)

        maxlabels = plot_maxmin_points(args['ax'], args['x'], args['y'], data['geop'],
                                       'max', 100, symbol='H', color='royalblue', random=True)
        minlabels = plot_maxmin_points(args['ax'], args['x'], args['y'], data['geop'], 
                                       'min', 100, symbol='L', color='coral', random=True)

        an_fc = annotation_forecast(args['ax'], time)
        an_var = annotation(args['ax'], 'Temperature and Geopotential at '+str(args['level'])+' hPa' ,loc='lower left', fontsize=6)
        an_run = annotation_run(args['ax'], run)
        logo = add_logo_on_map(ax=args['ax'],
                                zoom=0.1, pos=(0.95, 0.08))

        if first:
            plt.colorbar(cs, orientation='horizontal', label='RH [%]', pad=0.03, fraction=0.04)

        if debug:
            plt.show(block=True)
        else:
            plt.savefig(filename, **options_savefig)        

        remove_collections([c, cs, labels, an_fc, an_var, an_run, maxlabels, minlabels, logo])

        first = False 


if __name__ == "__main__":
    import time
    start_time=time.time()
    main()
    elapsed_time=time.time()-start_time
    print_message("script took " + time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
