# STRETCH AND TILE

This repository converts raster datasets into TMS tiles suitable for web mapping. Optionally, the workflow also publishes the output TMS tiles to S3.

## Features

- Generate TMS tiles from a specified raster dataset with GDAL for specified zoom levels
- Generate a quickview `.html` file
- Upload TMS tiles to the appropriate S3 bucket 
- Remove the locally created outputs after a successful S3 upload

## Caveats

- This tool expects a single raster dataset as input
- Already existing files will be overwritten, both locally and on S3
- deleting locally created ouputs is only possible after successful upload to S3

## Input requirements

A single configuration `.yaml` file is required to execute the worklow.
The tool processes **one raster per run**, so each configuration file should refer to a single scene only.

A template configuration file is provided: `configs/_EXAMPLE.yaml`

Create a copy of `_EXAMPLE.yaml` in the `configs/` folder and name it after the scene following the convention `ISO3_Locality_Sensor_Date`, for example `AUT_Vienna_SPOT_01Sep2026.yaml`.

### Configuration file template

```yaml
# --- INPUTS: Required ---
input_raster: I:\IMAGERY\AUT_Vienna_PNEO_01Sep2026\AUT_Vienna_PNEO_01Sep2026_RGB_stretched.tif
mm_name: 1234_5678_040_01122026

# --- EXPORT & CLEANUP: Required ---
s3_export: false
remove_local: false # <-- CAUTION: Deletes the entire scene foler with all its contents ! ONLY possible after successful s3 upload

# --- DEFAULTS: Optional ---
min_zoom: 10
max_zoom: 20
filetype: webp # <-- webp OR png
s3_profile: prod
```

### Parameter reference

> [!IMPORTANT]
> - Deleting the input directory and the locally created outputs is only possible after a successful S3 upload. Therefore, `remove_local: true` requires `s3_export: true`.

| Parameter | Status | Type | Default | Description |
|----------|--------|------|---------|-------------|
| `scene` | Required | `string` | — | Scene identifier used for processing. Mandatory naming convention: `ISO3_Locality_Sensor_Date`. |
| `input_root` | Required | `string` | — | Root directory containing the input scene data. |
| `mm_name` | Required | `string` | — | Folder name for the upload to the s3 bucket, following the MM naming convention: `Elixir(_)Ticket_NumericISO3_DDMMYYYY`|
| `s3_export` | Required | `boolean` | `false` | If `true`, upload generated outputs and archive data to the configured S3 buckets. |
| `remove_local` | Required | `boolean` | `false` | If `true`, remove the input directory and locally generated outputs. ONLY possible if `s3_export`: `true`. |
| `min_zoom` | Optional | `integer` | `10` | Minimum zoom level of the TMS tiles. |
| `max_zoom` | Optional | `integer` | `20` | Maximum zoom level of the TMS tiles. |
| `rft` | Optional | `string` | E:\MDCS\Parameter\RasterFunctionTemplates\Stretching\ITEM_Stretch_PercMinMax_025_05_Stats_AutoGamma_1_255.rft.xml | Stretch raster function template path. |
| `s3_profile` | Optional | `string` | `prod` | AWS profile used for S3 authentication and upload operations. |

## Usage

Run the tool from the repository root by passing the configuration file, for example:

```bash
python tms_tiler.py configs/AUT_Vienna_SPOT_01Sep2026.yaml
```

## Tests

At present, the repository includes a single integration test for validating AWS authentication, connectivity, and basic S3 operations.

### Run the test

Run the test from the repository root:

```bash
python tests/test_s3.py
```
