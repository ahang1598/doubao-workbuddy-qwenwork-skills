import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide11Tokens = contentTokens["slide-11"];

export function buildSlide11(presentation, tokens = slide11Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-11", width: "fill", height: "fill" }, [
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
    top: 36.17
  },
  width: 1197.33,
  height: 67.64,
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
  name: "Rounded-Rectangle-1-4",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 41.68,
    top: 350.56
  },
  width: 580.99,
  height: 138.67
}),
      text([tokens.body2], {
  name: "Content-Placeholder-10-5",
  position: {
    left: 72.89,
    top: 376.69
  },
  width: 523.56,
  height: 92.16,
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
      text([tokens.body4.detailGoesHere, tokens.body4.detailGoesHere2, tokens.body4.detailGoesHere3], {
  name: "Content-Placeholder-15-6",
  position: {
    left: 72.89,
    top: 506.94
  },
  width: 549.78,
  height: 102.67,
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
  name: "Rounded-Rectangle-7-7",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 657.3,
    top: 350.56
  },
  width: 580.99,
  height: 138.67
}),
      text([tokens.body3], {
  name: "Content-Placeholder-10-8",
  position: {
    left: 688.51,
    top: 376.69
  },
  width: 523.56,
  height: 92.16,
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
      text([tokens.body5.detailGoesHere, tokens.body5.detailGoesHere2, tokens.body5.detailGoesHere3], {
  name: "Content-Placeholder-15-9",
  position: {
    left: 688.51,
    top: 506.94
  },
  width: 549.78,
  height: 102.67,
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
      text([tokens.body1.topic, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing2], {
  name: "Content-Placeholder-15-10",
  position: {
    left: 42.09,
    top: 121.52
  },
  width: 1197.33,
  height: 171.05,
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
