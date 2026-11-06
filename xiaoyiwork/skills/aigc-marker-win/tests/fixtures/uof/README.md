# UOF test fixtures and validation provenance

These are synthetic native UOF documents, not OOXML files renamed to UOF.
No office application, runtime dependency or reference converter is installed
by the skill. Reference converters were downloaded to a system temporary
research directory solely for the independent checks below.

## Fixture construction

- `uof1.uot`, `uof1.uos`, and `uof1.uop` were generated from small ODF XML
  documents using the corresponding official LibreOffice `odf2uof_*.xsl`
  exports. They contain one text paragraph, two populated worksheets, and one
  slide with an existing text shape respectively. A `KeepMe` custom property
  has the value `original property`; that payload was restored explicitly
  after export because the old Writer/Impress exporters omit its value.
- `make_uof_sample()` in `test_uof_marker.py` builds UOF 2 ZIP packages using
  the native structures emitted by the Beihang UOF/Open XML Translator.
  Packages contain `uof.xml`, native `content.xml`, `_meta/meta.xml`, style,
  graphic, rule, hyperlink, object, extension and theme parts, plus a binary
  preservation sentinel. Word paragraphs are siblings of section-property
  markers. Spreadsheet strings are native cell data. A slide label is a text
  graphic in `graphics.xml` referenced by a slide anchor in `content.xml`.
- Document/template pairs use the matching UOF content model. Tests preserve
  the six requested extensions and existing template metadata. Native office
  applications' create-from-template workflows have not been tested.

## Independent content checks performed on 2026-10-10

1. The three UOF 1 samples were marked, then converted back with the official
   LibreOffice `uof2odf_*.xsl` imports, using lxml XSLT. Original text remained;
   the new labels appeared in the ODF body: one Writer paragraph, one cell in
   each of the two Calc worksheets, and one text graphic in the Impress slide.
2. UOF 2 samples were read through the original Beihang preprocessing rules
   (`word/uof2oox/uof2ooxpre.xsl`, `Excel/uof2oox/pretreatment.xsl`, and
   `Powerpoint/uof2oox/uof2ooxpre.xslt`), with the required local package parts.
   The original `uof2oox.xsl` rules were executed by Windows .NET
   `System.Xml.Xsl.XslCompiledTransform` with a local XML resolver.
3. For the minimal UOF 2 slide, the original C# presentation preprocessor's
   graph-reference expansion was reproduced: it copies each referenced
   graphic under its matching anchor before running the final XSL. The
   remaining C# preprocessing for layouts, complex shapes and animations was
   not executed, as those features are absent from the sample.
4. The resulting OOXML XML parts contained the labels at actual body sites:
   `word/document.xml` had both the original text and a new `w:p/w:r/w:t`;
   `xl/worksheets/sheet1.xml` and `sheet2.xml` had A2 cells referring to label
   strings in `xl/sharedStrings.xml`; and `ppt/slides/slide1.xml` had an
   anchored text shape containing `a:t`. This independent check detected and
   corrected an initial Word section-container mistake.

These are native-content parsing/conversion checks. They are not screenshots,
full XSD conformance certification, or claims of successful visual rendering
in WPS/Yozo/LibreOffice desktop. The full reference translators are not shipped
with or invoked by regression tests.

## Automated regression coverage

Run `python -m unittest discover -s resources/skills/aigc-marker-win/tests
-p test_uof_marker.py -v` from the repository root. Seven tests cover UOF 1 and
UOF 2 across all six extensions, real CLI execution, body/metadata placement,
visible upgrade after implicit-only marking, stable content IDs, byte-stable
repeated runs, unchanged ZIP member payloads/archive comments, custom
properties, unknown namespaces/comments, hidden first slide selection, and
failure without changing the original file.

Watermark placement is the final Word paragraph, final data row of each
worksheet, and a text box at the upper left of the first shown slide. Existing
spreadsheet print areas are preserved; the cell label is verified in the
worksheet reading view and is not guaranteed to be included in a restricted
print area. Encrypted/signed packages, DTD XML, and chart-only sheets without
native cell data are rejected instead of reported as successfully marked.

## Primary implementation sources

- [LibreOffice UOF export filters](https://github.com/LibreOffice/core/tree/master/filter/source/xslt/export/uof)
- [LibreOffice UOF import filters](https://github.com/LibreOffice/core/tree/master/filter/source/xslt/import/uof)
- [Beihang UOF/Open XML Translator project](https://uof-translator.sourceforge.net/download.html)
- [Translator source mirror](https://github.com/ARLM-Keller/UOF-EF-to-Open-XML-Translator/tree/master/UofTranslatorLib/resources)
- [UOF 2 metadata output rules](https://github.com/ARLM-Keller/UOF-EF-to-Open-XML-Translator/blob/master/UofTranslatorLib/resources/word/oox2uof/metadata.xsl)
- [UOF 2 native Word output rules](https://github.com/ARLM-Keller/UOF-EF-to-Open-XML-Translator/blob/master/UofTranslatorLib/resources/word/oox2uof/oox2uof.xsl)
- [UOF 2 native spreadsheet output rules](https://github.com/ARLM-Keller/UOF-EF-to-Open-XML-Translator/blob/master/UofTranslatorLib/resources/Excel/oox2uof/sheets.xsl)
- [UOF 2 native slide graphic output rules](https://github.com/ARLM-Keller/UOF-EF-to-Open-XML-Translator/blob/master/UofTranslatorLib/resources/Powerpoint/oox2uof/shapes.xsl)
- [Presentation reference expansion](https://github.com/ARLM-Keller/UOF-EF-to-Open-XML-Translator/blob/master/UofTranslatorLib/UofToOoxPreProcessorOnePresentation.cs)

The real UOF 2 schema element names are `用户自定义元数据集_520F` and
`用户自定义元数据_5210`; the handler also reads the shortened names printed in
the TC260 practice guide. New records use native schema names and put the AIGC
JSON directly in the property with `名称_5211="AIGC"`.
