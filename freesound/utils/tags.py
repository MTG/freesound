def size_generator(small_size, large_size, num_items):
    if num_items <= 1:
        yield (small_size + large_size)*0.5
    else:
        for i in range(0,num_items):
            yield (i*(large_size - small_size))/(num_items-1) + small_size;

def annotate(dictionary, **kwargs):
    x = dictionary.copy()
    x.update(**kwargs)
    return x

def annotate_tags(tags, sort=True, small_size=0.7, large_size=1.8):
    unique_counts = sorted(dict((tag["count"], 1) for tag in tags).keys())
    lookup = dict(zip(unique_counts, size_generator(small_size, large_size, len(unique_counts))))
    tags = [annotate(tag, size=lookup[tag["count"]]) for tag in tags]
    if sort:
        tags.sort(cmp=lambda x, y: cmp(x["name"].lower(), y["name"].lower()))
    return tags