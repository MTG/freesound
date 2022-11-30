from __future__ import print_function

import gaia2
import pylab as pl

OUT_FOLDER = 'out_plots' # Must be created
GAIA_INDEX_FILE = 'fs_index.db' # File with gaia index
BINS = 100 # Bins per histogram plot


def plot_histogram(pool, label,  x_label_ticks = False):
    fig = pl.figure()
    ax = fig.add_subplot(111)

    if not x_label_ticks:
        range_min = min(pool) #percentile(pool, 10)
        range_max = max(pool) #percentile(pool, 90)
    else:
        range_min = min(pool)
        range_max = max(pool) + 1

    n_bins = BINS
    if x_label_ticks:
        n_bins = len(x_label_ticks)
    n, bins, patches = ax.hist(pool, bins=n_bins, range=(float(range_min), float(range_max)), log=False, histtype='stepfilled')
    pl.title('Distribution: %s' % label)
    if not x_label_ticks:
        ax.ticklabel_format(axis='x', style='sci', scilimits=(-3,3))
    else:
        pl.xticks(range(0, len(x_label_ticks)),['           %s'%tick for tick in x_label_ticks])
    ax.ticklabel_format(axis='y', style='sci', scilimits=(-2,2))
    ax.set_xlabel('Value')
    ax.set_ylabel('Frequency of occurrence')
    ax.grid(True)
    pl.savefig('%s/%s.png' % (OUT_FOLDER, label[1:]))
    pl.close()

ds = gaia2.DataSet()
dataset_path = GAIA_INDEX_FILE
ds.load(dataset_path)
transformation_history = ds.history().toPython()
normalization_coeffs = None
for i in range(0,len(transformation_history)):
    if transformation_history[-(i+1)]['Analyzer name'] == 'normalize':
        normalization_coeffs = transformation_history[-(i+1)]['Applier parameters']['coeffs']
print([x for x in normalization_coeffs.keys() if (".tonal" in x and "chords" in x)])
descriptor_names = ds.layout().descriptorNames()
point_names = ds.pointNames()
example_point = ds.point(point_names[0])
reject_stats = ['dmean', 'dmean2', 'dvar', 'dvar2', 'max',  'min', 'var']


for descriptor_name in descriptor_names:
    region = ds.layout().descriptorLocation(descriptor_name)
    if region.lengthType() == gaia2.VariableLength or descriptor_name.split('.')[-1] in reject_stats:
	continue

    try:
        example_value = example_point.value(descriptor_name)
    except:
        try:
            example_value = example_point.label(descriptor_name)
        except:
            print("ERROR: %s could not be processed" % descriptor_name)
            continue

    print("Histogram for descriptor: %s" % descriptor_name)
    if type(example_value) == float:
        pool = []
        for point_name in point_names:
            point = ds.point(point_name)
            normalized_value = point.value(descriptor_name)
            if not normalization_coeffs:
                value = normalized_value
            else:
                a = normalization_coeffs[descriptor_name]['a']
                b = normalization_coeffs[descriptor_name]['b']
                value = float(normalized_value - b[0]) / a[0]
            pool.append(value)

        plot_histogram(pool, descriptor_name)

    elif type(example_value) == tuple:
        for i in range(0, len(example_value)):
            label = descriptor_name + '.%.3i' % i
            print("\tDimension %i" % i)
            pool = []
            for point_name in point_names:
                point = ds.point(point_name)
                normalized_value = point.value(descriptor_name)[i]
                if not normalization_coeffs or descriptor_name not in normalization_coeffs.keys():
                    value = normalized_value
                else:
                    a = normalization_coeffs[descriptor_name]['a']
                    b = normalization_coeffs[descriptor_name]['b']
                    value = float(normalized_value - b[i]) / a[i]
                pool.append(value)

            plot_histogram(pool, label)

    elif type(example_value) == str:
        pool = []
        for point_name in point_names:
            point = ds.point(point_name)
            value = point.label(descriptor_name)
            pool.append(value)

        keys = sorted(list(set(pool)))
        key_ids = dict()
        for j, key in enumerate(keys):
            key_ids[key] = j
        pool = [key_ids[value] for value in pool]

        plot_histogram(pool, descriptor_name,  x_label_ticks = keys)
