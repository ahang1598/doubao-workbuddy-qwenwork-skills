import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide04Tokens = contentTokens["slide-04"];

export function buildSlide04(presentation, tokens = slide04Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-04", width: "fill", height: "fill" }, [
      text([tokens.body1.titleHere, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing2, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing3], {
  name: "Google-Shape-534-p58-1",
  position: {
    left: 41.33,
    top: 193.05
  },
  width: 580.91,
  height: 436.28,
  style: {
    fontSize: "32px",
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
      text([tokens.footer1], {
  name: "Google-Shape-532-p58-3",
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
  name: "Google-Shape-533-p58-4",
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
      text([tokens.body2.loremIpsumDolorSitAmetConsecteturAdipiscing, tokens.body2.loremIpsumDolorSitAmetConsecteturAdipiscing2, tokens.body2.loremIpsumDolorSitAmetConsecteturAdipiscing3], {
  name: "Google-Shape-534-p58-5",
  position: {
    left: 657.75,
    top: 230.2
  },
  width: 581.33,
  height: 399.13,
  style: {
    fontSize: "32px",
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
