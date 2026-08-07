import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide17Tokens = contentTokens["slide-17"];

export function buildSlide17(presentation, tokens = slide17Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-17", width: "fill", height: "fill" }, [
      text([tokens.footer1], {
  name: "Slide-Number-Placeholder-3-2",
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
  name: "Title-10-3",
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
      shape({
  name: "Google-Shape-2259-p159-4",
  geometry: "straightConnector1",
  fill: "none",
  line: {
    style: "solid",
    width: 1,
    fill: "#000000"
  },
  position: {
    left: 35.46,
    top: 354.2
  },
  width: 1285.61,
  height: 0.03
}),
      shape({
  name: "Google-Shape-2260-p159-5",
  geometry: "ellipse",
  fill: "#000000",
  position: {
    left: 35.46,
    top: 348.58
  },
  width: 11.24,
  height: 11.24
}),
      shape({
  name: "Google-Shape-2261-p159-6",
  geometry: "ellipse",
  fill: "#000000",
  position: {
    left: 446.38,
    top: 348.58
  },
  width: 11.24,
  height: 11.24
}),
      shape({
  name: "Google-Shape-2262-p159-7",
  geometry: "ellipse",
  fill: "#000000",
  position: {
    left: 858.38,
    top: 348.58
  },
  width: 11.24,
  height: 11.24
}),
      text([tokens.label1], {
  name: "Content-Placeholder-15-8",
  position: {
    left: 41.33,
    top: 298.51
  },
  width: 169.33,
  height: 27.55,
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
      text([tokens.label2], {
  name: "Content-Placeholder-15-9",
  position: {
    left: 450.83,
    top: 298.51
  },
  width: 169.33,
  height: 27.55,
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
      text([tokens.label3], {
  name: "Content-Placeholder-15-10",
  position: {
    left: 863.33,
    top: 298.51
  },
  width: 169.33,
  height: 27.55,
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
      text([tokens.body2.titleHere, tokens.body2.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Text-Placeholder-16-11",
  position: {
    left: 453.24,
    top: 401.33
  },
  width: 331.35,
  height: 166.54,
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
      text([tokens.body1.titleHere, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Text-Placeholder-16-12",
  position: {
    left: 41.98,
    top: 401.33
  },
  width: 331.35,
  height: 166.54,
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
      text([tokens.body3.titleHere, tokens.body3.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Text-Placeholder-16-13",
  position: {
    left: 858.57,
    top: 401.33
  },
  width: 331.35,
  height: 166.54,
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
