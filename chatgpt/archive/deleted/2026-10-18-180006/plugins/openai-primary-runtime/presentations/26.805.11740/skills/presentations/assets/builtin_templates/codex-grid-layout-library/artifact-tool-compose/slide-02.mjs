import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide02Tokens = contentTokens["slide-02"];

export function buildSlide02(presentation, tokens = slide02Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-02", width: "fill", height: "fill" }, [
      text([tokens.title3], {
  name: "Title-3-1",
  position: {
    left: 41.33,
    top: 270.86
  },
  width: 992,
  height: 380.5,
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
      text([tokens.title], {
  name: "Subtitle-4-2",
  position: {
    left: 41.33,
    top: 41.18
  },
  width: 646.49,
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
      text([tokens.title2], {
  name: "Subtitle-4-3",
  position: {
    left: 828,
    top: 41.18
  },
  width: 410.67,
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
