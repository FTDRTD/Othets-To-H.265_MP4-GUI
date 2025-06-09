# Video Batch Converter

A Python and FFmpeg based video batch conversion tool that can convert various video formats to H.265/HEVC encoded MP4 format, significantly reducing file size.

## Features

- Supports multiple input formats: MP4, MKV, AVI, MOV, WMV, FLV, TS, WEBM
- Automatic system theme detection (Dark/Light mode)
- Multi-threaded processing for improved efficiency
- Progress bar displays conversion progress
- System notification upon completion
- Automatically adapts video resolution to set appropriate encoding parameters
- Supports hardware accelerated encoding (AMF/Vulkan)

## System Requirements

- Windows operating system
- Python 3.7+
- FFmpeg installed and added to system PATH
- Recommended: Graphics card with hardware acceleration support (AMD/NVIDIA)

## Installation Guide

1. Clone or download this project
2. Install Python dependencies:
   ```
   pip install ttkbootstrap plyer
   ```
3. Ensure FFmpeg is properly installed and added to system PATH

## Usage Instructions

1. Run `GUI_Drakmode.py` to launch the graphical interface
2. Click "Browse" button to select folder containing video files
3. Click "Start Conversion" button to begin the process
4. After conversion, videos will be saved in "Converted" subfolder of the source folder
5. Log files are saved in "Logs" subfolder

## Notes

1. Do not close the program during conversion
2. Conversion time depends on video size and hardware performance
3. If conversion fails, the program will automatically try software encoding
4. Converted files will have "_hevc" suffix added to their names

## Building Executable

You can build a standalone executable using Nuitka:

```
python -m nuitka --onefile --enable-plugin=tk-inter --windows-disable-console .\GUI_Drakmode.py
```

## License

MIT License