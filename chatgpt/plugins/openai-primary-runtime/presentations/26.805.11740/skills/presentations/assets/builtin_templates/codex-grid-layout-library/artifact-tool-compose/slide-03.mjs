import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide03Tokens = contentTokens["slide-03"];

export function buildSlide03(presentation, tokens = slide03Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-03", width: "fill", height: "fill" }, [
      text([tokens.footer1], {
  name: "Slide-Number-Placeholder-1-2",
  position: {
    left: 1184.18,
    top: 659.24
  },
  width: 54.48,
  height: 25.33,
  style: {
    fontSize: "13.33px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "right",
    verticalAlignment: "bottom",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.title], {
  name: "Title-2-3",
  position: {
    left: 41.33,
    top: 36.12
  },
  width: 1197.33,
  height: 109.97,
  style: {
    fontSize: "38.67px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "top",
    autoFit: "shrinkText",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      table({
  name: "Table-3-4",
  rows: 6,
  columns: 2,
  values: [
    [
      "01",
      "Agenda item one"
    ],
    [
      "02",
      "Agenda item two"
    ],
    [
      "03",
      "Agenda item three"
    ],
    [
      "04",
      "Agenda item four"
    ],
    [
      "05",
      "Agenda item five"
    ],
    [
      "06",
      "Agenda item six"
    ]
  ],
  columnWidths: [
    92.23,
    1105.1
  ],
  position: {
    left: 41.33,
    top: 218.37
  },
  width: 1197.34,
  height: 410.96
}),
    ]),
    { frame: {
  left: 0,
  top: 0,
  width: 1280,
  height: 720
}, baseUnit: 1 },
  );
  return slide;
}
