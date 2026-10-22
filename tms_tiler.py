# This script utilizes 'gdal raster tile'
# Required gdal version >= 3.11
# See official documentation:
# https://gdal.org/en/stable/programs/gdal_raster_tile.html

import os
import shutil
import subprocess
import time

from utils.io_utils import (
    parse_args,
    load_config,
    format_duration
    )
from utils.s3_utils import upload_to_s3


if __name__ == "__main__":
    start_time = time.perf_counter()

    # parse and load the config
    args = parse_args()
    config = load_config(args.config)

    # Prevent creating outputs just to delete them without s3 upload
    if config.get("remove_local", False) and not config.get("s3_export", False):
        raise ValueError("remove_local=True requires s3_export=True.")

    # TMS tile filetype
    filetype = str(config.get("filetype", "")).strip().lower()
    if filetype not in {"png", "webp"}:
        raise ValueError(
            "Invalid or missing config value: filetype. Expected 'png' or 'webp'."
        )
    
    gdal_format = filetype.upper()

    # build IO paths
    raster_path = os.path.join(config["input_raster"])

    # set up gdal tiling
    out_tms = os.path.join(os.path.dirname(raster_path), "TMS")
    os.makedirs(out_tms, exist_ok=True)

    min_zoom = int(config.get("min_zoom", 10))
    max_zoom = int(config.get("max_zoom", 20))

    if min_zoom > max_zoom:
        raise ValueError(
            f"min_zoom ({min_zoom}) cannot be greater than max_zoom ({max_zoom})"
        )

    # The current ArcGisPro v3.5.6 is not compatible with the min. required version of GDAL >= 3.11
    # Therefore, GDAL 3.12.3 is installed in a stand-alone environment and called as a subprocess.
    gdal_exe = r"E:\RESOURCES\PYTHON\envs\gdal_312\Library\bin\gdal.exe"
    
    cmd = [
        gdal_exe,
        "raster",
        "tile",
        "--min-zoom", str(min_zoom),
        "--max-zoom", str(max_zoom),
        "--skip-blank",
        "--format", gdal_format,
        "--webviewer", "openlayers",
        raster_path,
        out_tms,
    ]
    
    if filetype == "webp":
        cmd.extend([
            "--co", "QUALITY=100",
        ])

    # Start TMS tiling
    print("Running command:")
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    subprocess.run(cmd, check=True)

    # S3 export
    if config.get("s3_export", False):
        upload_to_s3(out_tms, config)
    
    # delete locally created tms output, after successful s3 upload
    if config.get("remove_local", False):
        shutil.rmtree(out_tms, ignore_errors=False)

    total_elapsed = time.perf_counter() - start_time
    print(f"Done. Tiles written to: {out_tms}")
    print(f"Total runtime: {format_duration(total_elapsed)} ({total_elapsed:.2f} seconds)")

