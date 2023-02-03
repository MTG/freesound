#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from past.utils import old_div
import re


def size_generator(small_size, large_size, num_items):
    if num_items <= 1:
        yield (small_size + large_size)*0.5
    else:
        for i in range(0,num_items):
            yield old_div((i*(large_size - small_size)),(num_items-1)) + small_size;

def annotate(dictionary, **kwargs):
    x = dictionary.copy()
    x.update(**kwargs)
    return x


def annotate_tags(tags, sort=None, small_size=0.7, large_size=1.8):
    """
    Process a list of tags with counts and annotate it with computed size. Size will be proportional to count.

    Args:
        tags (List[dict]): list of dictionaries with the tag "name" and "count" (see example below)
        sort (str or None): whether to sort the annotated list by "name", "count" or None
        small_size (float): smallest annotated size
        large_size (float): highest annotated range

    Returns:
        List[dict]: list of dictionaries with the tag "name", "count" and "size"

    For example, if tags are given as:
    [ {"name": "tag1", "count": 1}, {"name": "tag2", "count": 200}, {"name": "tag3", "count": 200}]
    after this function the list will look like this:
    [ {"name": "tag1", "count": 1, "size": 0.7}, {"name": "tag2", "count": 200, "size": 1.8}, {"name": "tag3", "count": 200, "size": 1.8}]
    """
    unique_counts = sorted({tag["count"] for tag in tags})
    lookup = dict(zip(unique_counts, size_generator(small_size, large_size, len(unique_counts))))
    tags = [annotate(tag, size=lookup[tag["count"]]) for tag in tags]
    if sort is not None:
        if sort == "name":
            tags.sort(key=lambda x: x["name"].lower())
        elif sort == "count":
            tags.sort(key=lambda x: x["count"], reverse=True)
    return tags


alphanum_only = re.compile(r"[^ a-zA-Z0-9-]")
multi_dashes = re.compile(r"-+")


def clean_and_split_tags(tags):
    """
    >>> sorted(clean_and_split_tags("a,b\\tc d\\n\\ne"))
    ['a', 'b', 'c', 'd', 'e']
    >>> sorted(clean_and_split_tags("apple\\n\\n\\n    field-recording tree"))
    ['apple', 'field-recording', 'tree']
    """

    tags = alphanum_only.sub(" ", tags)
    tags = multi_dashes.sub("-", tags)
    common_words = "the of to and an in is it you that he was for on are with as i his they be at".split() #@UnusedVariable
    return {tag for tag in [tag.strip('-') for tag in tags.split()] if tag and tag not in common_words}
