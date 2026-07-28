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


import csv
import json
import logging
import os
import re
import shutil
import zlib
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from django.conf import settings

from sounds.models import Sound
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


fields = [
    ("id", lambda sound: sound.id),
    ("created", lambda sound: sound.created.strftime("%Y-%m-%d %H:%M:%S")),
    ("username", lambda sound: sound.username),
    ("user_id", lambda sound: sound.user_id),
    ("title", lambda sound: sound.original_filename),
    ("description", lambda sound: sound.description),
    ("tags", lambda sound: " ".join(sound.tag_array)),
    ("pack_name", lambda sound: sound.pack_name),
    ("bst_category_code", lambda sound: sound.category_code),
    ("geotag", lambda sound: sound.geotag.get_lat_lon_as_string() if hasattr(sound, "geotag") else ""),
    ("license", lambda sound: sound.license.name),
    (
        "generative_ai_preference",
        lambda sound: sound.user.profile.get_gen_ai_preference(category_code=sound.category_code),
    ),
    ("type", lambda sound: sound.type),
    ("duration", lambda sound: sound.duration),
    ("filesize", lambda sound: sound.filesize),
    ("crc32", lambda sound: sound.crc),
    ("avg_rating", lambda sound: sound.avg_rating),
    ("num_ratings", lambda sound: sound.num_ratings),
    ("num_downloads", lambda sound: sound.num_downloads),
    ("num_comments", lambda sound: sound.num_comments),
]

MetadataValue = str | int | float


def get_field_values(
    metadata_dicts: list[dict[str, MetadataValue]], field_name: str, coerce_to: type
) -> list[MetadataValue]:
    return [coerce_to(metadata_dict[field_name]) for metadata_dict in metadata_dicts if field_name in metadata_dict]


def format_bytes(num_bytes: int) -> str:
    units = ["bytes", "KB", "MB", "GB", "TB", "PB"]
    value = float(num_bytes)
    unit_index = 0

    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{num_bytes} {units[unit_index]}"
    return f"{value:.2f} {units[unit_index]}"


def compute_taxonomy_stats(sounds: list[dict[str, MetadataValue]]) -> list[dict[str, MetadataValue]]:
    sound_categories = [sound["bst_category_code"] for sound in sounds if "bst_category_code" in sound]
    return Counter(sound_categories).most_common()


def compute_crc32(file_path: Path) -> str:
    crc32_value = 0
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4096), b""):
            crc32_value = zlib.crc32(chunk, crc32_value)
    return f"{crc32_value & 0xFFFFFFFF:08x}"


def slugify(variant_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", variant_name.lower()).strip("-")
    if not slug:
        raise ValueError(f"Name '{variant_name}' results in an empty slug")
    return slug


def create_datapack_variant(
    variant_name: str,
    condition: callable,
    sounds_metadata: list[dict[str, MetadataValue]],
    output_dir: Path,
    verbose: bool = False,
) -> None:
    variant_slug = slugify(variant_name)

    # Filter sounds with the condition
    filtered_sounds = [sound for sound in sounds_metadata if condition(sound)]

    # Group sounds by their thousand ID (ID 0-999, 1000-1999, etc.) to create manifest and metadata files. Make a list of lists
    grouped_sounds = []
    for sound in filtered_sounds:
        sound_id = int(sound["id"])
        group_index = sound_id // 1000
        if len(grouped_sounds) <= group_index:
            grouped_sounds.extend([[] for _ in range(group_index - len(grouped_sounds) + 1)])
        grouped_sounds[group_index].append(sound)

    # Create directories for manifest and metadata files
    manifests_dir = output_dir / "manifests" / variant_slug
    manifests_dir.mkdir(parents=True)
    metadata_dir = output_dir / "metadata" / variant_slug
    metadata_dir.mkdir(parents=True)
    manifest_files_content_total_size = defaultdict(
        int
    )  # We will save info about the total size of sounds in a manifest file here

    # Iterate sound groups and create files
    for group in grouped_sounds:
        if not group:
            # Because the way in which groups are created, there might be empty groups. Skip them.
            continue
        id_range_number = int(group[0]["id"]) // 1000
        if verbose:
            print(f"- Creating manifest and metadata files for ID range {id_range_number:04d} with {len(group)} sounds")
        manifest_file_path = manifests_dir / f"audio_{id_range_number:04d}"
        metadata_file_path = metadata_dir / f"metadata_{id_range_number:04d}.csv"

        manifest_lines = []
        csv_rows = []
        fields_to_include_in_csv = [
            "id",
            "created",
            "username",
            "title",
            "description",
            "tags",
            "pack_name",
            "bst_category_code",
            "geotag",
            "license",
            "generative_ai_preference",
            "type",
            "duration",
            "filesize",
            "avg_rating",
            "num_ratings",
            "num_downloads",
            "num_comments",
        ]  # All except for user_id and crc32

        manifest_files_content_total_size[id_range_number] = 0  # Initialize total size for this manifest file
        for sound in group:
            manifest_lines.append(
                f"{sound['crc32']} {sound['filesize']} /secret/sounds/{id_range_number}/{sound['id']}_{sound['user_id']}.{sound['type']} {id_range_number}/{sound['id']}.{sound['type']}"
            )
            csv_rows.append({field: sound.get(field, "") for field in fields_to_include_in_csv})
            manifest_files_content_total_size[id_range_number] += int(sound["filesize"])

        # Save manifest file
        with manifest_file_path.open("w", encoding="utf-8") as handle:
            for line in manifest_lines:
                handle.write(f"{line}\n")

        # Save metadata CSV file
        with metadata_file_path.open("w", encoding="utf-8", newline="") as handle:
            if csv_rows:
                writer = csv.DictWriter(handle, fieldnames=fields_to_include_in_csv)
                writer.writeheader()
                writer.writerows(csv_rows)

    metadata_for_variant = {
        "name": variant_name,
        "num_sounds": len(filtered_sounds),
        "full_size": sum(get_field_values(filtered_sounds, "filesize", int)),
        "full_duration": sum(get_field_values(filtered_sounds, "duration", float)),
        "manifest_files": [
            {
                "path": str(manifest_file.relative_to(output_dir)),
                "size": manifest_files_content_total_size[int(manifest_file.stem.split("_")[1])],
            }
            for manifest_file in manifests_dir.iterdir()
            if "_" in manifest_file.stem
        ],
        "metadata_files": [
            {
                "path": str(metadata_file.relative_to(output_dir)),
                "size": metadata_file.stat().st_size,
                "crc32": compute_crc32(metadata_file),
            }
            for metadata_file in metadata_dir.iterdir()
        ],
        "taxonomy_stats": compute_taxonomy_stats(filtered_sounds),
    }

    # Make sure manifest files are sorted alphabetically
    metadata_for_variant["manifest_files"].sort(key=lambda x: x["path"])

    # Add an extra manifest file for the metadata
    metadata_manifest_file_path = manifests_dir / "metadata"
    metadata_manifest_lines = [
        f"{metadata_file_data['crc32']} {metadata_file_data['size']} /secret/data_packs/{str(output_dir).split('/')[-1]}/{metadata_file_data['path']} metadata/{os.path.basename(metadata_file_data['path'])}\n"
        for metadata_file_data in metadata_for_variant["metadata_files"]
    ]
    metadata_manifest_file_path.write_text("".join(metadata_manifest_lines), encoding="utf-8")
    metadata_for_variant["manifest_files"] = [
        {
            "path": str(metadata_manifest_file_path.relative_to(output_dir)),
            "size": metadata_manifest_file_path.stat().st_size,
        }
    ] + metadata_for_variant["manifest_files"]

    return metadata_for_variant


def condition_commercial_allowed(sound: dict[str, MetadataValue]) -> bool:
    return sound.get("license") not in ["Attribution-NonCommercial"]


def condition_gen_ai_allowed(
    sound: dict[str, MetadataValue], commercial_use_wanted=False, open_source_model=False
) -> bool:
    preference = sound.get("generative_ai_preference", settings.AI_PREF_NO_ADDITIONAL_PREFERENCES)

    if preference == settings.AI_PREF_NO_GEN_AI:
        # If preferent is gen AI opt-out, don't allow gen AI
        return False

    if commercial_use_wanted:
        # In case commercial use is wanted, we only allow gen AI if
        #   1) the CC license allows it and preference is settings.AI_PREF_NO_ADDITIONAL_PREFERENCES
        #   2) if the CC license allows it, the preference is settings.AI_PREF_OPEN_MODELS and open_source_model is True
        if preference == settings.AI_PREF_NO_ADDITIONAL_PREFERENCES:
            return condition_commercial_allowed(sound)
        elif preference == settings.AI_PREF_OPEN_MODELS:
            return condition_commercial_allowed(sound) and open_source_model
        else:
            return False

    # If commercial use is not wanted, we allow gen AI if
    #   1) the CC license allows it and preference is settings.AI_PREF_NO_ADDITIONAL_PREFERENCES
    #   2) if the CC license allows it, the preference is settings.AI_PREF_OPEN_MODELS and open_source_model is True
    #   3) if the CC license allows it, the preference is settings.AI_PREF_OPEN_NONCOMMERCIAL_MODELS and open_source_model is True
    if preference == settings.AI_PREF_NO_ADDITIONAL_PREFERENCES:
        return True
    elif preference == settings.AI_PREF_OPEN_MODELS:
        return open_source_model
    elif preference == settings.AI_PREF_OPEN_NONCOMMERCIAL_MODELS:
        return (
            open_source_model  # We don't check commerical here because commercial_use_wanted is False, so it's allowed
        )

    return True  # We should never reach here


def condition_attribution_not_required(sound: dict[str, MetadataValue]) -> bool:
    return sound.get("license") == "Creative Commons 0"


def create_data_pack_files(
    sounds_metadata: list[dict[str, MetadataValue]], output_dir: Path, verbose: bool = False
) -> None:
    metadata = {}

    for variant_name, condition, variant_extra_metadata in [
        (
            "Complete",
            lambda sound: True,
            {
                "gen_ai_allowed": False,
                "commercial_use_allowed": False,
                "attribution_required": True,
                "open_source_gen_ai_model_required": True,
            },
        ),
        (
            "Commercial use + Generative AI (Open source model)",
            lambda sound: condition_commercial_allowed(sound)
            and condition_gen_ai_allowed(sound, commercial_use_wanted=True, open_source_model=True),
            {
                "gen_ai_allowed": True,
                "commercial_use_allowed": True,
                "attribution_required": True,
                "open_source_gen_ai_model_required": True,
            },
        ),
        (
            "Commercial use + Generative AI (No open source model)",
            lambda sound: condition_commercial_allowed(sound)
            and condition_gen_ai_allowed(sound, commercial_use_wanted=True, open_source_model=False),
            {
                "gen_ai_allowed": True,
                "commercial_use_allowed": True,
                "attribution_required": True,
                "open_source_gen_ai_model_required": False,
            },
        ),
        (
            "Commercial use + Generative AI (No open source model) + No attribution required",
            lambda sound: condition_commercial_allowed(sound)
            and condition_gen_ai_allowed(sound, commercial_use_wanted=True, open_source_model=False)
            and condition_attribution_not_required(sound),
            {
                "gen_ai_allowed": True,
                "commercial_use_allowed": True,
                "attribution_required": False,
                "open_source_gen_ai_model_required": False,
            },
        ),
    ]:
        print(f"Creating data pack variant '{variant_name}'")
        variant_metadata = create_datapack_variant(
            variant_name, condition, sounds_metadata, output_dir, verbose=verbose
        )
        variant_metadata.update(variant_extra_metadata)
        metadata.setdefault("variants", []).append(variant_metadata)

    return metadata


class Command(LoggingBaseCommand):
    help = """This command loads sounds metadata from the database and creates all files needed for creating a downloadable 
    Data Pack for the Freesound Data Packs Portal."""

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            action="store",
            dest="limit",
            default=None,
            help="Maximum number of sounds to be included. Useful for debugging.",
        )
        parser.add_argument(
            "--skip-audio-existence-check",
            action="store_true",
            help="Skip checking that referenced audio files exist.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose logging.",
        )
        parser.add_argument(
            "--datapack-dir-name",
            action="store",
            dest="datapack_dir_name",
            default="",
            help="Optional suffix to append to the YYYYMMDD output directory name.",
        )

    def handle(self, *args, **options):
        self.log_start()

        # Load all sounds metadata from the database. Do it in chunks.
        all_sound_ids = list(Sound.objects.values_list("id", flat=True))[: options.get("limit", None)]
        max_sound_id = max(all_sound_ids)
        sounds_metadata = []
        num_non_existing = 0
        total_chunks = (max_sound_id // 1000) + 1
        for chunk_start in range(0, max_sound_id + 1, 1000):
            chunk_index = (chunk_start // 1000) + 1

            # Get corresponding Sound objects. include_audio_descriptors=True is used to avoid N+1 queries when accessing the generated bst category (if needed).
            sound_ids = all_sound_ids[chunk_start : chunk_start + 1000]
            sound_objects = Sound.objects.ordered_ids(sorted(sound_ids), include_audio_descriptors=True)
            for sound in sound_objects:
                if not options["skip_audio_existence_check"]:
                    if not os.path.exists(sound.locations("path")):
                        num_non_existing += 1
                        continue
                sound_dict = {f: l(sound) for f, l in fields}
                sounds_metadata.append(sound_dict)
            console_logger.info(f"Loaded sounds from chunk {chunk_index}/{total_chunks}")

        # Skip sampling + sounds
        num_sounds_before_sampling_plus_removal = len(sounds_metadata)
        sounds_metadata = [sound for sound in sounds_metadata if sound["license"] != "Sampling+"]
        num_skipped_sampling_plus = num_sounds_before_sampling_plus_removal - len(sounds_metadata)

        # Show some stats about the loaded sounds metadata
        print(f"Loaded metadata for {len(sounds_metadata)} sounds")
        if num_non_existing > 0:
            print(f"Number of non-existing sound files: {num_non_existing}")
        if num_skipped_sampling_plus > 0:
            print(f"Number of sampling+ sounds skipped: {num_skipped_sampling_plus}")

        # Create output directory if missing, or delete it if existing
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        datapack_dir_name = (options.get("datapack_dir_name") or "").strip()
        output_dir_basename = f"{date_prefix}-{datapack_dir_name}" if datapack_dir_name else date_prefix
        output_dir_path = Path(settings.DATA_PACKS_PATH) / "data_packs" / output_dir_basename
        if output_dir_path.exists():
            shutil.rmtree(output_dir_path)
        output_dir_path.mkdir(parents=True)

        # Create data pack files with different variants
        datapack_metadata = create_data_pack_files(sounds_metadata, output_dir_path, verbose=options["verbose"])

        # Save datapack metadata file
        metadata_file_path = output_dir_path / "metadata.json"
        with metadata_file_path.open("w", encoding="utf-8") as handle:
            json.dump(datapack_metadata, handle, indent=4)

        # Finally print some stats about created variants
        print(f'\nData pack created and saved to "{output_dir_path}".')
        for variant in datapack_metadata.get("variants", []):
            print(
                f"- Variant '{variant['name']}': {variant['num_sounds']} sounds, "
                f"{format_bytes(variant['full_size'])}, {variant['full_duration'] // 3600:.2f} hours"
            )

        self.log_end({"output_dir": str(output_dir_path), "num_sounds": len(sounds_metadata)})
