import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide12Tokens = contentTokens["slide-12"];

export function buildSlide12(presentation, tokens = slide12Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-12", width: "fill", height: "fill" }, [
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
  name: "Rounded-Rectangle-6-4",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 657.68,
    top: 248.8
  },
  width: 580.99,
  height: 172
}),
      text([tokens.body3.titleGoesHere, tokens.body3.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-10-5",
  position: {
    left: 688.89,
    top: 279.77
  },
  width: 523.56,
  height: 110.07,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
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
  name: "Rounded-Rectangle-8-6",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 42.94,
    top: 248.8
  },
  width: 580.99,
  height: 172
}),
      text([tokens.body2.titleGoesHere, tokens.body2.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-10-7",
  position: {
    left: 74.15,
    top: 279.77
  },
  width: 523.56,
  height: 110.07,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
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
  name: "Rounded-Rectangle-1-8",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 657.68,
    top: 458.8
  },
  width: 580.99,
  height: 172
}),
      text([tokens.body5.titleGoesHere, tokens.body5.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-10-9",
  position: {
    left: 688.89,
    top: 489.77
  },
  width: 523.56,
  height: 110.07,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
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
  name: "Rounded-Rectangle-3-10",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 42.94,
    top: 458.8
  },
  width: 580.99,
  height: 172
}),
      text([tokens.body4.titleGoesHere, tokens.body4.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-10-11",
  position: {
    left: 74.15,
    top: 489.77
  },
  width: 523.56,
  height: 110.07,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
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
