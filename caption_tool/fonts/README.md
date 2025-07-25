# Fonts Directory

This directory contains fonts used by the caption tool.

## Current Fonts

- **roboto.ttf**: Roboto Regular by Google - Modern, clean font
- **opensans.ttf**: Open Sans - Highly readable font  
- **inter.ttf**: Inter Regular - Optimized for screens
- **liberation-sans.ttf**: Liberation Sans - Free alternative to Arial
- **arial.ttf**: Arial (if copied from system)
- **calibri.ttf**: Calibri (if copied from system)

## Adding More Fonts

You can add more TTF font files to this directory. The caption tool will automatically detect and use them.

Popular free font sources:
- Google Fonts: https://fonts.google.com/
- Font Squirrel: https://www.fontsquirrel.com/
- Liberation Fonts: https://github.com/liberationfonts/liberation-fonts

## Usage

The caption tool will automatically use fonts from this directory. You can also specify a specific font:

```bash
python main.py video.mp4 output.mp4 --font-path fonts/roboto.ttf
```

## Font Licenses

- Roboto: Apache License 2.0
- Open Sans: Apache License 2.0
- Inter: SIL Open Font License 1.1
- Liberation Sans: SIL Open Font License 1.1

All fonts in this directory are free for commercial and personal use.
