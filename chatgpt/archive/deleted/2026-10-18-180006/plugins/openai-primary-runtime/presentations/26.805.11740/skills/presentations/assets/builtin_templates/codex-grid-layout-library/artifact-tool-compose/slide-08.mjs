import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide08Tokens = contentTokens["slide-08"];

export function buildSlide08(presentation, tokens = slide08Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-08", width: "fill", height: "fill" }, [
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
      shape({
  name: "Picture-3-4-backing",
  geometry: "roundRect",
  fill: "#EAF5FB",
  line: {
    style: "solid",
    width: 1,
    fill: "#B8BCC4"
  },
  position: {
    left: 658.17,
    top: 41.62
  },
  width: 581.6,
  height: 588.14
}),
      image({
  name: "Picture-3-4",
  prompt: "Clean editorial light-blue conceptual image with subtle architectural geometry, ample white space, and no embedded text",
  alt: "hero placeholder for Picture 3",
  fit: "cover",
  geometry: "roundRect",
  position: {
    left: 658.17,
    top: 41.62
  },
  width: 581.6,
  height: 588.14
}),
      text([tokens.body1.titleHere, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Google-Shape-534-p58-5",
  position: {
    left: 41.33,
    top: 213.33
  },
  width: 581.33,
  height: 416,
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
