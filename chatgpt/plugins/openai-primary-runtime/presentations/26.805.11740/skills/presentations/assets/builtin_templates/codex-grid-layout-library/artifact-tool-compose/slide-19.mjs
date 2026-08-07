import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide19Tokens = contentTokens["slide-19"];

export function buildSlide19(presentation, tokens = slide19Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-19", width: "fill", height: "fill" }, [
      shape({
  name: "Rounded-Rectangle-5-1",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 41.33,
    top: 317.33
  },
  width: 374.67,
  height: 312
}),
      shape({
  name: "Rounded-Rectangle-6-2",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 452.67,
    top: 317.33
  },
  width: 374.67,
  height: 312
}),
      shape({
  name: "Rounded-Rectangle-7-3",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 864.28,
    top: 317.33
  },
  width: 374.67,
  height: 312
}),
      text([tokens.footer1], {
  name: "Slide-Number-Placeholder-1-4",
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
  name: "Title-2-5",
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
      text([tokens.body2], {
  name: "Content-Placeholder-9-6",
  position: {
    left: 73.74,
    top: 514.5
  },
  width: 309.67,
  height: 86,
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
      text([tokens.body4], {
  name: "Content-Placeholder-10-7",
  position: {
    left: 896.78,
    top: 514.5
  },
  width: 309.67,
  height: 86,
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
      text([tokens.body3], {
  name: "Content-Placeholder-11-8",
  position: {
    left: 485.17,
    top: 514.5
  },
  width: 309.67,
  height: 86,
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
      text([tokens.stat1], {
  name: "Content-Placeholder-9-9",
  position: {
    left: 73.74,
    top: 360
  },
  width: 308.67,
  height: 142.71,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "bottom",
    autoFit: "shrinkText",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.stat2], {
  name: "Content-Placeholder-9-10",
  position: {
    left: 484.3,
    top: 360
  },
  width: 308.67,
  height: 142.71,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "bottom",
    autoFit: "shrinkText",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.stat3], {
  name: "Content-Placeholder-9-11",
  position: {
    left: 898.94,
    top: 360
  },
  width: 308.67,
  height: 142.71,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "bottom",
    autoFit: "shrinkText",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.body1.topic, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-15-12",
  position: {
    left: 41.33,
    top: 119.51
  },
  width: 1197.33,
  height: 167.92,
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
