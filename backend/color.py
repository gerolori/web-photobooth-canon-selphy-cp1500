from PIL import Image, ImageCms
import os
from config import PROFILES, CORRECTION_UPLOADED, CORRECTION_PROCESSED

ICC_PROFILE = os.path.join(PROFILES, "Canon_SELPHY_CP1500.icc")

def apply_correction(input_path):
    """Apply ICC + color filter and save in the processed folder"""
    img = Image.open(input_path)
    if ICC_PROFILE and os.path.exists(ICC_PROFILE):
        img = ImageCms.profileToProfile(img, ICC_PROFILE, ICC_PROFILE)
    output_path = os.path.join(CORRECTION_PROCESSED, os.path.basename(input_path))
    img.save(output_path)
    return output_path
