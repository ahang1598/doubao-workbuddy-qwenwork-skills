import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide06Tokens = contentTokens["slide-06"];

export function buildSlide06(presentation, tokens = slide06Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-06", width: "fill", height: "fill" }, [
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
      text([tokens.body1.titleHere, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Google-Shape-534-p58-4",
  position: {
    left: 41.33,
    top: 353.33
  },
  width: 374.67,
  height: 276,
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
      text([tokens.body3.titleHere, tokens.body3.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-1-5",
  position: {
    left: 864,
    top: 353.33
  },
  width: 374.67,
  height: 276,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    autoFit: "shrinkText",
    insets: {
      top: 4.8,
      right: 9.6,
      bottom: 4.8,
      left: 9.6
    }
  }
}),
      text([tokens.body2.titleHere, tokens.body2.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-2-6",
  position: {
    left: 452.67,
    top: 353.33
  },
  width: 374.67,
  height: 276,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    autoFit: "shrinkText",
    insets: {
      top: 4.8,
      right: 9.6,
      bottom: 4.8,
      left: 9.6
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
