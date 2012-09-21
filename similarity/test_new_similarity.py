from gaia_wrapper import GaiaWrapper
import os
from settings import PRESETS


gaia = GaiaWrapper()

names = ['10', '100', '1000', '10000', '100000', '100001', '100002', '100003', '100004', '100005', '100006', '100007', '100008', '100009', '10001', '100010', '100011', '100012', '100013', '100014', '100015', '100016', '100017', '100018', '100019', '10002', '100020', '100021', '100022', '100023', '100024', '100025', '100026', '100027', '100028', '100029', '10003', '100030', '100031', '100032', '100033', '100035', '100036', '100037', '100038', '100039', '10004', '100040', '100041', '100042']


for preset in PRESETS:
    # Test normal similarity search
    point = gaia.get_point(names[0])
    print point.value('spectral_centroid.mean')
    print "Similarity search"
    rr = gaia.search_dataset(names[0],10,preset)
    for r in rr:
        p = gaia.get_point(r[0])
        print r, p.value('spectral_centroid.mean')


'''
# Test search with yaml point
pointname = '/home/frederic/Desktop/freesound-similarity/analysis/159999_2558789_statistics.yaml'
print "Similarity search (from yaml point)"
rr = gaia.search_dataset(pointname,10,'test')
for r in rr:
    p = gaia.get_point(r[0])
    print r, p.value('spectral_centroid.mean')

# Test content based search
content_based_params = {
    'target': {'.lowlevel.spectral_centroid.mean': 100.0},
    'filter': "WHERE value.lowlevel.spectral_centroid.mean>0.3 AND value.lowlevel.spectral_centroid.mean<0.4"
}
print "Content-based search"
rr = gaia.query_dataset(content_based_params, 10)
for r in rr:
    p = gaia.get_point(r[0])
    print r, p.value('spectral_centroid.mean')



MAX = 10
base_path = '/home/frederic/Desktop/freesound-similarity/analysis/'
point_locations = os.listdir(base_path)
new_point_names = []
i = 0
for location in point_locations:
    if str(location)[-4:] == "yaml":
        if i > MAX:
            break
        full_path = base_path + str(location)
        name = str(location).split("_")[0]
        new_point_names.append([name,full_path])
        i += 1

# Add points
for name,location in new_point_names:
    print "Adding point " + name
    gaia.add_point(location,name)

# Save into a new db
print "Saving..."
gaia.save_index(path = '/home/frederic/Desktop/freesound-similarity/save_test.db')

# Delete points
for name,location in new_point_names:
    print "Deleting point " + name
    gaia.delete_point(name)
'''