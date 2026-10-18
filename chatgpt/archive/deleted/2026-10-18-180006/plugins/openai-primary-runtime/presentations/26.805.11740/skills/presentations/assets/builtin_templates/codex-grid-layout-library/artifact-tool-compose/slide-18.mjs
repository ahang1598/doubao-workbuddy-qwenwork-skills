import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide18Tokens = contentTokens["slide-18"];

export function buildSlide18(presentation, tokens = slide18Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-18", width: "fill", height: "fill" }, [
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
    top: 560.8
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
    top: 555.18
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
    top: 555.18
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
    top: 555.18
  },
  width: 11.24,
  height: 11.24
}),
      shape({
  name: "Rounded-Rectangle-19-8",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 41.33,
    top: 147.17
  },
  width: 374.67,
  height: 380
}),
      text([tokens.body1.titleHere, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-8-9",
  position: {
    left: 73.85,
    top: 189.69
  },
  width: 309.64,
  height: 269.48,
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
      shape({
  name: "Rounded-Rectangle-21-10",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 452.33,
    top: 147.17
  },
  width: 374.67,
  height: 380
}),
      text([tokens.body2.titleHere, tokens.body2.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-8-11",
  position: {
    left: 484.85,
    top: 189.69
  },
  width: 309.64,
  height: 269.48,
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
      shape({
  name: "Rounded-Rectangle-23-12",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 864.83,
    top: 147.17
  },
  width: 374.67,
  height: 380
}),
      text([tokens.body3.titleHere, tokens.body3.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-8-13",
  position: {
    left: 897.35,
    top: 189.69
  },
  width: 309.64,
  height: 269.48,
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
  name: "Text-Placeholder-16-14",
  position: {
    left: 446.38,
    top: 588.18
  },
  width: 272.54,
  height: 41.15,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    autoFit: "none",
    insets: {
      top: 4.8,
      right: 9.6,
      bottom: 4.8,
      left: 9.6
    }
  }
}),
      text([tokens.label1], {
  name: "Text-Placeholder-16-15",
  position: {
    left: 41.04,
    top: 588.18
  },
  width: 272.54,
  height: 41.15,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    autoFit: "none",
    insets: {
      top: 4.8,
      right: 9.6,
      bottom: 4.8,
      left: 9.6
    }
  }
}),
      text([tokens.label3], {
  name: "Text-Placeholder-16-16",
  position: {
    left: 863.56,
    top: 588.18
  },
  width: 272.54,
  height: 41.15,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    autoFit: "none",
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
