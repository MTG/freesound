from solr import *
from sounds.models import Sound
import logging

logger = logging.getLogger("search")

def convert_to_solr_document(sound):
    logger.info("creating solr XML from sound %d" % sound.id)
    document = {}

    document["id"] = sound.id
    if sound.pack:
        document["pack"] = sound.pack.name
        document["pack_id"] = sound.pack.id
    document["username"] = sound.user.username
    document["user_id"] = sound.user.id
    document["created"] = sound.created
    
    # rename all of these to reflect db fields?
    document["filename"] = sound.original_filename
    document["downloads"] = sound.num_downloads
    document["votes"] = sound.num_ratings
    document["rating"] = sound.avg_rating
    
    # TODO: add license!! go through all fields...
    # make sure the solr names are human readable, because we will use them "as is"
    # so num_comments should be "comments", pack should be pack, not pack_original, pack should become pack_tokenized
    
    # should we add all the paths?
    # should we add the base URL?
    document["url_preview"] = sound.paths()["preview_path"]
    document["url_image"] = sound.paths()["waveform_path_m"]
    
    document["is_remix"] = bool(sound.sources.count())
    document["is_geotagged"] = sound.geotag != None

    document["type"] = sound.type
    document["samplerate"] = int(sound.samplerate)
    document["bitrate"] = sound.bitrate
    document["bitdepth"] = sound.bitdepth
    document["channels"] = sound.channels
    document["duration"] = sound.duration
    document["filesize"] = sound.filesize
    document["description"] = sound.description
    document["tag"] = [taggeditem.tag.name for taggeditem in sound.tags.all()]
    document["comment"] = [comment.comment for comment in sound.comments.all()]
    
    return document


def add_sound_to_solr(sound):
    logger.info("adding single sound to solr index")
    try:
        Solr().add([convert_to_solr_document(sound)])
    except SolrException, e:
        logger.error("failed to add sound %d to solr index, reason: %s" % (sound.id, str(e)))


def add_sounds_to_solr(sounds):
    logger.info("adding multiple sounds to solr index")
    try:
        Solr().add(map(convert_to_solr_document, sounds))
    except SolrException, e:
        logger.error("failed to add sound batch to solr index, reason: %s" % (sound.id, str(e)))


def add_all_sounds_to_solr(slice_size=100):
    qs = Sound.objects.select_related("pack", "user").filter(processing_state="OK", moderation_state="OK")
    num_sounds = qs.count()
    for i in range(0, num_sounds, slice_size):
        add_sounds_to_solr(qs[i:i+slice_size])