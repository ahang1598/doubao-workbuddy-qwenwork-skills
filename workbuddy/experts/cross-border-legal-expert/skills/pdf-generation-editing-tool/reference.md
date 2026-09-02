# PDF Processing Advanced Reference

This document contains advanced PDF processing features, detailed examples, and additional libraries not covered in the main skill instructions.

> **Note:** Plain text extraction from PDFs is handled by the system's built-in read tool (natively supports PDF + OCR). This reference focuses on table extraction, merge/split, image extraction, and other operations.

## pypdfium2 Library (Apache/BSD License)

### Overview
pypdfium2 is a Python binding for PDFium (Chromium's PDF library). It's excellent for fast PDF rendering and image generation.

### Render PDF to Images

## JavaScript Libraries

### pdf-lib (MIT License)

pdf-lib is a powerful JavaScript library for creating and modifying PDF documents in any JavaScript environment.

#### Load and Manipulate Existing PDF

#### Advanced Merge and Split Operations

## Advanced Command-Line Operations

### PyMuPDF (fitz) Advanced Features

> **Note**: This skill uses **pymupdf** for PDF-to-image conversion (pure Python, no system dependency).
> Poppler tools listed below are optional alternatives.

#### Advanced Image Conversion with PyMuPDF

#### Extract Embedded Images

### qpdf Advanced Features

#### Complex Page Manipulation

#### PDF Optimization and Repair

#### Advanced Encryption

## Advanced Python Techniques

### pdfplumber Advanced Features

#### Advanced Table Extraction with Custom Settings

### reportlab Advanced Features

#### Create Professional Reports with Tables

## Complex Workflows

### Extract Figures/Images from PDF

#### Method 1: Using pdfimages (fastest)

#### Method 2: Using pypdfium2 + Image Processing

### Batch PDF Processing with Error Handling

### Advanced PDF Cropping

## Performance Optimization Tips

### For Large PDFs
- Use streaming approaches instead of loading entire PDF in memory
- Use `qpdf --split-pages` for splitting large files
- Process pages individually with pypdfium2

### For Table Extraction
- Use pdfplumber with custom table settings for complex layouts
- Use `page.to_image()` for visual debugging

### For Image Extraction
- `pdfimages` is much faster than rendering pages
- Use low resolution for previews, high resolution for final output

### For Form Filling
- pdf-lib maintains form structure better than most alternatives
- Pre-validate form fields before processing

### Memory Management

## Troubleshooting Common Issues

### Encrypted PDFs

### Corrupted PDFs

## License Information

- **pypdf**: BSD License
- **pdfplumber**: MIT License
- **pypdfium2**: Apache/BSD License
- **reportlab**: BSD License
- **pymupdf**: AGPL-3.0 License (commercial: https://artifex.com/licensing/)
- **qpdf**: Apache License
- **pdf-lib**: MIT License
