import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide14Tokens = contentTokens["slide-14"];

export function buildSlide14(presentation, tokens = slide14Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-14", width: "fill", height: "fill" }, [
      text([tokens.footer1], {
  name: "Google-Shape-532-p58-2",
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
    autoFit: "none",
    wrap: "square",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.title], {
  name: "Google-Shape-533-p58-3",
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
    autoFit: "none",
    wrap: "square",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.body1.topic, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-15-4",
  position: {
    left: 42.09,
    top: 111.02
  },
  width: 1197.33,
  height: 106.27,
  style: {
    fontSize: "21.33px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    autoFit: "none",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      table({
  name: "Google-Shape-644-p93-5",
  rows: 9,
  columns: 5,
  values: [
    [
      "Column Label",
      "Column Label",
      "Column Label",
      "Column Label",
      "Column Label"
    ],
    [
      "Data Point",
      "$00.000 / item",
      "Yes",
      "1,000,000k / s",
      "0.00023862381"
    ],
    [
      "Data Point",
      "$00.000 / item",
      "No",
      "1,000,000k / s",
      "0.00023862381"
    ],
    [
      "Data Point",
      "$00.000 / item",
      "Yes",
      "1,000,000k / s",
      "0.00023862381"
    ],
    [
      "Data Point",
      "$00.000 / item",
      "No",
      "1,000,000k / s",
      "0.00023862381"
    ],
    [
      "Data Point",
      "$00.000 / item",
      "Yes",
      "1,000,000k / s",
      "0.00023862381"
    ],
    [
      "Data Point",
      "$00.000 / item",
      "No",
      "1,000,000k / s",
      "0.00023862381"
    ],
    [
      "Data Point",
      "$00.000 / item",
      "Yes",
      "1,000,000k / s",
      "0.00023862381"
    ],
    [
      "Data Point",
      "$00.000 / item",
      "Yes",
      "1,000,000k / s",
      "0.00023862381"
    ]
  ],
  columnWidths: [
    410.09,
    196.81,
    196.81,
    196.81,
    196.81
  ],
  position: {
    left: 41.33,
    top: 236.33
  },
  width: 1197.33,
  height: 412.87
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
