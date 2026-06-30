AUDIO_DESCRIPTOR_TYPE_FLOAT = "float"
AUDIO_DESCRIPTOR_TYPE_INT = "int"
AUDIO_DESCRIPTOR_TYPE_BOOL = "bool"
AUDIO_DESCRIPTOR_TYPE_STRING = "string"
AUDIO_DESCRIPTOR_TYPE_LIST_STRINGS = "list_of_strings"
AUDIO_DESCRIPTOR_TYPE_FLOAT_ARRAY = "float_array"
AUDIO_DESCRIPTOR_TYPE_JSON = "json"  # For complex structures
DEFAULT_AUDIO_DESCRIPTOR_TYPE = AUDIO_DESCRIPTOR_TYPE_FLOAT
DEFAULT_AUDIO_DESCRIPTOR_FLOAT_PRECISION = 3  # Number of decimal digits for float audio descriptors

condition_music_or_instrument_samples = lambda s: s.category_names[0] in ["Music", "Instrument samples"]
condition_instrument_samples = lambda s: s.category_names[0] == "Instrument samples"
condition_sfx_or_soundscapes = lambda s: s.category_names[0] in ["Sound effects", "Soundscapes"]
CONSOLIDATED_ANALYZER_NAME = "consolidated"
CONSOLIDATED_AUDIO_DESCRIPTORS = [
    {
        "name": "category",
        "analyzer": "bst-extractor_v2",
        "original_name": "bst_top_level",
        "type": AUDIO_DESCRIPTOR_TYPE_STRING,
    },
    {
        "name": "subcategory",
        "analyzer": "bst-extractor_v2",
        "original_name": "bst_second_level",
        "type": AUDIO_DESCRIPTOR_TYPE_STRING,
    },
    {
        "name": "amplitude_peak_ratio",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["sfx.max_to_total"],
    },
    {
        "name": "beat_count",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["rhythm.beats_count"],
        "type": AUDIO_DESCRIPTOR_TYPE_INT,
    },
    {
        "name": "beat_loudness",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["rhythm.beats_loudness.mean"],  # Increase precision?
    },
    {
        "name": "beat_times",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["rhythm.beats_position"],
        "type": AUDIO_DESCRIPTOR_TYPE_FLOAT_ARRAY,
        "index": False,
    },
    {
        "name": "boominess",
        "analyzer": "ac-extractor_v3",
        "original_name": "boominess",
    },
    {
        "name": "bpm",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: s.estimate_bpm_from_metadata() or d["fs.bpm"],
    },
    {
        "name": "bpm_confidence",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: 1.0 if s.estimate_bpm_from_metadata() else d["fs.bpm_confidence"],
    },
    {
        "name": "brightness",
        "analyzer": "ac-extractor_v3",
        "original_name": "brightness",
    },
    {
        "name": "decay_strength",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["sfx.strongdecay"],
    },
    {
        "name": "depth",
        "analyzer": "ac-extractor_v3",
        "original_name": "depth",
    },
    {
        "name": "dissonance",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.dissonance.mean"],
    },
    {
        "name": "duration_effective",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["sfx.effective_duration"],
    },
    {
        "name": "dynamic_range",
        "analyzer": "fs-essentia-extractor_v1",
        "original_name": lambda d, s: d["lowlevel.loudness_ebu128.loudness_range"],
    },
    {
        "name": "hardness",
        "analyzer": "ac-extractor_v3",
        "original_name": "hardness",
    },
    {
        "name": "hpcp",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["tonal.hpcp.mean"],
        "type": AUDIO_DESCRIPTOR_TYPE_FLOAT_ARRAY,  # Increase precision?
        "index": False,
    },
    {
        "name": "hpcp_var",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["tonal.hpcp.var"],
        "type": AUDIO_DESCRIPTOR_TYPE_FLOAT_ARRAY,  # Increase precision?
        "index": False,
    },
    {
        "name": "hpcp_crest",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["tonal.hpcp_crest.mean"],
    },
    {
        "name": "hpcp_entropy",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["tonal.hpcp_entropy.mean"],
    },
    {
        "name": "inharmonicity",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["sfx.inharmonicity.mean"],
    },
    {
        "name": "log_attack_time",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["sfx.logattacktime"],
    },
    {
        "name": "loopable",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["fs.loopable"],
        "type": AUDIO_DESCRIPTOR_TYPE_BOOL,
    },
    {
        "name": "loudness",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.loudness_ebu128.integrated"],
    },
    {
        "name": "mfcc",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.mfcc.mean"],
        "type": AUDIO_DESCRIPTOR_TYPE_FLOAT_ARRAY,  # Increase precision?
        "index": False,
    },
    {
        "name": "mfcc_var",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.mfcc.var"],
        "type": AUDIO_DESCRIPTOR_TYPE_FLOAT_ARRAY,  # Increase precision?
        "index": False,
    },
    {
        "name": "note_confidence",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["fs.note_confidence"],
        "condition": condition_instrument_samples,
    },
    {
        "name": "note_midi",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["fs.note_midi"],
        "type": AUDIO_DESCRIPTOR_TYPE_INT,
        "condition": condition_instrument_samples,
    },
    {
        "name": "note_name",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["fs.note_name"],
        "type": AUDIO_DESCRIPTOR_TYPE_STRING,
        "condition": condition_instrument_samples,
    },
    {
        "name": "onset_count",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["rhythm.onset_count"],
        "type": AUDIO_DESCRIPTOR_TYPE_INT,
    },
    {
        "name": "onset_times",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["rhythm.onset_times"],
        "type": AUDIO_DESCRIPTOR_TYPE_FLOAT_ARRAY,
        "index": False,
    },
    {
        "name": "pitch",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.pitch.mean"],
    },
    {
        "name": "pitch_max",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.pitch.max"],
    },
    {
        "name": "pitch_min",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.pitch.min"],
    },
    {
        "name": "pitch_confidence",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.pitch_instantaneous_confidence.mean"],
    },
    {
        "name": "pitch_salience",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.pitch_salience.mean"],
    },
    {
        "name": "pitch_var",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.pitch.var"],
    },
    {
        "name": "reverbness",
        "analyzer": "ac-extractor_v3",
        "original_name": "reverb",
        "type": AUDIO_DESCRIPTOR_TYPE_BOOL,
    },
    {
        "name": "roughness",
        "analyzer": "ac-extractor_v3",
        "original_name": "roughness",
    },
    {
        "name": "sharpness",
        "analyzer": "ac-extractor_v3",
        "original_name": "sharpness",
    },
    {
        "name": "silence_rate",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.silence_rate_30dB.mean"],
    },
    {
        "name": "single_event",
        "analyzer": "ac-extractor_v3",
        "original_name": "single_event",
        "type": AUDIO_DESCRIPTOR_TYPE_BOOL,
        "transformation": lambda v, d, s: v if s.category_names[0] not in ["Music", "Soundscapes"] else False,
    },
    {
        "name": "spectral_centroid",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.spectral_centroid.mean"],
    },
    {
        "name": "spectral_complexity",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.spectral_complexity.mean"],
    },
    {
        "name": "spectral_crest",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.spectral_crest.mean"],
    },
    {
        "name": "spectral_energy",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.spectral_energy.mean"],
    },
    {
        "name": "spectral_entropy",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.spectral_entropy.mean"],
    },
    {
        "name": "spectral_flatness",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.spectral_flatness_db.mean"],
    },
    {
        "name": "spectral_rolloff",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.spectral_rolloff.mean"],
    },
    {
        "name": "spectral_skewness",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.spectral_skewness.mean"],
    },
    {
        "name": "spectral_spread",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.spectral_spread.mean"],
    },
    {
        "name": "start_time",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.sound_start_frame"],
        "transformation": lambda v, d, s: (v * 2048.0) / 44100.0,  # Convert from frames to seconds
    },
    {
        "name": "temporal_centroid",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["sfx.temporal_centroid"],
    },
    {
        "name": "temporal_centroid_ratio",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["sfx.tc_to_total"],
    },
    {
        "name": "temporal_decrease",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["sfx.temporal_decrease"],
    },
    {
        "name": "temporal_skewness",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["sfx.temporal_skewness"],
    },
    {
        "name": "temporal_spread",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["sfx.temporal_spread"],
    },
    {
        "name": "tonality",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["fs.tonality"],
        "type": AUDIO_DESCRIPTOR_TYPE_STRING,
    },
    {
        "name": "tonality_confidence",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["fs.tonality_confidence"],
    },
    {
        "name": "tristimulus",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["sfx.tristimulus.mean"],
        "type": AUDIO_DESCRIPTOR_TYPE_FLOAT_ARRAY,  # Increase precision?
        "index": False,
    },
    {
        "name": "warmth",
        "analyzer": "ac-extractor_v3",
        "original_name": "warmth",
    },
    {
        "name": "zero_crossing_rate",
        "analyzer": "fs-essentia-extractor_v1",
        "get_func": lambda d, s: d["lowlevel.zerocrossingrate.mean"],
    },
    {
        "name": "has_audio_problems",
        "analyzer": "fs-essentia-problem-detection_v1",
        "original_name": "error",
        "type": AUDIO_DESCRIPTOR_TYPE_BOOL,
    },
    {
        "name": "birdnet_detected_class",
        "type": AUDIO_DESCRIPTOR_TYPE_LIST_STRINGS,
        "analyzer": "birdnet_v1",
        "original_name": "detected_classes",
        "transformation": lambda v, d, s: None if v == [] else v,
        "condition": condition_sfx_or_soundscapes,
    },
    {
        "name": "birdnet_detections",
        "analyzer": "birdnet_v1",
        "type": AUDIO_DESCRIPTOR_TYPE_JSON,
        "original_name": "detections",
        "transformation": lambda v, d, s: None if v == [] else v,
        "condition": condition_sfx_or_soundscapes,
        "index": False,
    },
    {
        "name": "birdnet_detections_count",
        "type": AUDIO_DESCRIPTOR_TYPE_INT,
        "analyzer": "birdnet_v1",
        "original_name": "num_detections",
        "condition": condition_sfx_or_soundscapes,
    },
    {
        "name": "fsdsinet_detected_class",
        "type": AUDIO_DESCRIPTOR_TYPE_LIST_STRINGS,
        "analyzer": "fsd-sinet_v1",
        "original_name": "detected_classes",
        "transformation": lambda v, d, s: None if v == [] else v,
    },
    {
        "name": "fsdsinet_detections",
        "analyzer": "fsd-sinet_v1",
        "type": AUDIO_DESCRIPTOR_TYPE_JSON,
        "original_name": "detections",
        "transformation": lambda v, d, s: None if v == [] else v,
        "index": False,
    },
    {
        "name": "fsdsinet_detections_count",
        "type": AUDIO_DESCRIPTOR_TYPE_INT,
        "analyzer": "fsd-sinet_v1",
        "original_name": "num_detections",
    },
]

CONSOLIDATED_AUDIO_DESCRIPTORS_ANALYZER_NAMES = list(set([ad["analyzer"] for ad in CONSOLIDATED_AUDIO_DESCRIPTORS]))
AVAILABLE_AUDIO_DESCRIPTORS_NAMES = [desc["name"] for desc in CONSOLIDATED_AUDIO_DESCRIPTORS]
