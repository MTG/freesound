from sets import Set
import re

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
    """
    if tags are given as:
    [ {"name": "tag1", "count": 1}, {"name": "tag2", "count": 200}, {"name": "tag3", "count": 200}]
    after this function the list will look like this:
    [ {"name": "tag1", "count": 1, "size": 0.7}, {"name": "tag2", "count": 200, "size": 1.8}, {"name": "tag3", "count": 200, "size": 1.8}]
    """
    unique_counts = sorted(dict((tag["count"], 1) for tag in tags).keys())
    lookup = dict(zip(unique_counts, size_generator(small_size, large_size, len(unique_counts))))
    tags = [annotate(tag, size=lookup[tag["count"]]) for tag in tags]
    if sort:
        tags.sort(cmp=lambda x, y: cmp(x["name"].lower(), y["name"].lower()))
    return tags

alphanum_only = re.compile(r"[^ a-zA-Z0-9-]")
multi_dashes = re.compile(r"-+")

def clean_and_split_tags(tags):
    tags = alphanum_only.sub("", tags)
    tags = multi_dashes.sub("-", tags)
    common_words = "the of to and an in is it you that he was for on are with as i his they be at".split()
    return Set([tag for tag in [tag.strip('-') for tag in tags.split()] if tag and tag not in common_words])    