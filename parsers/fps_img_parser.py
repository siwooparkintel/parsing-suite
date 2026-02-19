#!/usr/bin/env python3
"""
FPS Image Parser

Extracts FPS (Frames Per Second) data from game benchmark screenshot images.
Uses OCR to detect and parse FPS values from benchmark result screens.
"""

import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    import pytesseract
except ImportError:
    pytesseract = None


class FPSImageParser:
    """Parser for extracting FPS data from screenshot images."""
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize FPS Image Parser.
        
        Args:
            tesseract_path: Path to tesseract executable. If None, assumes it's in PATH.
        """
        if pytesseract is None:
            raise ImportError(
                "pytesseract not installed. Install with: pip install pytesseract opencv-python Pillow"
            )
        
        if cv2 is None:
            raise ImportError(
                "opencv-python not installed. Install with: pip install opencv-python"
            )
        
        if np is None:
            raise ImportError(
                "numpy not installed. Install with: pip install numpy"
            )
        
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Common FPS pattern variations
        self.fps_patterns = [
            r'(?:Average\s*)?FPS[:\s]*([0-9]+\.?[0-9]*)',
            r'Avg[:\s]*FPS[:\s]*([0-9]+\.?[0-9]*)',
            r'(?:Average|Avg)[:\s]*([0-9]+\.?[0-9]*)\s*FPS',
            r'([0-9]+\.?[0-9]*)\s*FPS',
            r'FPS[:\s]*([0-9]+)',
            r'Frames[:\s]*([0-9]+\.?[0-9]*)',
            r'Min[:\s]*FPS[:\s]*([0-9]+\.?[0-9]*)',
            r'Max[:\s]*FPS[:\s]*([0-9]+\.?[0-9]*)',
            r'1%\s*Low[:\s]*([0-9]+\.?[0-9]*)',
            r'0\.1%\s*Low[:\s]*([0-9]+\.?[0-9]*)',
        ]
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy.
        
        Args:
            image_path: Path to the screenshot image
            
        Returns:
            Preprocessed image as numpy array
        """
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to get better contrast
        # Try adaptive threshold for varying lighting conditions
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Alternative: Simple binary threshold (often works better for benchmark screens)
        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
        
        return denoised
    
    def extract_text(self, image_path: str, preprocess: bool = True) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image_path: Path to the screenshot image
            preprocess: Whether to preprocess the image
            
        Returns:
            Extracted text string
        """
        if preprocess:
            img = self.preprocess_image(image_path)
        else:
            img = cv2.imread(image_path)
        
        # Use pytesseract to extract text
        # Configure for better FPS number recognition
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img, config=custom_config)
        
        return text
    
    def parse_fps_from_text(self, text: str) -> Dict[str, float]:
        """
        Parse FPS values from extracted text.
        
        Args:
            text: Text extracted from image
            
        Returns:
            Dictionary with FPS metrics (avg, min, max, etc.)
        """
        fps_data = {}
        
        # Preserve original text with newlines for table parsing
        text_with_newlines = text
        
        # Clean up text for simple pattern matching
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        # Try to find average FPS (most common)
        for pattern in [
            r'Average\s*FPS[:\s]*([0-9]+\.?[0-9]*)',
            r'Avg\.?\s*FPS[:\s]*([0-9]+\.?[0-9]*)',
            r'(?:Average|Avg)\.?[:\s]*([0-9]+\.?[0-9]*)\s*FPS',
            r'Mean\s*FPS[:\s]*([0-9]+\.?[0-9]*)',
            r'(?:^|\s)FPS[:\s]*([0-9]+\.?[0-9]*)(?:\s|$)',  # Standalone FPS
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fps_data['avg_fps'] = float(match.group(1))
                break
        
        # Try to parse table format (like Shadow of Tomb Raider)
        # Format: "FPS CPUGame CPU Render GPU\nMin 64 122 72\nMax 158 390 153\nAverage 89 185 92"
        table_match = re.search(
            r'FPS\s+\S+\s+\S+\s+\S+\s+\S+.*?Min\s+([0-9]+)\s+([0-9]+)\s+([0-9]+).*?Max\s+([0-9]+)\s+([0-9]+)\s+([0-9]+).*?Average\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)',
            text_with_newlines,
            re.IGNORECASE | re.DOTALL
        )
        
        if table_match:
            # Extract GPU values (last column in the table)
            fps_data['min_fps'] = float(table_match.group(3))  # GPU Min
            fps_data['max_fps'] = float(table_match.group(6))  # GPU Max
            if 'avg_fps' not in fps_data:
                fps_data['avg_fps'] = float(table_match.group(9))  # GPU Average
        
        # Try to find min FPS (fallback patterns)
        if 'min_fps' not in fps_data:
            for pattern in [
                r'Min(?:imum)?\s*FPS[:\s]*([0-9]+\.?[0-9]*)',
                r'Min\.?[:\s]*([0-9]+\.?[0-9]*)\s*FPS',
                r'Minimum[:\s]*([0-9]+\.?[0-9]*)',
                r'1%\s*Low[:\s]*([0-9]+\.?[0-9]*)',
                r'Lowest\s*FPS[:\s]*([0-9]+\.?[0-9]*)',
            ]:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    fps_data['min_fps'] = float(match.group(1))
                    break
        
        # Try to find max FPS (fallback patterns)
        if 'max_fps' not in fps_data:
            for pattern in [
                r'Max(?:imum)?\s*FPS[:\s]*([0-9]+\.?[0-9]*)',
                r'Max\.?[:\s]*([0-9]+\.?[0-9]*)\s*FPS',
                r'Maximum[:\s]*([0-9]+\.?[0-9]*)',
                r'Highest\s*FPS[:\s]*([0-9]+\.?[0-9]*)',
                r'Peak\s*FPS[:\s]*([0-9]+\.?[0-9]*)',
            ]:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    fps_data['max_fps'] = float(match.group(1))
                    break
        
        # Try to find resolution - more comprehensive patterns
        for pattern in [
            r'Resolution[:\s]*([0-9]+\s*[xX×]\s*[0-9]+)',
            r'([0-9]+\s*[xX×]\s*[0-9]+)\s*(?:pixels?|resolution)',
            r'(?:^|\s)([0-9]{3,4}\s*[xX×]\s*[0-9]{3,4})(?:\s|$)',  # Standalone resolution
            r'Display[:\s]*([0-9]+\s*[xX×]\s*[0-9]+)',
            r'Screen[:\s]*([0-9]+\s*[xX×]\s*[0-9]+)',
            r'(?:^|\s)([1-9][0-9]{2,3}[xX×][1-9][0-9]{2,3})(?:\s|$)',  # Compact format like 1920x1080
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                resolution = match.group(1).replace(' ', '').lower().replace('×', 'x').replace('X', 'x')
                fps_data['resolution'] = resolution
                break
        
        # Try to find frames rendered - more comprehensive patterns
        for pattern in [
            r'Frames?\s*[Rr]endered[:\s]*([0-9,]+)',
            r'Rendered\s*[Ff]rames?[:\s]*([0-9,]+)',
            r'Total\s*[Ff]rames?[:\s]*([0-9,]+)',
            r'Frame\s*[Cc]ount[:\s]*([0-9,]+)',
            r'Frames?[:\s]*([0-9,]+)\s*rendered',
            r'(?:Rendered|Total)[:\s]*([0-9,]+)',
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Remove commas from number
                frame_count = match.group(1).replace(',', '')
                fps_data['frames_rendered'] = int(frame_count)
                break
        
        # Try to find Intel XeSS settings - more comprehensive patterns
        for pattern in [
            r'Intel\s+XeSS\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)',  # "Intel XeSS Balanced" or "Intel XeSS Ultra Quality"
            r'XeSS[:\s]+([A-Za-z]+(?:\s+[A-Za-z]+)?)',  # "XeSS: Balanced" or "XeSS Balanced"
            r'Intel\s+XeSS[:\s]*\(([^)]+)\)',  # "Intel XeSS (Balanced)"
            r'XeSS[:\s]*\(([^)]+)\)',  # "XeSS (Balanced)"
            r'Xe\s+Super\s+Sampling[:\s]+([A-Za-z]+(?:\s+[A-Za-z]+)?)',
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                xess_setting = match.group(1).strip()
                # Clean up common values
                xess_setting = xess_setting.replace('(', '').replace(')', '').replace('"', '').replace("'", '').strip()
                # Remove trailing punctuation and extra whitespace
                xess_setting = re.sub(r'[,;:.]$', '', xess_setting).strip()
                if xess_setting and len(xess_setting) < 30:  # Sanity check for reasonable setting name
                    fps_data['intel_xess'] = xess_setting
                break
        
        # If no specific metrics found, try to find any FPS number
        if 'avg_fps' not in fps_data:
            match = re.search(r'([0-9]+\.?[0-9]*)\s*FPS', text, re.IGNORECASE)
            if match:
                fps_data['fps'] = float(match.group(1))
        
        # Ensure all expected fields are present (with empty string if not found)
        expected_fields = ['avg_fps', 'min_fps', 'max_fps', 'resolution', 'frames_rendered', 'intel_xess']
        for field in expected_fields:
            if field not in fps_data:
                fps_data[field] = ''
        
        return fps_data
    
    def parse_image(self, image_path: str, debug: bool = False) -> Dict[str, float]:
        """
        Parse FPS data from a screenshot image.
        
        Args:
            image_path: Path to the screenshot image
            debug: If True, print extracted text for debugging
            
        Returns:
            Dictionary with FPS metrics
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Extract text from image
        text = self.extract_text(image_path)
        
        if debug:
            print(f"\n=== Extracted text from {Path(image_path).name} ===")
            print(text)
            print("=" * 50)
        
        # Parse FPS values
        fps_data = self.parse_fps_from_text(text)
        
        return fps_data
    
    def parse_folder(self, folder_path: str, pattern: str = "*_end.png", 
                     debug: bool = False) -> Dict[str, Dict[str, float]]:
        """
        Parse all matching images in a folder.
        
        Args:
            folder_path: Path to folder containing images
            pattern: Glob pattern for matching files
            debug: If True, print debug information
            
        Returns:
            Dictionary mapping image filename to FPS data
        """
        folder = Path(folder_path)
        results = {}
        
        for image_path in folder.glob(pattern):
            try:
                fps_data = self.parse_image(str(image_path), debug=debug)
                results[image_path.name] = fps_data
                
                if debug:
                    print(f"Parsed {image_path.name}: {fps_data}")
                    
            except Exception as e:
                print(f"Error parsing {image_path.name}: {e}")
                results[image_path.name] = {"error": str(e)}
        
        return results


# Legacy function for backward compatibility
def parseFpsImg(abs_path):
    """
    Legacy function for backward compatibility.
    
    Args:
        abs_path: Absolute path to image file
        
    Returns:
        Dictionary with FPS data
    """
    temp = dict()
    temp['fps_img_path'] = abs_path
    temp['fps_data'] = dict()
    
    try:
        # Try to find tesseract in common Windows locations
        tesseract_path = None
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Tesseract-OCR\tesseract.exe",
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                tesseract_path = path
                break
        
        parser = FPSImageParser(tesseract_path=tesseract_path)
        fps_data = parser.parse_image(abs_path)
        temp["fps_data"].update(fps_data)
        print(f"parsing FPS img: {temp}")
    except ImportError as e:
        print(f"Warning: OCR library not available for FPS image parsing: {e}")
        print("Install with: pip install pytesseract opencv-python Pillow")
        temp['error'] = "OCR library not installed"
    except Exception as e:
        print(f"Warning: Error parsing FPS image: {e}")
        if "tesseract" in str(e).lower():
            print("Tesseract not found. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
            print(f"Tried locations: {', '.join(common_paths)}")
        temp['error'] = str(e)
    
    return temp


def main():
    """Command-line interface for FPS image parser."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract FPS data from game benchmark screenshots")
    parser.add_argument("input", help="Input image file or folder")
    parser.add_argument("--pattern", default="*_end.png", 
                       help="File pattern for folder processing (default: *_end.png)")
    parser.add_argument("--debug", action="store_true", 
                       help="Print extracted text for debugging")
    parser.add_argument("--tesseract-path", 
                       help="Path to tesseract executable")
    
    args = parser.parse_args()
    
    # Initialize parser
    fps_parser = FPSImageParser(tesseract_path=args.tesseract_path)
    
    input_path = Path(args.input)
    
    if input_path.is_file():
        # Single file
        fps_data = fps_parser.parse_image(str(input_path), debug=args.debug)
        print(f"\n{input_path.name}:")
        for key, value in fps_data.items():
            print(f"  {key}: {value}")
    
    elif input_path.is_dir():
        # Folder
        results = fps_parser.parse_folder(str(input_path), pattern=args.pattern, debug=args.debug)
        
        print(f"\nProcessed {len(results)} images:")
        for filename, fps_data in results.items():
            print(f"\n{filename}:")
            if "error" in fps_data:
                print(f"  Error: {fps_data['error']}")
            else:
                for key, value in fps_data.items():
                    print(f"  {key}: {value}")
    
    else:
        print(f"Error: {input_path} is not a valid file or folder")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())





