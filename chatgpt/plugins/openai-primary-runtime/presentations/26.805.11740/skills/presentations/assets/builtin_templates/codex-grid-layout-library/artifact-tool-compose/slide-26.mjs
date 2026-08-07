import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide26Tokens = contentTokens["slide-26"];

export function buildSlide26(presentation, tokens = slide26Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-26", width: "fill", height: "fill" }, [
      text([tokens.title2], {
  name: "Title-3-1",
  position: {
    left: 41.33,
    top: 182.55
  },
  width: 992,
  height: 261.57,
  style: {
    fontSize: "80px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "bottom",
    autoFit: "none",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.title3.loremIpsumDetails, tokens.title3.loremIpsumDetails2, tokens.title3.loremIpsumDetails3], {
  name: "Subtitle-4-2",
  position: {
    left: 41.33,
    top: 522.13
  },
  width: 374.67,
  height: 113.41,
  style: {
    fontSize: "32px",
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
      text([tokens.title], {
  name: "Subtitle-4-3",
  position: {
    left: 41.33,
    top: 41.18
  },
  width: 169.33,
  height: 68.15,
  style: {
    fontSize: "32px",
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
