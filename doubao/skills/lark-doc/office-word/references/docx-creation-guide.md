# DOCX Creation Guide — Creating New Documents with docx-js

Generate .docx files with JavaScript using the `docx` npm package.

Install: `npm install -g docx`

## Table of Contents

1. [Basic Setup](#basic-setup)
2. [Page Size](#page-size)
3. [Styles](#styles)
4. [Lists](#lists)
5. [Tables](#tables)
6. [Images](#images)
7. [Headers and Footers](#headers-and-footers)
8. [Page Breaks](#page-breaks)
9. [Hyperlinks](#hyperlinks)
10. [Tab Stops](#tab-stops)
11. [Critical Rules](#critical-rules)
12. [Validation](#validation)

---

## Basic Setup

```javascript
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
        Header, Footer, AlignmentType, PageOrientation, LevelFormat, ExternalHyperlink,
        InternalHyperlink, Bookmark, FootnoteReferenceRun, PositionalTab,
        PositionalTabAlignment, PositionalTabRelativeTo, PositionalTabLeader,
        TabStopType, TabStopPosition, Column, SectionType,
        TableOfContents, HeadingLevel, BorderStyle, WidthType, ShadingType,
        VerticalAlign, PageNumber, PageBreak } = require('docx');

const doc = new Document({ sections: [{ children: [/* content */] }] });
Packer.toBuffer(doc).then(buffer => fs.writeFileSync("doc.docx", buffer));
```

## Page Size

```javascript
sections: [{
  properties: {
    page: {
      size: {
        width: 12240,   // 8.5 inches (US Letter)
        height: 15840   // 11 inches
      },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } // 1 inch
    }
  },
  children: [/* content */]
}]
```

**Common page sizes (DXA units, 1440 DXA = 1 inch):**

| Paper | Width | Height | Content Width (1" margins) |
|-------|-------|--------|---------------------------|
| US Letter | 12,240 | 15,840 | 9,360 |
| A4 (default) | 11,906 | 16,838 | 9,026 |

**Landscape:** Pass portrait dimensions and set orientation:
```javascript
size: {
  width: 12240,
  height: 15840,
  orientation: PageOrientation.LANDSCAPE
},
```

## Styles

Use Arial as the default font.

```javascript
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 } },
    ]
  },
  sections: [{ children: [
    new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Title")] }),
  ]}]
});
```

## Lists

```javascript
const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    children: [
      new Paragraph({ numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Bullet item")] }),
    ]
  }]
});
```

Never use unicode bullets like `\u2022` directly in TextRun — always use `LevelFormat.BULLET`.

## Tables

**Set both `columnWidths` on the table AND `width` on each cell. Use `WidthType.DXA` only (never percentage).**

```javascript
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [4680, 4680],
  rows: [
    new TableRow({
      children: [
        new TableCell({
          borders,
          width: { size: 4680, type: WidthType.DXA },
          shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ children: [new TextRun("Cell")] })]
        })
      ]
    })
  ]
})
```

## Images

```javascript
new Paragraph({
  children: [new ImageRun({
    type: "png",
    data: fs.readFileSync("image.png"),
    transformation: { width: 200, height: 150 },
    altText: { title: "Title", description: "Desc", name: "Name" }
  })]
})
```

## Headers and Footers

```javascript
sections: [{
  headers: {
    default: new Header({ children: [new Paragraph({ children: [new TextRun("Header")] })] })
  },
  footers: {
    default: new Footer({ children: [new Paragraph({
      children: [new TextRun("Page "), new TextRun({ children: [PageNumber.CURRENT] })]
    })] })
  },
  children: [/* content */]
}]
```

## Page Breaks

```javascript
new Paragraph({ children: [new PageBreak()] })
// Or
new Paragraph({ pageBreakBefore: true, children: [new TextRun("New page")] })
```

## Hyperlinks

```javascript
new Paragraph({
  children: [new ExternalHyperlink({
    children: [new TextRun({ text: "Click here", style: "Hyperlink" })],
    link: "https://example.com",
  })]
})
```

## Tab Stops

```javascript
new Paragraph({
  children: [
    new TextRun("Company Name"),
    new TextRun("\tJanuary 2025"),
  ],
  tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
})
```

## Critical Rules

- **Set page size explicitly** — docx-js defaults to A4
- **Never use `\n`** — use separate Paragraph elements
- **Never use unicode bullets** — use `LevelFormat.BULLET`
- **PageBreak must be in Paragraph**
- **ImageRun requires `type`** — always specify png/jpg/etc
- **Always use `WidthType.DXA`** for table widths (never percentage)
- **Tables need dual widths** — `columnWidths` AND cell `width` must match
- **Use `ShadingType.CLEAR`** for table shading (never SOLID)
- **Override built-in styles** with exact IDs: "Heading1", "Heading2", etc.
- **Include `outlineLevel`** for TOC (0 for H1, 1 for H2)

## Validation

After creating the file, validate it by re-extracting — if it opens and the content is intact, the file is valid:
```bash
uv run skills/lark-doc/office-word/scripts/extract_docx.py doc.docx
```
If extraction fails or the content is wrong, unpack with `uv run skills/lark-doc/office-word/scripts/docx_edit.py unpack`, fix the XML, and repack with `uv run skills/lark-doc/office-word/scripts/docx_edit.py pack`.
