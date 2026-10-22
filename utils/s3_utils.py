import os
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

import boto3
from botocore.config import Config


def get_s3_client(profile_name: str):
    """Create and return an S3 client from an AWS profile."""
    if not profile_name:
        raise ValueError("Missing required S3 config value: s3_profile")

    session = boto3.Session(profile_name=profile_name)
    return session.client(
        "s3",
        config=Config(
            max_pool_connections=128,
            retries={"max_attempts": 10, "mode": "adaptive"},
        ),
    )


def _get_content_type(filetype: str) -> str:
    """Map configured filetype to S3 ContentType."""
    if not filetype:
        raise ValueError("Missing required config value: filetype")

    filetype = str(filetype).strip().lower()

    if filetype == "png":
        return "image/png"
    if filetype == "webp":
        return "image/webp"

    raise ValueError(
        f"Unsupported filetype: {filetype}. Expected 'png' or 'webp'."
    )


def _upload_file(
    s3_client,
    local_file: str,
    bucket: str,
    s3_key: str,
    content_type: str,
) -> None:
    """Upload a single file to S3."""
    s3_client.upload_file(
        local_file,
        bucket,
        s3_key,
        ExtraArgs={
            "ContentType": content_type,
        },
    )


def _iter_local_files(local_dir: str):
    """Yield (local_file, relative_path) for all files in a directory tree."""
    for root, _, files in os.walk(local_dir):
        for filename in files:
            local_file = os.path.join(root, filename)
            rel_path = os.path.relpath(local_file, local_dir).replace(os.sep, "/")
            yield local_file, rel_path


def _upload_directory(
    s3_client,
    local_dir: str,
    bucket: str,
    s3_prefix: str,
    content_type: str,
    max_workers: int = 64,
) -> int:
    """Upload a directory tree to S3 in parallel, preserving relative paths."""
    if not os.path.isdir(local_dir):
        raise FileNotFoundError(f"Local directory not found: {local_dir}")

    count = 0
    pending = set()

    def upload_one(local_file: str, rel_path: str):
        s3_key = f"{s3_prefix.rstrip('/')}/{rel_path}"
        _upload_file(s3_client, local_file, bucket, s3_key, content_type)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for local_file, rel_path in _iter_local_files(local_dir):
            future = executor.submit(upload_one, local_file, rel_path)
            pending.add(future)

            if len(pending) >= max_workers * 4:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for f in done:
                    f.result()
                    count += 1
                    if count % 5000 == 0:
                        print(f"  Uploaded:   {count:,} file(s)")

        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for f in done:
                f.result()
                count += 1
                if count % 5000 == 0:
                    print(f"  Uploaded:   {count:,} file(s)")

    return count


def _s3_prefix_exists(s3_client, bucket: str, prefix: str) -> bool:
    """Return whether the given S3 prefix already contains objects."""
    response = s3_client.list_objects_v2(
        Bucket=bucket,
        Prefix=prefix.rstrip("/") + "/",
        MaxKeys=1,
    )
    return "Contents" in response


def _delete_s3_prefix(s3_client, bucket: str, prefix: str) -> int:
    """
    Delete all objects under an S3 prefix.

    Returns:
        int: Number of objects requested for deletion.
    """
    normalized_prefix = prefix.rstrip("/") + "/"
    deleted_count = 0

    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=normalized_prefix)

    batch = []
    for page in pages:
        for obj in page.get("Contents", []):
            batch.append({"Key": obj["Key"]})

            if len(batch) == 1000:
                s3_client.delete_objects(
                    Bucket=bucket,
                    Delete={"Objects": batch, "Quiet": True},
                )
                deleted_count += len(batch)
                batch = []

    if batch:
        s3_client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": batch, "Quiet": True},
        )
        deleted_count += len(batch)

    return deleted_count


def upload_to_s3(
    local_tms_dir: str,
    config: dict,
    delete_first: bool = False,
    max_workers: int = 64,
) -> None:
    """
    Upload the contents of the local TMS directory to:
    s3://prod-msf-eo-pub-s3/MMP/<mm_name>/

    Args:
        local_tms_dir (str): Local TMS output directory.
        config (dict): Parsed YAML configuration. Must contain:
            - s3_profile
            - mm_name
            - filetype
        delete_first (bool): If True, delete the S3 prefix before upload.
        max_workers (int): Number of parallel upload workers.
    """
    s3_profile = config.get("s3_profile")
    mm_name = config.get("mm_name")
    filetype = config.get("filetype")

    if not s3_profile:
        raise ValueError("Missing required S3 config value: s3_profile")
    if not mm_name or not str(mm_name).strip():
        raise ValueError("Missing required config value: mm_name")

    mm_name = str(mm_name).strip()
    content_type = _get_content_type(filetype)

    if not os.path.isdir(local_tms_dir):
        raise FileNotFoundError(f"Local TMS directory not found: {local_tms_dir}")

    bucket = "prod-msf-eo-pub-s3"
    s3_prefix = f"MMP/{mm_name}"

    s3_client = get_s3_client(s3_profile)

    print("\nPublishing TMS to S3")
    print(f"  Local path:    {local_tms_dir}")
    print(f"  S3 prefix:     s3://{bucket}/{s3_prefix}/")
    print(f"  Filetype:      {str(filetype).strip().lower()}")
    print(f"  Content-Type:  {content_type}")

    if delete_first and _s3_prefix_exists(s3_client, bucket, s3_prefix):
        print("  Folder already exists on S3, deleting it first...")
        deleted_count = _delete_s3_prefix(s3_client, bucket, s3_prefix)
        print(f"  Deleted:       {deleted_count:,} object(s)")

    uploaded_count = _upload_directory(
        s3_client,
        local_tms_dir,
        bucket,
        s3_prefix,
        content_type=content_type,
        max_workers=max_workers,
    )

    print(f"  Uploaded:      {uploaded_count:,} file(s)")
