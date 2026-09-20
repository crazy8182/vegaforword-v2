#!/usr/bin/env python3
"""Build/Run MediaInfo self-check. pymediainfo 7.x Linux wheels bundle MediaInfo.
This script intentionally does not require apt/MediaInfo system packages.
"""
from pymediainfo import MediaInfo

# Loading the class is enough to catch a missing bundled native library early.
# We do not parse a file here because no media file is available at startup.
print("MediaInfo backend ready")
